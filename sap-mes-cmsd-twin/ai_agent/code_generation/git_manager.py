"""
Git Manager — Atomic commits, rollback, and branch management.
All agent-generated code stays on feature/agentic-rag branch.
Never commits to main. Supports revert on failure.
"""

import json
import logging
import os
import subprocess
import time
from typing import Any

from ..config import PROJECT_ROOT, REPORTS_DIR

logger = logging.getLogger("ai-agent.git-manager")

FEATURE_BRANCH = "feature/agentic-rag"


class GitManager:
    """Manages Git operations for agent-generated code — atomic, safe, auditable."""

    def __init__(self, repo_root: str | None = None):
        # In Docker, CMSD_TWIN_REPO_PATH points to the bind-mounted git repo
        # On host, default to walking up from PROJECT_ROOT to find .git
        if repo_root:
            self.repo_root = os.path.abspath(repo_root)
        elif os.environ.get("CMSD_TWIN_REPO_PATH"):
            self.repo_root = os.path.abspath(os.environ["CMSD_TWIN_REPO_PATH"])
        else:
            self.repo_root = os.path.abspath(PROJECT_ROOT)
        self._git_repo = self._find_repo_root()

    def _find_repo_root(self) -> str | None:
        """Find the git repo root by walking up directories."""
        current = self.repo_root
        for _ in range(10):
            if os.path.isdir(os.path.join(current, ".git")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return None

    def _run_git(self, *args: str, cwd: str | None = None) -> tuple[int, str, str]:
        """Run a git command, return (returncode, stdout, stderr)."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -1, "", "git not found — is it installed?"

    def ensure_feature_branch(self) -> dict[str, Any]:
        """Ensure we're on feature/agentic-rag branch, create if needed."""
        if not self._git_repo:
            return {"ok": False, "error": "Not a git repository"}

        # Check current branch
        rc, current_branch, err = self._run_git("branch", "--show-current")
        if rc != 0:
            return {"ok": False, "error": f"Failed to get current branch: {err}"}

        if current_branch == FEATURE_BRANCH:
            return {"ok": True, "branch": FEATURE_BRANCH, "action": "already_on_branch"}

        # Try to switch to feature branch
        rc, _, err = self._run_git("checkout", FEATURE_BRANCH)
        if rc == 0:
            return {"ok": True, "branch": FEATURE_BRANCH, "action": "switched"}

        # Create the branch
        rc, _, err = self._run_git("checkout", "-b", FEATURE_BRANCH)
        if rc == 0:
            return {"ok": True, "branch": FEATURE_BRANCH, "action": "created"}

        return {"ok": False, "error": f"Failed to create/switch branch: {err}"}

    def atomic_commit(
        self,
        files: dict[str, str],
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Atomically write files and commit them.
        1. Write files to disk
        2. git add
        3. git commit
        4. Save report
        Returns {committed, commit_hash}.
        """
        if not self._git_repo:
            # Fallback: just write files without git
            return self._write_files_only(files, metadata)

        # Step 0: Ensure we're on correct branch
        branch_result = self.ensure_feature_branch()
        if not branch_result.get("ok"):
            logger.warning(f"Branch check failed: {branch_result.get('error')} — writing files only")
            return self._write_files_only(files, metadata)

        # Step 1: Write generated files
        written = []
        for file_path, content in files.items():
            full_path = os.path.join(self.repo_root, file_path) if not os.path.isabs(file_path) else file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Backup original
            backup_path = full_path + ".agent-backup"
            if os.path.exists(full_path):
                os.rename(full_path, backup_path)

            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                written.append(file_path)
            except Exception as e:
                # Restore backup
                if os.path.exists(backup_path):
                    os.rename(backup_path, full_path)
                logger.error(f"Failed to write {file_path}: {e}")
                return {"committed": False, "commit_hash": None, "error": f"Write failed: {e}"}

        # Step 2: git add
        for fp in written:
            self._run_git("add", fp)

        # Step 3: git commit
        rc, commit_hash, err = self._run_git("commit", "-m", message)
        if rc != 0:
            # Attempt to recover — unstage
            for fp in written:
                self._run_git("reset", "HEAD", fp)
            logger.error(f"Git commit failed: {err}")
            return {"committed": False, "commit_hash": None, "error": err, "files_written": written}

        # Step 4: Save generation report
        report = self._save_report(message, commit_hash, written, metadata)

        # Clean up backups
        for fp in written:
            full_path = os.path.join(self.repo_root, fp) if not os.path.isabs(fp) else fp
            backup_path = full_path + ".agent-backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)

        logger.info(f"Committed {commit_hash[:8]}: {message}")
        return {
            "committed": True,
            "commit_hash": commit_hash,
            "files_changed": written,
            "report_path": report,
        }

    def revert_last_commit(self) -> dict[str, Any]:
        """Revert the last commit on the feature branch."""
        rc, _, err = self._run_git("revert", "HEAD", "--no-edit")
        if rc == 0:
            return {"reverted": True, "message": "Last commit reverted"}
        return {"reverted": False, "error": err}

    def get_diff_last_commit(self) -> dict[str, Any]:
        """Get the diff of the last commit."""
        rc, diff, err = self._run_git("diff", "HEAD~1", "HEAD")
        if rc == 0:
            return {"diff": diff}
        return {"diff": "", "error": err}

    def _write_files_only(self, files: dict[str, str], metadata: dict | None) -> dict[str, Any]:
        """Fallback: write files without git commit."""
        written = []
        for file_path, content in files.items():
            full_path = os.path.join(self.repo_root, file_path) if not os.path.isabs(file_path) else file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            backup_path = full_path + ".agent-backup"
            if os.path.exists(full_path):
                os.rename(full_path, backup_path)
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                written.append(file_path)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
            except Exception as e:
                if os.path.exists(backup_path):
                    os.rename(backup_path, full_path)
                logger.error(f"Failed to write {file_path}: {e}")

        report_path = self._save_report("No-git write", "N/A", written, metadata)
        return {
            "committed": False,
            "commit_hash": None,
            "files_written": written,
            "report_path": report_path,
            "note": "Git not available — files written directly",
        }

    def _save_report(
        self, message: str, commit_hash: str, files: list[str], metadata: dict | None
    ) -> str:
        """Save a generation report to .agent-reports/."""
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        report_filename = f"{timestamp}_{metadata.get('data_point', 'unknown') if metadata else 'unknown'}.json"
        report_path = os.path.join(REPORTS_DIR, report_filename)

        report_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "commit_message": message,
            "commit_hash": commit_hash,
            "files_changed": files,
            "metadata": metadata or {},
        }

        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"Report saved: {report_path}")
        return report_path


# Singleton
git_manager = GitManager()
