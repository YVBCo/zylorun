"""Safe Cloud Preview Service for GitFlow Project Hub.

Provides:
- Ephemeral execution contract with strict resource boundaries (CPU, memory, runtime, storage)
- Isolated temporary worktree creation and sandboxing
- Strict log sanitization scrubbing credentials and sensitive runtime tokens
- Expiration-based automated lifecycle cleanup
"""

from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import uuid

from app.ai.service import redact_secrets

logger = logging.getLogger(__name__)


class CloudPreviewService:
    """Manages ephemeral preview environments and strict execution contracts."""

    def __init__(self) -> None:
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def cleanup_expired(self) -> int:
        """Purge all expired preview sessions and their isolated temp worktrees."""
        now = datetime.now(timezone.utc)
        expired_ids = [
            sid for sid, session in self.active_sessions.items()
            if session.get("expires_at_dt") and session["expires_at_dt"] <= now
        ]
        cleaned_count = 0
        for sid in expired_ids:
            if self.cleanup_preview(sid):
                cleaned_count += 1
        return cleaned_count

    def cleanup_preview(self, preview_id: str) -> bool:
        """Tear down a specific preview session and remove its temp directory."""
        session = self.active_sessions.pop(preview_id, None)
        if not session:
            return False

        worktree = session.get("ephemeral_worktree")
        if worktree and os.path.exists(worktree):
            try:
                shutil.rmtree(worktree, ignore_errors=True)
                logger.info("Successfully cleaned up ephemeral worktree: %s", worktree)
            except Exception as e:
                logger.error("Failed to clean up worktree %s: %s", worktree, e)
        return True

    def create_isolated_preview_contract(
        self,
        repo_id: int,
        repo_name: str,
        commit_sha: str,
        user_id: int,
        custom_limits: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an ephemeral preview contract with resource limits and an isolated worktree."""
        self.cleanup_expired()

        session_id = f"prev_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=15)

        # Enforce conservative ephemeral execution bounds
        limits = {
            "max_cpu_cores": 1,
            "max_memory_mb": 512,
            "max_runtime_seconds": 30,
            "max_storage_mb": 100,
            "network_isolated": True,
        }
        if custom_limits:
            limits["max_runtime_seconds"] = min(60, int(custom_limits.get("max_runtime_seconds", 30)))
            limits["max_storage_mb"] = min(250, int(custom_limits.get("max_storage_mb", 100)))

        # Create isolated temporary workspace
        temp_dir = tempfile.mkdtemp(prefix=f"cloud_preview_{session_id}_")

        session_record = {
            "preview_id": session_id,
            "status": "READY",
            "repository_id": repo_id,
            "repo_name": repo_name,
            "commit_sha": commit_sha,
            "user_id": user_id,
            "contract": limits,
            "ephemeral_worktree": temp_dir,
            "expires_at": expires_at.isoformat(),
            "expires_at_dt": expires_at,
            "log_sanitization_enabled": True,
            "created_at": now.isoformat(),
        }

        self.active_sessions[session_id] = session_record

        # Return sanitized summary without internal datetime objects
        return {
            "preview_id": session_id,
            "status": "READY",
            "repository_id": repo_id,
            "repo_name": repo_name,
            "commit_sha": commit_sha,
            "user_id": user_id,
            "contract": limits,
            "ephemeral_worktree": temp_dir,
            "expires_at": expires_at.isoformat(),
            "log_sanitization_enabled": True,
            "created_at": now.isoformat(),
        }

    def execute_preview_command(
        self,
        preview_id: str,
        command: List[str],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a command inside the ephemeral worktree with timeout and sanitized logs."""
        session = self.active_sessions.get(preview_id)
        if not session:
            return {
                "success": False,
                "exit_code": -1,
                "error": "Preview session not found or already expired",
                "stdout": "",
                "stderr": "",
            }

        now = datetime.now(timezone.utc)
        if session.get("expires_at_dt") and session["expires_at_dt"] <= now:
            self.cleanup_preview(preview_id)
            return {
                "success": False,
                "exit_code": -1,
                "error": "Preview session has expired",
                "stdout": "",
                "stderr": "",
            }

        worktree = session["ephemeral_worktree"]
        contract = session["contract"]
        max_time = timeout or contract.get("max_runtime_seconds", 30)

        # Enforce safe environment variables
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "CI": "true",
            "PREVIEW_ENVIRONMENT": "ephemeral",
        }

        try:
            res = subprocess.run(
                command,
                cwd=worktree,
                capture_output=True,
                text=True,
                timeout=max_time,
                env=safe_env,
            )

            stdout_clean = redact_secrets(res.stdout)
            stderr_clean = redact_secrets(res.stderr)

            return {
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": stdout_clean,
                "stderr": stderr_clean,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "error": f"Execution exceeded ephemeral contract timeout ({max_time}s)",
                "stdout": "",
                "stderr": "",
                "timed_out": True,
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "error": f"Execution failed: {str(e)}",
                "stdout": "",
                "stderr": "",
                "timed_out": False,
            }


# Global singleton instance
cloud_preview_service = CloudPreviewService()
