"""
Execution Logger — structured build logging to .agentos/logs/.

Writes JSON-line logs per agent per workspace.
Supports reading logs back for the /logs/{workspace_id} endpoint.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from app.services.time_service import now_label

_AGENT_LOG_FILES = {
    "Builder Agent": "builder.log",
    "Security Agent": "security.log",
    "Build Orchestrator": "orchestrator.log",
}


class ExecutionLogger:
    """Writes and reads structured execution logs."""

    def log(
        self,
        workspace_path: str,
        agent: str,
        event: str,
        task_id: str | None = None,
        details: str = "",
    ) -> None:
        """Append a structured log entry to the agent's log file."""
        log_dir = os.path.join(workspace_path.replace("/", os.sep), ".agentos", "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = _AGENT_LOG_FILES.get(agent, "general.log")
        log_path = os.path.join(log_dir, log_file)

        entry = {
            "timestamp": now_label(),
            "agent": agent,
            "task_id": task_id,
            "event": event,
            "details": details,
        }

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError:
            pass  # Don't break the pipeline if logging fails

    def read_logs(
        self,
        workspace_id: str,
        agent_filter: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Read logs for a workspace. Returns newest-first."""
        from app.services.workspace_service import workspace_service

        try:
            workspace = workspace_service.get(workspace_id)
        except Exception:
            return []

        log_dir = os.path.join(workspace.path.replace("/", os.sep), ".agentos", "logs")
        if not os.path.exists(log_dir):
            return []

        entries: list[dict] = []

        # Determine which files to read
        if agent_filter and agent_filter in _AGENT_LOG_FILES:
            files = [_AGENT_LOG_FILES[agent_filter]]
        else:
            files = list(_AGENT_LOG_FILES.values()) + ["general.log"]

        for log_file in files:
            log_path = os.path.join(log_dir, log_file)
            if not os.path.exists(log_path):
                continue
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except OSError:
                pass

        # Sort newest first and apply limit
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return entries[:limit]


# ── Singleton ─────────────────────────────────────────────────────────────

execution_logger = ExecutionLogger()
