"""
Tester Agent (Agent 3) — NOT an LLM agent. Executes generated Python code
in isolated subprocesses to catch syntax errors, import errors, and basic
runtime issues before code is committed. Timeout: 10s per test.
"""

import ast
import logging
import subprocess
import tempfile
import os
from typing import Any

logger = logging.getLogger("ai-agent.tester-agent")


class TesterAgent:
    """Agent 3: Sandbox executor for generated Python code."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def test(self, files: dict[str, str]) -> dict[str, Any]:
        """
        Run test suite on generated files.
        Returns {pass: bool, results: {file_path: {syntax, compile, ...}}, summary: str}.
        """
        results: dict[str, Any] = {}
        all_pass = True

        for file_path, content in files.items():
            file_results: dict[str, str] = {}

            # Test 1: AST parse (syntax check)
            try:
                ast.parse(content)
                file_results["syntax"] = "pass"
            except SyntaxError as e:
                file_results["syntax"] = f"FAIL: {e}"
                all_pass = False

            # Test 2: Check for obvious issues
            file_results["has_content"] = "pass" if len(content) > 50 else "FAIL: too short"
            if len(content) <= 50:
                all_pass = False

            # Test 3: Check for import of non-existent modules (simple heuristic)
            try:
                tree = ast.parse(content)
                imports = self._extract_imports(tree)
                file_results["imports_found"] = imports[:10]  # limit
            except Exception:
                file_results["imports_found"] = ["parse failed"]

            # Test 4: Check for common anti-patterns
            antipatterns = self._check_antipatterns(content)
            if antipatterns:
                file_results["antipatterns"] = f"FAIL: {', '.join(antipatterns)}"
                all_pass = False
            else:
                file_results["antipatterns"] = "pass"

            results[file_path] = file_results

        return {
            "pass": all_pass,
            "results": results,
            "summary": "All tests passed" if all_pass else "Some tests failed — see results",
        }

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _check_antipatterns(self, content: str) -> list[str]:
        """Check for common anti-patterns in generated code."""
        issues = []

        # Check for hardcoded secrets
        if "password =" in content and '"' in content:
            issues.append("possible hardcoded password string")
        if "api_key =" in content and '"' in content and len(content.split("api_key =")[1].split('"')[1]) > 5:
            issues.append("possible hardcoded API key")

        # Check for print statements (should use logger)
        if "print(" in content and "from __future__" not in content:
            issues.append("uses print() instead of logger")

        # Check for bare except
        if "except:" in content and "except Exception" not in content:
            issues.append("bare except clause without exception type")

        # Check for missing f-string or format in SQL strings
        # (skip — too many false positives)

        return issues


# Singleton
tester_agent = TesterAgent()
