"""
Paper Evaluation Test Harness — Enhanced with n-run statistical analysis and RAG ablation.

Usage:
    python tests/paper_evaluation.py [--variant V] [--entity E] [--runs N] [--ablation]
    python tests/paper_evaluation.py --runs 5 --ablation  # Full study
    python tests/paper_evaluation.py --quick                # 1 run, RAG only (fast smoke test)

Output:
    tests/fixtures/results/evaluation_report.json  — full statistical data
    tests/fixtures/results/evaluation_report.md    — human-readable summary
"""

import json
import os
import sys
import time
import statistics
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
    TYPE_COERCION_REQUIRED,
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


def build_expected_api_path(ground_truth_mapping, variant):
    variant_map = VARIANT_API_PATH_MAP.get(variant, {})
    result = {}
    for cmsd_field, clean_path in ground_truth_mapping.items():
        result[cmsd_field] = variant_map.get(clean_path, clean_path)
    return result


def evaluate_mapping(llm_mapping, ground_truth, expected_paths, cmsd_entity, variant):
    gt_fields = set(ground_truth.keys())
    llm_fields = set(llm_mapping.keys())

    correct = 0
    incorrect = 0
    incorrect_details = []
    missed = 0
    missed_fields = []
    extra = 0
    extra_fields = []

    for field in gt_fields:
        expected_path = expected_paths.get(field, ground_truth[field])
        if field in llm_mapping:
            field_info = llm_mapping[field]
            if isinstance(field_info, dict):
                actual_path = field_info.get("api_path", "")
            else:
                actual_path = str(field_info)
            actual_path = actual_path.lstrip("$.") if actual_path.startswith("$.") else actual_path

            if actual_path == expected_path:
                correct += 1
            else:
                incorrect += 1
                incorrect_details.append({
                    "field": field, "expected": expected_path, "actual": actual_path,
                    "confidence": field_info.get("confidence", "?") if isinstance(field_info, dict) else "?",
                })
        else:
            missed += 1
            missed_fields.append({"field": field, "expected": expected_path})

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
        "confidence_distribution": conf_dist,
        "incorrect_details": incorrect_details,
        "missed_fields": missed_fields,
    }


def run_single_experiment(client, entity_name, variant, ground_truth, skip_rag=False):
    payload = load_variant_payload(entity_name, variant)
    items_key = get_variant_items_key(entity_name, variant)
    first_item = get_first_item(payload, items_key)

    rag_label = "no_rag" if skip_rag else "full_rag"
    data_point_name = f"Eval: {entity_name} ({variant}/{rag_label})"
    request_body = {
        "data_point_name": data_point_name,
        "cmsd_entity": entity_name,
        "skip_rag": skip_rag,
        "approved_payloads": [{
            "endpoint": f"/{entity_name.lower()}",
            "source_id": variant,
            "label": f"Variant {variant}",
            "raw_payload": first_item if isinstance(first_item, dict) else payload,
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

    mapping = response.get("mapping") or response.get("proposed_mapping", {})
    if isinstance(mapping, dict) and "mapping" in mapping:
        mapping = mapping["mapping"]

    expected_paths = build_expected_api_path(ground_truth, variant)
    result = evaluate_mapping(mapping, ground_truth, expected_paths, entity_name, variant)
    result["elapsed_seconds"] = round(elapsed, 1)
    result["rag_mode"] = rag_label
    result["rag_context_length"] = len(response.get("rag_context", "") or "")
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
    corrects = [r["correct"] for r in runs if "error" not in r]
    errors = [r for r in runs if "error" in r]

    if not accuracies:
        return {"error": "All runs failed", "runs": len(runs), "failures": len(errors)}

    return {
        "runs": len(runs),
        "failures": len(errors),
        "accuracy_mean": round(statistics.mean(accuracies), 1),
        "accuracy_median": round(statistics.median(accuracies), 1),
        "accuracy_stdev": round(statistics.stdev(accuracies), 1) if len(accuracies) >= 2 else 0.0,
        "accuracy_min": round(min(accuracies), 1),
        "accuracy_max": round(max(accuracies), 1),
        "correct_mean": round(statistics.mean(corrects), 1),
        "time_mean": round(statistics.mean(times), 1),
        "time_stdev": round(statistics.stdev(times), 1) if len(times) >= 2 else 0.0,
        "per_run_accuracies": accuracies,
        "per_run_times": times,
        "sample_result": runs[0],  # First run details for debugging
    }


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Parse args
    target_variants = VARIANTS
    target_entities = list(ENTITY_GROUND_TRUTH.keys())
    num_runs = 1
    do_ablation = False
    rag_modes = ["full_rag"]

    args = sys.argv[1:]
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
    if "--quick" in args:
        num_runs = 1
        do_ablation = False
        rag_modes = ["full_rag"]

    client = httpx.Client()
    llm_ready = check_llm_available(client)

    total_experiments = len(target_variants) * len(target_entities) * len(rag_modes) * num_runs

    print("=" * 60)
    print("PAPER EVALUATION TEST HARNESS (Enhanced)")
    print("=" * 60)
    print(f"AI Agent: {AI_AGENT_BASE}")
    print(f"LLM Configured: {llm_ready}")
    print(f"Variants: {target_variants}")
    print(f"Entities: {target_entities}")
    print(f"Runs per experiment: {num_runs}")
    print(f"RAG modes: {rag_modes}")
    print(f"Total experiments: {total_experiments}")
    print(f"Est. time: ~{total_experiments * 8 // 60} min")
    print()

    if not llm_ready:
        print("WARNING: LLM not configured. Attempting anyway - may fail.")
        print()

    all_grouped = {}  # {(entity, variant, rag_mode): [results]}
    n = 0

    for rag_mode in rag_modes:
        skip_rag = (rag_mode == "no_rag")
        print(f"\n{'='*60}")
        print(f"RAG MODE: {rag_mode}")
        print(f"{'='*60}")

        for variant in target_variants:
            for entity_name in target_entities:
                ground_truth = ENTITY_GROUND_TRUTH.get(entity_name)
                if not ground_truth:
                    continue

                key = (entity_name, variant, rag_mode)
                all_grouped[key] = []

                for run_i in range(1, num_runs + 1):
                    n += 1
                    print(f"  [{n}/{total_experiments}] {rag_mode}/{variant}/{entity_name} run={run_i}/{num_runs}...",
                          end=" ", flush=True)
                    result = run_single_experiment(client, entity_name, variant, ground_truth, skip_rag)

                    if "error" in result:
                        print(f"ERROR: {result['error'][:100]}")
                    else:
                        print(f"accuracy={result['accuracy']}% "
                              f"({result['correct']}/{result['ground_truth_fields']}) "
                              f"in {result['elapsed_seconds']}s")

                    all_grouped[key].append(result)

    client.close()

    # --- Aggregate statistics ---
    stats_by_key = {}
    for key, runs in all_grouped.items():
        stats_by_key[key] = compute_run_stats(runs)

    # --- Build per-RAG-mode summaries ---
    rag_summaries = {}
    for rag_mode in rag_modes:
        rag_runs = [(k, v) for k, v in stats_by_key.items() if k[2] == rag_mode and "error" not in v]
        if not rag_runs:
            continue

        total_correct = sum(v["correct_mean"] for _, v in rag_runs)
        total_gt = sum(runs[0]["ground_truth_fields"] for (k, _) in rag_runs for runs in [all_grouped[k]])

        # Recalculate total_gt from ground truth
        total_gt_calc = 0
        total_correct_calc = 0
        for (entity, variant, _), stats in rag_runs:
            gt = ENTITY_GROUND_TRUTH.get(entity, {})
            total_gt_calc += len(gt)
            total_correct_calc += stats["correct_mean"]

        all_accs = [stats["accuracy_mean"] for _, stats in rag_runs]
        rag_summaries[rag_mode] = {
            "experiments": len(rag_runs),
            "avg_accuracy": round(statistics.mean(all_accs), 1) if all_accs else 0,
            "median_accuracy": round(statistics.median(all_accs), 1) if all_accs else 0,
            "total_correct": round(total_correct_calc, 1),
            "total_ground_truth": total_gt_calc,
            "overall_accuracy": round(total_correct_calc / total_gt_calc * 100, 1) if total_gt_calc > 0 else 0,
        }

    # --- Build per-variant summaries ---
    variant_summaries = {}
    for variant in target_variants:
        for rag_mode in rag_modes:
            vkey = f"{variant}_{rag_mode}"
            vruns = [(k, v) for k, v in stats_by_key.items()
                     if k[1] == variant and k[2] == rag_mode and "error" not in v]
            if not vruns:
                continue
            all_accs = [stats["accuracy_mean"] for _, stats in vruns]
            all_times = [stats["time_mean"] for _, stats in vruns]
            variant_summaries[vkey] = {
                "variant": variant,
                "rag_mode": rag_mode,
                "experiments": len(vruns),
                "avg_accuracy": round(statistics.mean(all_accs), 1),
                "accuracy_stdev": round(statistics.stdev(all_accs), 1) if len(all_accs) >= 2 else 0,
                "avg_time": round(statistics.mean(all_times), 1),
            }

    # --- Build ablation comparison ---
    ablation_rows = []
    for entity in target_entities:
        row = {"entity": entity}
        for rag_mode in rag_modes:
            ekey = next((k for k in stats_by_key if k[0] == entity and k[2] == rag_mode), None)
            if ekey is None:
                # Aggregate across variants
                e_runs = [(k, v) for k, v in stats_by_key.items()
                          if k[0] == entity and k[2] == rag_mode and "error" not in v]
                if e_runs:
                    all_accs = [stats["accuracy_mean"] for _, stats in e_runs]
                    row[f"{rag_mode}_acc"] = round(statistics.mean(all_accs), 1)
                    row[f"{rag_mode}_stdev"] = round(statistics.stdev(all_accs), 1) if len(all_accs) >= 2 else 0
        if len(row) > 1:
            # Calculate delta
            if "full_rag_acc" in row and "no_rag_acc" in row:
                row["rag_delta"] = round(row["full_rag_acc"] - row["no_rag_acc"], 1)
            ablation_rows.append(row)

    # --- Build final report ---
    report = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ai_agent_url": AI_AGENT_BASE,
            "llm_configured": llm_ready,
            "variants_tested": target_variants,
            "entities_tested": target_entities,
            "rag_modes": rag_modes,
            "runs_per_experiment": num_runs,
            "total_experiments": total_experiments,
            "successful": sum(1 for v in stats_by_key.values() if "error" not in v),
        },
        "rag_summaries": rag_summaries,
        "variant_summaries": variant_summaries,
        "ablation_comparison": ablation_rows,
        "detail_stats": {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in stats_by_key.items()},
    }

    # Save JSON report
    json_path = os.path.join(RESULTS_DIR, "evaluation_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {json_path}")

    # --- Print summary ---
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")

    # RAG comparison table
    if len(rag_modes) > 1:
        print(f"\n{'RAG Mode':<12} {'Exps':<6} {'Avg Acc%':<10} {'Median%':<10} {'Overall%':<10}")
        print("-" * 50)
        for rag_mode in rag_modes:
            if rag_mode in rag_summaries:
                s = rag_summaries[rag_mode]
                print(f"{rag_mode:<12} {s['experiments']:<6} {s['avg_accuracy']:<10.1f} "
                      f"{s['median_accuracy']:<10.1f} {s['overall_accuracy']:<10.1f}")

        # Delta
        if "full_rag" in rag_summaries and "no_rag" in rag_summaries:
            delta = rag_summaries["full_rag"]["avg_accuracy"] - rag_summaries["no_rag"]["avg_accuracy"]
            print(f"\n>>> RAG contribution: +{delta:.1f}% accuracy improvement <<<")

    # Per-variant table
    print(f"\n{'Variant':<12} {'RAG':<10} {'Exps':<6} {'Avg Acc%':<10} {'Stdev':<8} {'Avg Time':<10}")
    print("-" * 60)
    for vkey, vs in sorted(variant_summaries.items()):
        print(f"{vs['variant']:<12} {vs['rag_mode']:<10} {vs['experiments']:<6} "
              f"{vs['avg_accuracy']:<10.1f} {vs['accuracy_stdev']:<8.1f} {vs['avg_time']:<10.1f}s")

    # Ablation table
    if ablation_rows:
        print(f"\n{'Entity':<16} {'No RAG %':<10} {'Full RAG %':<12} {'Delta':<8}")
        print("-" * 50)
        for row in ablation_rows:
            nr = row.get("no_rag_acc", 0)
            fr = row.get("full_rag_acc", 0)
            delta = row.get("rag_delta", 0)
            print(f"{row['entity']:<16} {nr:<10.1f} {fr:<12.1f} +{delta:<7.1f}")

    # --- Generate markdown ---
    md_path = os.path.join(RESULTS_DIR, "evaluation_report.md")
    with open(md_path, "w") as f:
        f.write(f"# Paper Evaluation Report (n={num_runs})\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(f"**Total experiments:** {total_experiments}\n\n")

        if len(rag_modes) > 1:
            f.write("## RAG Ablation Study\n\n")
            f.write("| RAG Mode | Avg Accuracy | Median Accuracy | Overall Accuracy |\n")
            f.write("|---|---|---|---|\n")
            for rag_mode in rag_modes:
                if rag_mode in rag_summaries:
                    s = rag_summaries[rag_mode]
                    f.write(f"| {rag_mode} | {s['avg_accuracy']}% | {s['median_accuracy']}% | {s['overall_accuracy']}% |\n")
            if "full_rag" in rag_summaries and "no_rag" in rag_summaries:
                delta = rag_summaries["full_rag"]["avg_accuracy"] - rag_summaries["no_rag"]["avg_accuracy"]
                f.write(f"\n**RAG contribution: +{delta:.1f}% accuracy improvement**\n\n")

        f.write("## Per-Variant Results\n\n")
        f.write("| Variant | RAG Mode | Avg Accuracy | Stdev | Avg Time |\n")
        f.write("|---|---|---|---|---|\n")
        for vkey, vs in sorted(variant_summaries.items()):
            f.write(f"| {vs['variant']} | {vs['rag_mode']} | {vs['avg_accuracy']}% | {vs['accuracy_stdev']} | {vs['avg_time']}s |\n")

        if ablation_rows:
            f.write("\n## Ablation by Entity\n\n")
            f.write("| Entity | No RAG | Full RAG | Delta |\n")
            f.write("|---|---|---|---|\n")
            for row in ablation_rows:
                nr = row.get("no_rag_acc", 0)
                fr = row.get("full_rag_acc", 0)
                delta = row.get("rag_delta", 0)
                f.write(f"| {row['entity']} | {nr}% | {fr}% | +{delta}% |\n")

    print(f"Markdown report saved: {md_path}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
