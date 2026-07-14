"""
Code Generation Orchestrator — Manages the 3-agent loop:
Writer → Reviewer → Tester, with retry logic and rollback safety.
"""

import json
import logging
import time
import uuid
from typing import Any

from ..agents.writer_agent import writer_agent
from ..agents.reviewer_agent import reviewer_agent
from ..agents.tester_agent import tester_agent
from ..rag.retriever import retriever
from .git_manager import git_manager

logger = logging.getLogger("ai-agent.code-generation")


class CodeGenerationOrchestrator:
    """Orchestrates the 3-agent code generation feedback loop."""

    def __init__(self):
        self.max_retries = 3
        self._mapping_progress: dict[str, Any] = {}

    async def generate_from_mapping(
        self,
        confirmed_mapping: dict[str, Any],
        existing_code: dict[str, str],
        cmsd_schema_context: str = "",
    ) -> dict[str, Any]:
        """
        Run the full 3-agent loop for a single confirmed mapping.
        Returns {success, files, report, commit_hash}.
        """
        mapping_id = f"gen-{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        logger.info(f"Starting generation pipeline {mapping_id} for {confirmed_mapping.get('data_point', 'unknown')}")

        # Phase 1: Writer Agent
        writer_result = await writer_agent.generate(
            confirmed_mapping=confirmed_mapping,
            existing_code=existing_code,
            cmsd_schema_context=cmsd_schema_context,
        )

        if "error" in writer_result:
            return self._build_error_response("Writer agent failed", writer_result, start_time)

        generated_files = {
            f.get("path", ""): f.get("full_content", "")
            for f in writer_result.get("files", [])
        }

        # Phase 2: Reviewer Agent
        reviewer_result = await reviewer_agent.review(
            original_files=existing_code,
            generated_files=generated_files,
            confirmed_mapping=confirmed_mapping,
        )

        # If rejected, retry writer with feedback (max 3 total writer attempts)
        retry_count = 0
        while reviewer_result.get("recommendation") == "REJECT" and retry_count < self.max_retries:
            retry_count += 1
            logger.info(f"Reviewer rejected — retrying Writer (attempt {retry_count}/{self.max_retries})")
            writer_result = await writer_agent.generate(
                confirmed_mapping=confirmed_mapping,
                existing_code=existing_code,
                cmsd_schema_context=cmsd_schema_context,
                reviewer_feedback=reviewer_result,
            )
            if "error" not in writer_result:
                generated_files = {
                    f.get("path", ""): f.get("full_content", "")
                    for f in writer_result.get("files", [])
                }
                reviewer_result = await reviewer_agent.review(
                    original_files=existing_code,
                    generated_files=generated_files,
                    confirmed_mapping=confirmed_mapping,
                )

        if reviewer_result.get("recommendation") == "REJECT":
            return self._build_error_response(
                f"Reviewer rejected after {retry_count} writer retries",
                {"writer": writer_result, "reviewer": reviewer_result},
                start_time,
            )

        # Phase 3: Tester Agent (sandbox execution)
        tester_result = tester_agent.test(generated_files)

        if not tester_result.get("pass"):
            logger.warning(f"Tester found issues: {tester_result.get('summary')}")

        # Phase 4: Git commit (atomic, on feature branch)
        git_result = {"committed": False, "commit_hash": None}
        try:
            data_point = confirmed_mapping.get("data_point", "unknown")
            git_result = git_manager.atomic_commit(
                files=generated_files,
                message=f"[AGENT] {data_point} mapping applied ({mapping_id})",
                metadata={
                    "mapping_id": mapping_id,
                    "data_point": data_point,
                    "cmsd_entity": confirmed_mapping.get("cmsd_entity", ""),
                    "writer_result": writer_result,
                    "reviewer_result": reviewer_result,
                    "tester_result": tester_result,
                },
            )
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            git_result = {"committed": False, "commit_hash": None, "error": str(e)}

        elapsed = round(time.time() - start_time, 2)

        report = {
            "mapping_id": mapping_id,
            "success": tester_result.get("pass", False) and git_result.get("committed", False),
            "data_point": confirmed_mapping.get("data_point", ""),
            "cmsd_entity": confirmed_mapping.get("cmsd_entity", ""),
            "writer": writer_result,
            "reviewer": reviewer_result,
            "tester": tester_result,
            "git": git_result,
            "elapsed_seconds": elapsed,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Track progress
        self._mapping_progress[confirmed_mapping.get("data_point", mapping_id)] = {
            "mapping_id": mapping_id,
            "status": "completed" if report["success"] else "failed",
            "generated_at": report["timestamp"],
        }

        return report

    async def generate_batch(
        self,
        mappings: list[dict[str, Any]],
        existing_code: dict[str, str],
    ) -> dict[str, Any]:
        """
        Run the 3-agent loop for a batch of confirmed mappings.
        Accumulates changes across all mappings and produces a single
        unified diff + report.
        """
        start_time = time.time()
        all_files: dict[str, str] = {}
        all_reports: list[dict] = []
        files_generated: list[str] = []
        overall_success = True

        for mapping in mappings:
            confirmed = {
                "data_point": mapping.get("data_point", mapping.get("mapping", {}).get("data_point_name", "unknown")),
                "cmsd_entity": mapping.get("cmsd_entity", mapping.get("mapping", {}).get("cmsd_entity", "unknown")),
                "api_endpoint": mapping.get("mapping", {}).get("api_endpoint", ""),
                "proposed_mapping": mapping.get("mapping", {}).get("proposed_mapping", mapping.get("mapping", {})),
            }
            cmsd_context = mapping.get("cmsd_schema_context", "")

            result = await self.generate_from_mapping(
                confirmed_mapping=confirmed,
                existing_code=existing_code,
                cmsd_schema_context=cmsd_context,
            )
            all_reports.append(result)

            if result.get("success"):
                # Accumulate generated files
                writer_files = result.get("writer", {}).get("files", [])
                for f in writer_files:
                    path = f.get("path", "")
                    content = f.get("full_content", "")
                    if path and content:
                        all_files[path] = content
                        if path not in files_generated:
                            files_generated.append(path)
                # Update existing_code in memory for next iteration
                for path, content in all_files.items():
                    existing_code[path] = content
            else:
                overall_success = False
                logger.warning(f"Mapping {confirmed['data_point']} failed: {result.get('error')}")

        # Single atomic commit for all accumulated files
        git_result = {"committed": False, "commit_hash": None}
        if all_files:
            try:
                data_points = [m.get("data_point", "?") for m in mappings]
                dp_summary = ", ".join(data_points[:5])
                if len(data_points) > 5:
                    dp_summary += f" +{len(data_points) - 5} more"
                git_result = git_manager.atomic_commit(
                    files=all_files,
                    message=f"[AGENT] Batch: {dp_summary}",
                    metadata={
                        "batch_size": len(mappings),
                        "data_points": data_points,
                        "reports": all_reports,
                    },
                )
                # Restore backup if commit failed
                if not git_result.get("committed"):
                    logger.warning("Batch git commit failed — files may be in backup")
            except Exception as e:
                logger.error(f"Batch git commit error: {e}")
                git_result = {"committed": False, "commit_hash": None, "error": str(e)}

        elapsed = round(time.time() - start_time, 2)

        return {
            "success": overall_success and git_result.get("committed", False),
            "batch_size": len(mappings),
            "files_generated": files_generated,
            "reports": all_reports,
            "git": git_result,
            "elapsed_seconds": elapsed,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def get_progress(self) -> dict[str, Any]:
        """Get overall mapping progress."""
        total = len(self._mapping_progress)
        completed = sum(1 for v in self._mapping_progress.values() if v.get("status") == "completed")
        return {
            "total_mappings": total,
            "completed": completed,
            "failed": total - completed,
            "mappings": self._mapping_progress,
        }

    def _build_error_response(
        self, message: str, details: dict, start_time: float
    ) -> dict[str, Any]:
        return {
            "success": False,
            "error": message,
            "details": details,
            "elapsed_seconds": round(time.time() - start_time, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


# Singleton
code_gen_orchestrator = CodeGenerationOrchestrator()
