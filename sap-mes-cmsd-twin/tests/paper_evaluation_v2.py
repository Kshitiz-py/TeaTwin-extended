"""
Paper Evaluation Test Harness v2 — Multi-model, multi-instance, token-aware.

Usage:
    python tests/paper_evaluation_v2.py [--models M1,M2] [--runs N] [--ablation]
                                        [--multi-instance] [--variant V] [--entity E]

    python tests/paper_evaluation_v2.py --runs 3 --ablation --multi-instance  # Full study

Models (-m flag or MODELS list below):
    qwen       → qwen3.5:397b-cloud via Ollama Cloud
    kimi       → kimi-k2.6:cloud via Ollama Cloud
    deepseek-c → deepseek-v4-flash:cloud via Ollama Cloud
    deepseek   → deepseek-chat via direct DeepSeek API

Output:
    tests/fixtures/results/evaluation_report_v2.json  — full statistical data
    tests/fixtures/results/evaluation_report_v2.md    — human-readable summary
"""

import json
import os
import sys
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import httpx

# --- Configuration ---
AI_AGENT_BASE = os.environ.get("AI_AGENT_URL", "http://localhost:8003/api/agent/v1")
CMSD_BASE = os.environ.get("CMSD_TWIN_URL", "http://localhost:8000/api/cmsd/v1")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
VARIANTS_DIR = os.path.join(FIXTURES_DIR, "variants")
RESULTS_DIR = os.path.join(FIXTURES_DIR, "results")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fixtures", "ground_truth"))
from ground_truth import (
    RESOURCE_GROUND_TRUTH,
    RESOURCECLASS_GROUND_TRUTH,
    ORDER_GROUND_TRUTH,
    PARTTYPE_GROUND_TRUTH,
    SCHEMA_COVERAGE,
    LEGACY_API_PATH,
    GERMAN_API_PATH,
    DEEP_COUNT_PATH,
)

ENTITY_GROUND_TRUTH = {
    "Resource": RESOURCE_GROUND_TRUTH,
    "ResourceClass": RESOURCECLASS_GROUND_TRUTH,
    "Order": ORDER_GROUND_TRUTH,
    "PartType": PARTTYPE_GROUND_TRUTH,
}

VARIANTS = ["clean", "legacy", "german", "deep"]

VARIANT_API_PATH_MAP = {
    "clean": {},
    "legacy": LEGACY_API_PATH,
    "german": GERMAN_API_PATH,
    "deep": {},
}

# --- Model Registry ---
# Each model entry: {name, provider_type, host, api_key, chat_model}
OLLAMA_CLOUD_KEY = os.environ.get("OLLAMA_CLOUD_KEY", "de478d55164445e5898129af80475a3b.6rr0bjQe_Ngwi1FGJ0mujrN_")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

MODEL_REGISTRY = {
    "deepseek-flash": {
        "name": "deepseek-v4-flash",
        "provider_type": "deepseek",
        "host": "https://api.deepseek.com",
        "api_key": DEEPSEEK_KEY or "",
        "chat_model": "deepseek-v4-flash",
    },
    "deepseek-pro": {
        "name": "deepseek-v4-pro",
        "provider_type": "deepseek",
        "host": "https://api.deepseek.com",
        "api_key": DEEPSEEK_KEY or "",
        "chat_model": "deepseek-v4-pro",
    },
    "qwen": {
        "name": "qwen3.5:397b-cloud",
        "provider_type": "custom",
        "host": "https://ollama.com",
        "api_key": OLLAMA_CLOUD_KEY,
        "chat_model": "qwen3.5:397b-cloud",
    },
    "kimi": {
        "name": "kimi-k2.6:cloud",
        "provider_type": "custom",
        "host": "https://ollama.com",
        "api_key": OLLAMA_CLOUD_KEY,
        "chat_model": "kimi-k2.6:cloud",
    },
}

# --- Field Type Classification (for string vs numeric analysis) ---
# Will be populated after helper functions are defined below
FIELD_TYPE_CLASSIFICATION: dict[str, dict[str, str]] = {}


def get_variant_items_key(entity_name, variant):
    if variant == "deep":
        return DEEP_COUNT_PATH
    key_map = {
        "Resource": "resources",
        "ResourceClass": "resource_classes",
        "Order": "orders",
        "PartType": "part_types",
    }
    return key_map[entity_name]


def load_variant_payload(entity_name, variant):
    filepath = os.path.join(VARIANTS_DIR, variant, f"{entity_name}.json")
    with open(filepath) as f:
        return json.load(f)


def get_first_item(payload, items_key):
    parts = items_key.split(".")
    cur = payload
    for part in parts:
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return payload
    if isinstance(cur, list) and len(cur) > 0:
        return cur[0]
    return payload


def get_all_items(payload, items_key):
    """Extract ALL instances from the array for multi-instance mode."""
    parts = items_key.split(".")
    cur = payload
    for part in parts:
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return [payload]
    if isinstance(cur, list):
        return cur
    return [cur]


def build_expected_api_path(ground_truth_mapping, variant):
    variant_map = VARIANT_API_PATH_MAP.get(variant, {})
    result = {}
    for cmsd_field, clean_path in ground_truth_mapping.items():
        result[cmsd_field] = variant_map.get(clean_path, clean_path)
    return result


def evaluate_mapping(llm_mapping, ground_truth, expected_paths, cmsd_entity, variant):
    """Evaluate mapping accuracy, broken down by string vs numeric field types."""
    gt_fields = set(ground_truth.keys())
    llm_fields = set(llm_mapping.keys())
    field_types = FIELD_TYPE_CLASSIFICATION.get(cmsd_entity, {})

    correct = 0
    incorrect = 0
    incorrect_details = []
    missed = 0
    missed_fields = []
    extra = 0
    extra_fields = []

    # Per-type counters
    string_correct = 0
    string_total = 0
    numeric_correct = 0
    numeric_total = 0
    null_prone_correct = 0
    null_prone_total = 0

    for field in gt_fields:
        expected_path = expected_paths.get(field, ground_truth[field])
        ftype = field_types.get(field, "string")

        if ftype == "string":
            string_total += 1
        elif ftype == "numeric":
            numeric_total += 1
        else:
            null_prone_total += 1

        if field in llm_mapping:
            field_info = llm_mapping[field]
            if isinstance(field_info, dict):
                actual_path = field_info.get("api_path") or ""
            else:
                actual_path = str(field_info) if field_info is not None else ""
            if actual_path and actual_path.startswith("$."):
                actual_path = actual_path[2:]

            if actual_path == expected_path:
                correct += 1
                if ftype == "string":
                    string_correct += 1
                elif ftype == "numeric":
                    numeric_correct += 1
                else:
                    null_prone_correct += 1
            else:
                incorrect += 1
                incorrect_details.append({
                    "field": field, "expected": expected_path, "actual": actual_path,
                    "confidence": field_info.get("confidence", "?") if isinstance(field_info, dict) else "?",
                    "field_type": ftype,
                })
        else:
            missed += 1
            missed_fields.append({"field": field, "expected": expected_path, "field_type": ftype})

    for field in llm_fields - gt_fields:
        extra += 1
        field_info = llm_mapping[field]
        extra_fields.append({
            "field": field,
            "api_path": field_info.get("api_path", "?") if isinstance(field_info, dict) else str(field_info),
        })

    total_gt = len(gt_fields)
    accuracy = correct / total_gt if total_gt > 0 else 0.0
    recall = (correct + incorrect) / total_gt if total_gt > 0 else 0.0
    precision = correct / (correct + incorrect) if (correct + incorrect) > 0 else 0.0

    string_acc = string_correct / string_total if string_total > 0 else None
    numeric_acc = numeric_correct / numeric_total if numeric_total > 0 else None
    null_prone_acc = null_prone_correct / null_prone_total if null_prone_total > 0 else None

    conf_dist = {"high": 0, "medium": 0, "low": 0, "manual": 0, "unknown": 0}
    for field, info in llm_mapping.items():
        if isinstance(info, dict):
            c = info.get("confidence", "unknown")
            conf_dist[c] = conf_dist.get(c, 0) + 1
        else:
            conf_dist["unknown"] += 1

    return {
        "entity": cmsd_entity, "variant": variant,
        "ground_truth_fields": total_gt,
        "llm_total_proposals": len(llm_fields),
        "correct": correct, "incorrect": incorrect, "missed": missed, "extra": extra,
        "accuracy": round(accuracy * 100, 1),
        "recall": round(recall * 100, 1),
        "precision": round(precision * 100, 1),
        "string_accuracy": round(string_acc * 100, 1) if string_acc is not None else None,
        "numeric_accuracy": round(numeric_acc * 100, 1) if numeric_acc is not None else None,
        "null_prone_accuracy": round(null_prone_acc * 100, 1) if null_prone_acc is not None else None,
        "string_fields": string_total,
        "numeric_fields": numeric_total,
        "null_prone_fields": null_prone_total,
        "confidence_distribution": conf_dist,
        "incorrect_details": incorrect_details,
        "missed_fields": missed_fields,
    }


def configure_llm(client, model_config):
    """Reconfigure the AI agent's LLM for a specific model."""
    # Use a fresh client for configuration to avoid stale connection issues
    cfg_client = httpx.Client(timeout=30)
    payload = {
        "chat": {
            "provider_type": model_config["provider_type"],
            "host": model_config["host"],
            "api_key": model_config["api_key"],
            "chat_model": model_config["chat_model"],
            "embed_model": "",
        },
    }
    try:
        r = cfg_client.post(f"{AI_AGENT_BASE}/agent/connect", json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("configured"):
                if not data.get("connection_test", {}).get("chat", {}).get("ok"):
                    return True, "WARNING: connection test failed but config applied"
                return True, data
            return False, data
        return False, r.text
    except Exception as e:
        return False, str(e)
    finally:
        cfg_client.close()


def run_single_experiment(client, entity_name, variant, ground_truth,
                          skip_rag=False, multi_instance=False):
    """Run one mapping experiment. Returns result dict with all metrics."""
    payload = load_variant_payload(entity_name, variant)
    items_key = get_variant_items_key(entity_name, variant)

    if multi_instance:
        raw_items = get_all_items(payload, items_key)
        instance_count = len(raw_items)
    else:
        first_item = get_first_item(payload, items_key)
        raw_items = first_item if isinstance(first_item, dict) else payload
        instance_count = 1

    rag_label = "no_rag" if skip_rag else "full_rag"
    inst_label = "multi" if multi_instance else "single"
    data_point_name = f"Eval: {entity_name} ({variant}/{rag_label}/{inst_label})"

    request_body = {
        "data_point_name": data_point_name,
        "cmsd_entity": entity_name,
        "skip_rag": skip_rag,
        "multi_instance": multi_instance,
        "approved_payloads": [{
            "endpoint": f"/{entity_name.lower()}",
            "source_id": variant,
            "label": f"Variant {variant}",
            "raw_payload": raw_items,
        }],
    }

    t0 = time.time()
    try:
        r = client.post(
            f"{AI_AGENT_BASE}/mapping/analyze",
            json=request_body,
            timeout=120,
        )
        elapsed = time.time() - t0
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:500]}", "elapsed_seconds": round(elapsed, 1)}
        response = r.json()
    except Exception as e:
        elapsed = time.time() - t0
        return {"error": str(e), "elapsed_seconds": round(elapsed, 1)}

    # Extract mapping from response
    mapping = response.get("mapping") or response.get("proposed_mapping", {})
    if isinstance(mapping, dict) and "mapping" in mapping:
        inner = mapping["mapping"]
        # Capture token usage and timing from the outer mapping wrapper
        token_usage = mapping.get("_token_usage", {})
        timing_ms = mapping.get("_timing_ms", {})
    else:
        inner = mapping
        token_usage = {}
        timing_ms = {}

    expected_paths = build_expected_api_path(ground_truth, variant)
    result = evaluate_mapping(inner, ground_truth, expected_paths, entity_name, variant)

    # Attach metadata
    result["elapsed_seconds"] = round(elapsed, 1)
    result["rag_mode"] = rag_label
    result["instance_mode"] = inst_label
    result["instance_count"] = instance_count if multi_instance else 1
    result["rag_context_length"] = len(response.get("rag_context", "") or "")
    result["prompt_tokens"] = token_usage.get("prompt_tokens", 0)
    result["completion_tokens"] = token_usage.get("completion_tokens", 0)
    result["total_tokens"] = token_usage.get("total_tokens", 0)
    result["llm_inference_ms"] = timing_ms.get("llm_call", 0)
    result["overhead_ms"] = timing_ms.get("total", 0) - timing_ms.get("llm_call", 0)

    return result


def check_llm_available(client):
    try:
        r = client.get(f"{AI_AGENT_BASE}/agent/status", timeout=5)
        if r.status_code == 200:
            return r.json().get("connected", False)
    except Exception:
        pass
    return False


def compute_run_stats(runs: list[dict]) -> dict:
    """Compute aggregate statistics across multiple runs."""
    accuracies = [r["accuracy"] for r in runs if "error" not in r]
    times = [r.get("elapsed_seconds", 0) for r in runs if "error" not in r]
    string_accs = [r["string_accuracy"] for r in runs if "error" not in r and r.get("string_accuracy") is not None]
    numeric_accs = [r["numeric_accuracy"] for r in runs if "error" not in r and r.get("numeric_accuracy") is not None]
    null_accs = [r["null_prone_accuracy"] for r in runs if "error" not in r and r.get("null_prone_accuracy") is not None]
    prompt_tokens = [r.get("prompt_tokens", 0) for r in runs if "error" not in r and r.get("prompt_tokens", 0) > 0]
    completion_tokens = [r.get("completion_tokens", 0) for r in runs if "error" not in r and r.get("completion_tokens", 0) > 0]
    errors = [r for r in runs if "error" in r]

    if not accuracies:
        return {"error": "All runs failed", "runs": len(runs), "failures": len(errors)}

    stats = {
        "runs": len(runs),
        "failures": len(errors),
        "accuracy_mean": round(statistics.mean(accuracies), 1),
        "accuracy_median": round(statistics.median(accuracies), 1),
        "accuracy_stdev": round(statistics.stdev(accuracies), 1) if len(accuracies) >= 2 else 0.0,
        "accuracy_min": round(min(accuracies), 1),
        "accuracy_max": round(max(accuracies), 1),
        "time_mean": round(statistics.mean(times), 1),
        "time_stdev": round(statistics.stdev(times), 1) if len(times) >= 2 else 0.0,
        "per_run_accuracies": accuracies,
        "per_run_times": times,
    }

    if string_accs:
        stats["string_accuracy_mean"] = round(statistics.mean(string_accs), 1)
        stats["string_accuracy_stdev"] = round(statistics.stdev(string_accs), 1) if len(string_accs) >= 2 else 0.0
    if numeric_accs:
        stats["numeric_accuracy_mean"] = round(statistics.mean(numeric_accs), 1)
        stats["numeric_accuracy_stdev"] = round(statistics.stdev(numeric_accs), 1) if len(numeric_accs) >= 2 else 0.0
    if null_accs:
        stats["null_prone_accuracy_mean"] = round(statistics.mean(null_accs), 1)
    if prompt_tokens:
        stats["prompt_tokens_mean"] = round(statistics.mean(prompt_tokens), 0)
        stats["completion_tokens_mean"] = round(statistics.mean(completion_tokens), 0)
        stats["total_tokens_mean"] = round(statistics.mean([r.get("total_tokens", 0) for r in runs if "error" not in r]), 0)

    stats["sample_result"] = runs[0] if runs else {}
    return stats


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Parse args
    target_variants = VARIANTS
    target_entities = list(ENTITY_GROUND_TRUTH.keys())
    num_runs = 1
    do_ablation = False
    do_multi_instance = False
    target_models = list(MODEL_REGISTRY.keys())
    rag_modes = ["full_rag"]
    instance_modes = ["single"]

    args = sys.argv[1:]
    if "--models" in args or "-m" in args:
        flag = "--models" if "--models" in args else "-m"
        m_idx = args.index(flag) + 1
        if m_idx < len(args):
            target_models = [m.strip() for m in args[m_idx].split(",") if m.strip() in MODEL_REGISTRY]
    if "--variant" in args:
        v_idx = args.index("--variant") + 1
        target_variants = [args[v_idx]] if v_idx < len(args) else VARIANTS
    if "--entity" in args:
        e_idx = args.index("--entity") + 1
        target_entities = [args[e_idx]] if e_idx < len(args) else target_entities
    if "--runs" in args:
        r_idx = args.index("--runs") + 1
        num_runs = int(args[r_idx]) if r_idx < len(args) else 1
    if "--ablation" in args:
        do_ablation = True
        rag_modes = ["full_rag", "no_rag"]
    if "--multi-instance" in args:
        do_multi_instance = True
        instance_modes = ["single", "multi"]
    if "--quick" in args:
        num_runs = 1
        do_ablation = False
        do_multi_instance = False
        rag_modes = ["full_rag"]
        instance_modes = ["single"]

    parallel_workers = 1
    if "--parallel" in args:
        p_idx = args.index("--parallel") + 1
        parallel_workers = int(args[p_idx]) if p_idx < len(args) else 4

    skip_config = "--skip-config" in args

    # Filter out models with no API key
    active_models = {}
    for mkey in target_models:
        cfg = MODEL_REGISTRY[mkey]
        if cfg["api_key"]:
            active_models[mkey] = cfg
        else:
            print(f"SKIPPED: {mkey} — no API key (set DEEPSEEK_API_KEY env var)")

    if not active_models:
        print("ERROR: No models with valid API keys.")
        sys.exit(1)

    total_experiments = (len(active_models) * len(target_variants) * len(target_entities)
                         * len(rag_modes) * len(instance_modes) * num_runs)

    print("=" * 70)
    print("PAPER EVALUATION v2 — Multi-Model, Multi-Instance, Token-Aware")
    print("=" * 70)
    print(f"AI Agent: {AI_AGENT_BASE}")
    print(f"Models: {list(active_models.keys())}")
    print(f"Variants: {target_variants}")
    print(f"Entities: {target_entities}")
    print(f"RAG modes: {rag_modes}")
    print(f"Instance modes: {instance_modes}")
    print(f"Runs per experiment: {num_runs}")
    print(f"Total experiments: {total_experiments}")
    print(f"Est. time: ~{total_experiments * 10 // 60} min")
    print()

    client = httpx.Client(timeout=180)

    # Initialize field type classification (deferred to avoid ordering issues)
    global FIELD_TYPE_CLASSIFICATION
    if not FIELD_TYPE_CLASSIFICATION:
        for entity_name, gt in ENTITY_GROUND_TRUTH.items():
            FIELD_TYPE_CLASSIFICATION[entity_name] = {}
            clean_payload = load_variant_payload(entity_name, "clean")
            items_key = get_variant_items_key(entity_name, "clean")
            first_item = get_first_item(clean_payload, items_key)
            for cmsd_field, api_path in gt.items():
                parts = api_path.split(".")
                cur = first_item
                for p in parts:
                    if isinstance(cur, dict):
                        cur = cur.get(p)
                    else:
                        cur = None
                        break
                if cur is None:
                    FIELD_TYPE_CLASSIFICATION[entity_name][cmsd_field] = "null_prone"
                elif isinstance(cur, (int, float)) and not isinstance(cur, bool):
                    FIELD_TYPE_CLASSIFICATION[entity_name][cmsd_field] = "numeric"
                else:
                    FIELD_TYPE_CLASSIFICATION[entity_name][cmsd_field] = "string"

    all_grouped = {}  # {(model, entity, variant, rag_mode, inst_mode): [results]}
    model_status = {}  # {model_key: True/False}
    n = 0

    for model_key, model_cfg in active_models.items():
        model_name = model_cfg["name"]
        print(f"\n{'='*70}")
        print(f"MODEL: {model_name} ({model_key})")
        print(f"  host={model_cfg['host']}, provider={model_cfg['provider_type']}")
        print(f"{'='*70}")

        # Configure LLM for this model (skip if --skip-config)
        if skip_config:
            print(f"  Using pre-configured LLM (--skip-config)", flush=True)
            ok = True
        else:
            print(f"  Configuring LLM...", end=" ", flush=True)
            ok, detail = configure_llm(client, model_cfg)
            if ok:
                print("OK")
            else:
                print(f"FAILED: {str(detail)[:200]}")
                continue
        model_status[model_key] = ok

        # Build task list
        tasks = []
        for inst_mode in instance_modes:
            multi_inst = (inst_mode == "multi")
            if multi_inst and "legacy" not in [v.lower() for v in target_variants]:
                if len(target_variants) == 1 and target_variants[0] != "legacy":
                    continue
            for rag_mode in rag_modes:
                skip_rag = (rag_mode == "no_rag")
                for variant in target_variants:
                    if multi_inst and variant != "legacy":
                        continue
                    for entity_name in target_entities:
                        ground_truth = ENTITY_GROUND_TRUTH.get(entity_name)
                        if not ground_truth:
                            continue
                        key = (model_key, entity_name, variant, rag_mode, inst_mode)
                        all_grouped[key] = []
                        for run_i in range(1, num_runs + 1):
                            tasks.append({
                                "key": key,
                                "run_i": run_i,
                                "entity_name": entity_name,
                                "variant": variant,
                                "ground_truth": ground_truth,
                                "skip_rag": skip_rag,
                                "multi_inst": multi_inst,
                                "model_key": model_key,
                                "inst_mode": inst_mode,
                                "rag_mode": rag_mode,
                            })

        # Execute tasks in parallel
        print(f"  Running {len(tasks)} experiments with {parallel_workers} workers...")
        t_batch_start = time.time()
        completed = 0
        errors = 0

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            future_to_task = {}
            for task in tasks:
                future = executor.submit(
                    run_single_experiment,
                    httpx.Client(timeout=180),  # Each thread gets its own client
                    task["entity_name"],
                    task["variant"],
                    task["ground_truth"],
                    skip_rag=task["skip_rag"],
                    multi_instance=task["multi_inst"],
                )
                future_to_task[future] = task

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                completed += 1
                try:
                    result = future.result()
                except Exception as e:
                    result = {"error": str(e), "elapsed_seconds": 0}
                    errors += 1

                if "error" in result:
                    print(f"  [{completed}/{len(tasks)}] {task['model_key']}/{task['inst_mode']}"
                          f"/{task['rag_mode']}/{task['variant']}/{task['entity_name']}"
                          f" run={task['run_i']} ERROR: {result['error'][:100]}",
                          flush=True)
                    errors += 1
                else:
                    str_acc = result.get('string_accuracy', 'N/A')
                    num_acc = result.get('numeric_accuracy', 'N/A')
                    tok = result.get('total_tokens', 0)
                    print(f"  [{completed}/{len(tasks)}] {task['model_key']}/{task['inst_mode']}"
                          f"/{task['rag_mode']}/{task['variant']}/{task['entity_name']}"
                          f" run={task['run_i']} acc={result['accuracy']}%"
                          f" (str={str_acc}%, num={num_acc}%) tok={tok}"
                          f" in {result['elapsed_seconds']}s",
                          flush=True)

                all_grouped[task["key"]].append(result)

        batch_elapsed = time.time() - t_batch_start
        print(f"  Model batch done: {completed} experiments in {batch_elapsed:.0f}s "
              f"({errors} errors)", flush=True)

    client.close()

    # --- Aggregate statistics ---
    stats_by_key = {}
    for key, runs in all_grouped.items():
        stats_by_key[key] = compute_run_stats(runs)

    # --- Cross-model RAG comparison ---
    rag_by_model = {}
    for model_key in active_models:
        for rag_mode in rag_modes:
            mrag_key = f"{model_key}_{rag_mode}"
            mrag_runs = [(k, v) for k, v in stats_by_key.items()
                         if k[0] == model_key and k[3] == rag_mode
                         and k[4] == "single" and "error" not in v]
            if not mrag_runs:
                continue
            all_accs = [stats["accuracy_mean"] for _, stats in mrag_runs]
            all_string = [stats.get("string_accuracy_mean") for _, stats in mrag_runs
                          if stats.get("string_accuracy_mean") is not None]
            all_numeric = [stats.get("numeric_accuracy_mean") for _, stats in mrag_runs
                           if stats.get("numeric_accuracy_mean") is not None]
            rag_by_model[mrag_key] = {
                "model": model_key,
                "rag_mode": rag_mode,
                "experiments": len(mrag_runs),
                "avg_accuracy": round(statistics.mean(all_accs), 1) if all_accs else 0,
                "string_acc": round(statistics.mean(all_string), 1) if all_string else None,
                "numeric_acc": round(statistics.mean(all_numeric), 1) if all_numeric else None,
            }

    # --- Multi-instance impact (legacy variant only) ---
    multi_impact = {}
    for model_key in active_models:
        for rag_mode in rag_modes:
            single_key = (model_key, None, "legacy", rag_mode, "single")
            multi_key = (model_key, None, "legacy", rag_mode, "multi")

            single_runs = [(k, v) for k, v in stats_by_key.items()
                           if k[0] == model_key and k[2] == "legacy"
                           and k[3] == rag_mode and k[4] == "single" and "error" not in v]
            multi_runs = [(k, v) for k, v in stats_by_key.items()
                          if k[0] == model_key and k[2] == "legacy"
                          and k[3] == rag_mode and k[4] == "multi" and "error" not in v]

            if single_runs and multi_runs:
                s_acc = statistics.mean([s["accuracy_mean"] for _, s in single_runs])
                m_acc = statistics.mean([s["accuracy_mean"] for _, s in multi_runs])
                impact_key = f"{model_key}_{rag_mode}"
                multi_impact[impact_key] = {
                    "model": model_key,
                    "rag_mode": rag_mode,
                    "single_accuracy": round(s_acc, 1),
                    "multi_accuracy": round(m_acc, 1),
                    "delta": round(m_acc - s_acc, 1),
                }

    # --- Build final report ---
    report = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "harness_version": "v2",
            "ai_agent_url": AI_AGENT_BASE,
            "models_tested": list(active_models.keys()),
            "model_status": model_status,
            "variants_tested": target_variants,
            "entities_tested": target_entities,
            "rag_modes": rag_modes,
            "instance_modes": instance_modes,
            "runs_per_experiment": num_runs,
            "total_experiments": total_experiments,
            "successful": sum(1 for v in stats_by_key.values() if "error" not in v),
            "field_type_classification": {
                entity: {
                    "string_fields": sum(1 for t in types.values() if t == "string"),
                    "numeric_fields": sum(1 for t in types.values() if t == "numeric"),
                    "null_prone_fields": sum(1 for t in types.values() if t == "null_prone"),
                }
                for entity, types in FIELD_TYPE_CLASSIFICATION.items()
            },
        },
        "rag_by_model": rag_by_model,
        "multi_instance_impact": multi_impact,
        "detail_stats": {f"{k[0]}/{k[2]}/{k[3]}/{k[4]}": v for k, v in stats_by_key.items()},
    }

    # Save JSON report
    json_path = os.path.join(RESULTS_DIR, "evaluation_report_v2.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n\nReport saved: {json_path}")

    # --- Print summary ---
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")

    # RAG by model table
    if len(rag_modes) > 1:
        print(f"\n--- RAG Ablation by Model ---")
        print(f"{'Model':<14} {'RAG':<10} {'Exps':<6} {'Acc%':<8} {'Str%':<8} {'Num%':<8}")
        print("-" * 60)
        for key, s in sorted(rag_by_model.items()):
            print(f"{s['model']:<14} {s['rag_mode']:<10} {s['experiments']:<6} "
                  f"{s['avg_accuracy']:<8.1f} {s['string_acc'] or 'N/A':<8} "
                  f"{s['numeric_acc'] or 'N/A':<8}")

    # Multi-instance impact
    if multi_impact:
        print(f"\n--- Multi-Instance Impact (Legacy Variant) ---")
        print(f"{'Model':<14} {'RAG':<10} {'Single%':<10} {'Multi%':<10} {'Delta':<8}")
        print("-" * 55)
        for key, s in sorted(multi_impact.items()):
            sign = "+" if s["delta"] >= 0 else ""
            print(f"{s['model']:<14} {s['rag_mode']:<10} {s['single_accuracy']:<10.1f} "
                  f"{s['multi_accuracy']:<10.1f} {sign}{s['delta']:<7.1f}")

    # String vs numeric breakdown across all models
    print(f"\n--- Accuracy by Field Type (Single-instance, RAG) ---")
    print(f"{'Model':<14} {'Entity':<16} {'Overall':<8} {'String':<8} {'Numeric':<8} {'Null':<8}")
    print("-" * 65)
    for key, stats in sorted(stats_by_key.items()):
        if key[3] == "full_rag" and key[4] == "single" and "error" not in stats:
            model, entity = key[0], key[1]
            sample = stats.get("sample_result", {})
            s_acc = sample.get('string_accuracy')
            n_acc = sample.get('numeric_accuracy')
            np_acc = sample.get('null_prone_accuracy')
            print(f"{model:<14} {entity:<16} "
                  f"{stats['accuracy_mean']:<8.1f} "
                  f"{f'{s_acc:.1f}%' if s_acc is not None else 'N/A':<8} "
                  f"{f'{n_acc:.1f}%' if n_acc is not None else 'N/A':<8} "
                  f"{f'{np_acc:.1f}%' if np_acc is not None else 'N/A':<8}")

    # --- Generate markdown ---
    md_path = os.path.join(RESULTS_DIR, "evaluation_report_v2.md")
    with open(md_path, "w") as f:
        f.write(f"# Paper Evaluation Report v2 (n={num_runs})\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(f"**Models:** {', '.join(active_models.keys())}\n\n")
        f.write(f"**Total experiments:** {total_experiments}\n\n")

        # RAG ablation
        if len(rag_modes) > 1:
            f.write("## RAG Ablation by Model\n\n")
            f.write("| Model | RAG Mode | Experiments | Avg Accuracy | String Acc | Numeric Acc |\n")
            f.write("|---|---|---|---|---|---|\n")
            for key, s in sorted(rag_by_model.items()):
                f.write(f"| {s['model']} | {s['rag_mode']} | {s['experiments']} | "
                        f"{s['avg_accuracy']}% | {s['string_acc'] or 'N/A'}% | "
                        f"{s['numeric_acc'] or 'N/A'}% |\n")

        # Multi-instance
        if multi_impact:
            f.write("\n## Multi-Instance Impact (Legacy Variant)\n\n")
            f.write("| Model | RAG Mode | Single-instance | Multi-instance | Delta |\n")
            f.write("|---|---|---|---|---|\n")
            for key, s in sorted(multi_impact.items()):
                sign = "+" if s["delta"] >= 0 else ""
                f.write(f"| {s['model']} | {s['rag_mode']} | {s['single_accuracy']}% | "
                        f"{s['multi_accuracy']}% | {sign}{s['delta']}% |\n")

        # Field type breakdown
        f.write("\n## Accuracy by Field Type (Single-instance, Full RAG)\n\n")
        f.write("| Model | Entity | Overall | String | Numeric | Null-prone |\n")
        f.write("|---|---|---|---|---|---|\n")
        for key, stats in sorted(stats_by_key.items()):
            if key[3] == "full_rag" and key[4] == "single" and "error" not in stats:
                sample = stats.get("sample_result", {})
                f.write(f"| {key[0]} | {key[1]} | {stats['accuracy_mean']}% | "
                        f"{sample.get('string_accuracy', 'N/A')}% | "
                        f"{sample.get('numeric_accuracy', 'N/A')}% | "
                        f"{sample.get('null_prone_accuracy', 'N/A')}% |\n")

        f.write("\n## Field Type Classification\n\n")
        f.write("| Entity | String Fields | Numeric Fields | Null-prone Fields |\n")
        f.write("|---|---|---|---|\n")
        for entity, types in FIELD_TYPE_CLASSIFICATION.items():
            f.write(f"| {entity} | {sum(1 for t in types.values() if t == 'string')} | "
                    f"{sum(1 for t in types.values() if t == 'numeric')} | "
                    f"{sum(1 for t in types.values() if t == 'null_prone')} |\n")

    print(f"Markdown report saved: {md_path}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
