"""Sprint 5: Project Context Memory (Feature 3)

Persistent workspace memory that stores project analysis, architecture,
framework, component list, task history, and design decisions.
Context is available to any service that needs workspace awareness.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("project_context")


class ProjectContextStore:
    """In-memory persistent context for each workspace."""

    def __init__(self):
        self._contexts: dict[str, dict] = {}

    def get_context(self, workspace_id: str) -> dict:
        """Get the full context for a workspace."""
        if workspace_id not in self._contexts:
            self._contexts[workspace_id] = self._empty_context(workspace_id)
        return self._contexts[workspace_id]

    def update_context(self, workspace_id: str, **updates) -> dict:
        """Merge updates into the workspace context."""
        ctx = self.get_context(workspace_id)
        for key, value in updates.items():
            if key in ctx:
                if isinstance(ctx[key], list) and isinstance(value, list):
                    ctx[key].extend(value)
                elif isinstance(ctx[key], dict) and isinstance(value, dict):
                    ctx[key].update(value)
                else:
                    ctx[key] = value
            else:
                ctx[key] = value
        ctx["last_updated"] = datetime.now().isoformat()
        return ctx

    def store_analysis(self, workspace_id: str, analysis: dict) -> dict:
        """Store a project analysis result into the workspace context."""
        return self.update_context(
            workspace_id,
            project_name=analysis.get("project_name", ""),
            framework=analysis.get("framework", "Unknown"),
            components=analysis.get("components", []),
            pages=analysis.get("pages", []),
            routes=analysis.get("routes", []),
            services=analysis.get("services", []),
            dependencies=analysis.get("dependencies", {}),
            file_counts=analysis.get("file_counts", {}),
            risk_assessment=analysis.get("risk_assessment", {}),
        )

    def record_decision(self, workspace_id: str, decision: str, reason: str = "") -> dict:
        """Record an important design decision for a workspace."""
        ctx = self.get_context(workspace_id)
        ctx["decisions"].append({
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        ctx["last_updated"] = datetime.now().isoformat()
        return ctx

    def record_edit_event(self, workspace_id: str, event_type: str, details: str = "") -> dict:
        """Record an event on the edit timeline."""
        ctx = self.get_context(workspace_id)
        ctx["edit_timeline"].append({
            "event": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })
        ctx["last_updated"] = datetime.now().isoformat()
        return ctx

    def add_task_history(self, workspace_id: str, task_id: str, task_title: str, status: str) -> dict:
        """Record a task completion in the workspace history."""
        ctx = self.get_context(workspace_id)
        ctx["task_history"].append({
            "task_id": task_id,
            "title": task_title,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })
        ctx["last_updated"] = datetime.now().isoformat()
        return ctx

    def delete_context(self, workspace_id: str) -> None:
        """Remove context for a deleted workspace."""
        self._contexts.pop(workspace_id, None)

    def list_contexts(self) -> list[str]:
        """List all workspace IDs with stored context."""
        return list(self._contexts.keys())

    @staticmethod
    def _empty_context(workspace_id: str) -> dict:
        """Create an empty context structure."""
        return {
            "workspace_id": workspace_id,
            "project_name": "",
            "framework": "Unknown",
            "architecture": "",
            "components": [],
            "pages": [],
            "routes": [],
            "services": [],
            "dependencies": {},
            "file_counts": {},
            "risk_assessment": {},
            "decisions": [],
            "task_history": [],
            "edit_timeline": [],
            "file_history": [],
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
        }


project_context = ProjectContextStore()
