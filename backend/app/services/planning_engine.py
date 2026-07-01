"""
Planning Engine — transforms coarse architecture tasks into hierarchical engineering plans.

Generates:
  - Hierarchical structure: Epic -> Feature -> Story -> Task
  - Stable UIDs (e.g., TASK-FE-001)
  - Acceptance criteria
  - Complexity scores (XS, S, M, L, XL)
  - Context estimation and dependencies
  - Engineering metadata
  - Engineering standards (Initiative 2)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("planning_engine")


class PlanningEngine:
    """Enriches architecture task proposals into structured engineering plans."""

    def __init__(self):
        self.counters: dict[str, int] = {}

    def _next_uid(self, prefix: str) -> str:
        count = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = count
        return f"TASK-{prefix}-{count:03d}"

    def reset_counters(self) -> None:
        self.counters = {}

    def plan(self, architecture_tasks: list[dict], spec: dict) -> list[dict]:
        """Transform coarse architecture tasks into enriched hierarchical task specifications.

        Parameters
        ----------
        architecture_tasks : list[dict]
            Coarse tasks from architecture generation.
        spec : dict
            Project specification dictionary.

        Returns
        -------
        list[dict]
            Enriched task specifications with hierarchy, UIDs, acceptance criteria,
            complexity, and engineering standards.
        """
        from app.services.engineering_standards import engineering_standards_engine

        self.reset_counters()
        enriched_tasks: list[dict] = []
        project_name = spec.get("project_name", "Project")
        frontend_tech = spec.get("frontend", "React + Vite")
        backend_tech = spec.get("backend", False)

        for task in architecture_tasks:
            title = task.get("title", "").strip()
            desc = task.get("description", "").strip()
            priority = task.get("priority", "Medium")

            # Determine Layer & Epic
            title_lower = title.lower()
            if any(k in title_lower for k in ["auth", "login", "register", "security"]):
                prefix = "AUTH"
                epic = "Security & Authentication"
                feature = "User Authentication"
                complexity = "M"
                context = ["spec.json", "auth/config.py"]
            elif any(k in title_lower for k in ["backend", "api", "database", "model", "endpoint", "server"]):
                prefix = "BE"
                epic = "Backend API & Data Layer"
                feature = "Core REST API"
                complexity = "L" if backend_tech else "M"
                context = ["spec.json", "backend/main.py"]
            elif any(k in title_lower for k in ["integration", "connect", "fetch", "client"]):
                prefix = "INT"
                epic = "System Integration"
                feature = "Frontend-Backend Communication"
                complexity = "M"
                context = ["spec.json", "src/services/apiClient.js"]
            elif any(k in title_lower for k in ["test", "qa", "jest", "vitest"]):
                prefix = "QA"
                epic = "Quality Assurance"
                feature = "Automated Testing"
                complexity = "S"
                context = ["spec.json"]
            elif any(k in title_lower for k in ["polish", "deploy", "optimize", "performance", "seo"]):
                prefix = "OPS"
                epic = "Deployment & Optimization"
                feature = "Production Readiness"
                complexity = "S"
                context = ["spec.json", "index.html"]
            else:
                prefix = "FE"
                epic = "Frontend Infrastructure & UI"
                feature = "Core User Interface"
                complexity = "M"
                context = ["spec.json", "src/App.jsx", "src/index.css"]

            uid = self._next_uid(prefix)
            story = f"Implement {title}"

            # Generate default acceptance criteria
            acceptance_criteria = [
                f"Successfully completes: {title}",
                "No syntax or runtime errors introduced",
                f"Adheres to project specifications for {project_name}"
            ]
            if prefix == "FE":
                acceptance_criteria.append("Responsive layout works across desktop and mobile screen sizes")
            elif prefix == "BE":
                acceptance_criteria.append("API endpoints return correct HTTP status codes and payloads")
            elif prefix == "AUTH":
                acceptance_criteria.append("Unauthorized access is properly restricted")

            enriched_task = {
                "title": title,
                "description": desc,
                "priority": priority,
                "task_uid": uid,
                "epic": epic,
                "feature": feature,
                "story": story,
                "objective": f"Engineering objective: {title}",
                "expected_output": task.get("expected_output", f"Completed implementation of {title}"),
                "acceptance_criteria": acceptance_criteria,
                "complexity": complexity,
                "estimated_context": context,
                "context_dependencies": [],
                "engineering_metadata": {
                    "layer": prefix,
                    "estimated_files_count": 3 if complexity in ["L", "XL"] else 1,
                    "risk_level": "High" if prefix in ["AUTH", "BE"] else "Low"
                }
            }

            # ── Initiative 2: Attach Engineering Standards ────────────────
            engineering_standards_engine.enrich_task(enriched_task, spec)

            enriched_tasks.append(enriched_task)

        logger.info("PlanningEngine enriched %d coarse tasks with UIDs, hierarchy, and engineering standards", len(enriched_tasks))
        return enriched_tasks


planning_engine = PlanningEngine()
