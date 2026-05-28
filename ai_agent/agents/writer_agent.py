"""
Writer Agent (Agent 1) — Generates code for api_client.py and factory.py
based on confirmed field mappings. Uses structured JSON input/output.
Temperature: 0.1, max 3 retries on failure.
"""

import json
import logging
from typing import Any

from ..llm import llm_client
from ..config import MAX_GENERATION_RETRIES

logger = logging.getLogger("ai-agent.writer-agent")

SYSTEM_PROMPT = """You are an expert Python code generator for the CMSD (Core Manufacturing Simulation Data) digital twin system.

Your task: Given a confirmed field mapping between an API endpoint and a CMSD entity, generate the COMPLETE updated source code for two files:
1. cmsd_twin_service/api_client.py — HTTP client with async methods
2. cmsd_twin_service/factory.py — CMSDFactory that builds CMSD Pydantic models

RULES (strict):
1. PRESERVE ALL existing code. Only ADD or MODIFY methods related to the new data point.
2. Do NOT remove any existing methods or imports.
3. Follow the EXISTING code style: async/await for API calls, same import patterns, same helper functions (_to_decimal, _to_duration, etc.).
4. For api_client.py: Add a new async method that calls the endpoint and returns the JSON.
5. For factory.py: Add a new _build_* method and integrate it into the build() method.
6. Use proper httpx error handling (try/except or .raise_for_status()).
7. Include ALL type hints.
8. The CMSD Pydantic model imports must use the same pattern as existing code.

OUTPUT FORMAT — valid JSON only:
{
  "files": [
    {
      "path": "cmsd_twin_service/api_client.py",
      "full_content": "<COMPLETE file content, not just the diff>"
    },
    {
      "path": "cmsd_twin_service/factory.py",
      "full_content": "<COMPLETE file content, not just the diff>"
    }
  ],
  "summary": "Brief description of changes made",
  "new_methods": ["list of new method names added"],
  "modified_methods": ["list of existing methods modified"]
}

IMPORTANT: Output ONLY the JSON object. No markdown, no explanation text outside the JSON."""


class WriterAgent:
    """Agent 1: Generates updated api_client.py and factory.py from confirmed mappings."""

    async def generate(
        self,
        confirmed_mapping: dict[str, Any],
        existing_code: dict[str, str],
        cmsd_schema_context: str = "",
        reviewer_feedback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate code from a confirmed field mapping.
        If reviewer_feedback is provided, this is a retry with corrections.
        Returns the structured generation result.
        """
        user_prompt = self._build_user_prompt(
            confirmed_mapping, existing_code, cmsd_schema_context, reviewer_feedback
        )

        for attempt in range(1, MAX_GENERATION_RETRIES + 1):
            try:
                logger.info(f"Writer agent attempt {attempt}/{MAX_GENERATION_RETRIES}")
                result = llm_client.chat_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.1,
                )
                # Validate structure
                self._validate_output(result)
                result["attempt"] = attempt
                return result
            except Exception as e:
                logger.warning(f"Writer agent attempt {attempt} failed: {e}")
                if attempt == MAX_GENERATION_RETRIES:
                    return {
                        "error": f"Writer agent failed after {MAX_GENERATION_RETRIES} attempts: {e}",
                        "files": [],
                        "attempt": attempt,
                    }
                # Add error context to prompt for retry
                user_prompt += f"\n\nPREVIOUS ATTEMPT FAILED with: {e}\nPlease fix the JSON structure and try again."

        return {"error": "Unexpected writer agent failure", "files": [], "attempt": 0}

    def _build_user_prompt(
        self,
        confirmed_mapping: dict[str, Any],
        existing_code: dict[str, str],
        cmsd_schema_context: str,
        reviewer_feedback: dict[str, Any] | None,
    ) -> str:
        parts = []

        parts.append(f"## Confirmed Field Mapping\n{json.dumps(confirmed_mapping, indent=2)}")

        parts.append(f"\n## Existing api_client.py\n```python\n{existing_code.get('api_client.py', '# File not provided')}\n```")

        parts.append(f"\n## Existing factory.py\n```python\n{existing_code.get('factory.py', '# File not provided')}\n```")

        if cmsd_schema_context:
            parts.append(f"\n## CMSD Schema Context\n{cmsd_schema_context[:1500]}")

        if reviewer_feedback:
            parts.append(f"\n## Reviewer Feedback (FIX THESE ISSUES)\n{json.dumps(reviewer_feedback, indent=2)}")

        parts.append("\nGenerate the updated api_client.py and factory.py files.")
        return "\n".join(parts)

    @staticmethod
    def _validate_output(result: dict[str, Any]):
        """Validate the writer agent output structure."""
        if "files" not in result:
            raise ValueError("Writer output missing 'files' key")

        files = result["files"]
        if not isinstance(files, list) or len(files) == 0:
            raise ValueError("Writer output 'files' must be a non-empty list")

        valid_paths = {"cmsd_twin_service/api_client.py", "cmsd_twin_service/factory.py"}
        generated_paths = set()
        for file_entry in files:
            path = file_entry.get("path", "")
            content = file_entry.get("full_content", "")
            if path not in valid_paths:
                raise ValueError(f"Writer generated invalid file path: {path}")
            if not content or len(content) < 50:
                raise ValueError(f"Writer generated empty/too-short content for {path}")
            generated_paths.add(path)

        if len(generated_paths) < 1:
            raise ValueError("Writer generated no valid files")


# Singleton
writer_agent = WriterAgent()
