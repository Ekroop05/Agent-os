"""
Task Graph Logger — persists the full planning trace.

Writes `.agentos/planning/task_graph.json` as the source of truth
for how architecture tasks were decomposed into atomic tasks.

Stores:
  - Original architecture tasks
  - Expansion log (which coarse task → which atomic tasks)
  - Final task list with metadata
  - Dependency graph
  - Validation report
  - Statistics
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.services.time_service import now_label

logger = logging.getLogger("task_graph")


class TaskGraph:
    """Persists planning trace to disk."""

    def save(
        self,
        workspace_path: str,
        architecture_tasks: list[dict],
        expansion_log: list[dict],
        final_tasks: list[dict],
        validation_report: dict,
    ) -> str:
        """Write the task graph to .agentos/planning/task_graph.json.

        Parameters
        ----------
        workspace_path : str
            The workspace root path (forward-slash style).
        architecture_tasks : list[dict]
            The original coarse task_breakdown from architecture.
        expansion_log : list[dict]
            Log of how each coarse task was expanded.
        final_tasks : list[dict]
            The validated, ordered atomic tasks.
        validation_report : dict
            Output from task_validator.validate().to_dict().

        Returns
        -------
        str
            The absolute path to the written JSON file.
        """
        # Build dependency graph
        dependency_graph = {}
        for task in final_tasks:
            dependency_graph[task["title"]] = task.get("dependencies", [])

        # Build the full graph document
        graph = {
            "generated_at": now_label(),
            "architecture_tasks": [
                t.get("title", "Unknown") for t in architecture_tasks
            ],
            "expansion_log": expansion_log,
            "final_tasks": [
                {
                    "title": t["title"],
                    "type": t.get("type", "unknown"),
                    "expected_output": t.get("expected_output", ""),
                    "dependencies": t.get("dependencies", []),
                    "priority": t.get("priority", "Medium"),
                }
                for t in final_tasks
            ],
            "dependency_graph": dependency_graph,
            "validation_report": validation_report,
            "stats": {
                "original_count": len(architecture_tasks),
                "expanded_count": sum(
                    len(entry.get("expanded_to", []))
                    for entry in expansion_log
                    if entry.get("action") == "decomposed"
                ),
                "filtered_planning_count": sum(
                    1 for entry in expansion_log
                    if entry.get("action") == "filtered_planning_task"
                ),
                "feature_expansion_count": sum(
                    len(entry.get("expanded_to", []))
                    for entry in expansion_log
                    if entry.get("action") == "feature_expansion"
                ),
                "final_count": len(final_tasks),
                "rejected_count": validation_report.get("rejected_count", 0),
                "warnings": validation_report.get("warnings", []),
            },
        }

        # Write to disk
        native_path = workspace_path.replace("/", os.sep)
        planning_dir = os.path.join(native_path, ".agentos", "planning")
        os.makedirs(planning_dir, exist_ok=True)

        graph_path = os.path.join(planning_dir, "task_graph.json")

        try:
            with open(graph_path, "w", encoding="utf-8") as f:
                json.dump(graph, f, indent=2, default=str)
            logger.info("Wrote task graph to %s", graph_path)
        except OSError as e:
            logger.warning("Could not write task graph: %s", e)

        return graph_path

    def read(self, workspace_path: str) -> dict | None:
        """Read the task graph from disk. Returns None if not found."""
        native_path = workspace_path.replace("/", os.sep)
        graph_path = os.path.join(native_path, ".agentos", "planning", "task_graph.json")

        if not os.path.exists(graph_path):
            return None

        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read task graph: %s", e)
            return None


# ── Singleton ─────────────────────────────────────────────────────────────

task_graph = TaskGraph()
