"""
Task Validator — quality gate for atomic tasks.

Runs after decomposition and before task creation.
Rejects tasks that are:
  - Duplicates (identical or near-identical titles)
  - Vague (too short or matching vague patterns)
  - Multi-objective (joins two unrelated objectives with "and")
  - Planning tasks (contain planning verbs)
  - Recursive (title matches the original coarse task)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("task_validator")


# ── Vague Task Patterns ───────────────────────────────────────────────────

_VAGUE_PATTERNS = [
    r"^build\s+(the\s+)?website$",
    r"^build\s+(the\s+)?app$",
    r"^build\s+(the\s+)?application$",
    r"^build\s+(the\s+)?project$",
    r"^implement\s+features$",
    r"^implement\s+core\s+features$",
    r"^set\s+up\s+project$",
    r"^create\s+project$",
    r"^build\s+frontend$",
    r"^build\s+backend$",
    r"^build\s+everything$",
    r"^do\s+everything$",
    r"^finish\s+project$",
    r"^complete\s+project$",
    r"^make\s+it\s+work$",
]

# ── Planning Verbs ────────────────────────────────────────────────────────

_PLANNING_VERBS = [
    "define product scope",
    "design system architecture",
    "design architecture",
    "gather requirements",
    "analyze requirements",
    "analyse requirements",
    "research technologies",
    "plan development",
    "document goals",
    "confirm scope",
    "scope definition",
]


class ValidationResult:
    """Result of task validation."""

    def __init__(self):
        self.accepted: list[dict] = []
        self.rejected: list[dict] = []
        self.warnings: list[str] = []

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    def to_dict(self) -> dict:
        return {
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "rejected": [
                {"title": r["task"]["title"], "reason": r["reason"]}
                for r in self.rejected
            ],
            "warnings": self.warnings,
        }


class TaskValidator:
    """Validates atomic tasks before they are created in the system."""

    def validate(
        self,
        tasks: list[dict],
        original_titles: list[str] | None = None,
    ) -> ValidationResult:
        """Validate a list of atomic tasks.

        Parameters
        ----------
        tasks : list[dict]
            Atomic tasks from the decomposer.
        original_titles : list[str] | None
            Titles of the original coarse tasks, for recursion detection.

        Returns
        -------
        ValidationResult
            Contains accepted tasks, rejected tasks with reasons, and warnings.
        """
        result = ValidationResult()
        seen_titles: set[str] = set()
        seen_uids: set[str] = set()
        original_set = {t.strip().lower() for t in (original_titles or [])}

        for task in tasks:
            title = task.get("title", "").strip()
            title_lower = title.lower()
            rejection_reason = None

            # ── Check 1: Empty or very short title ────────────────────
            if not title or len(title.split()) < 2:
                rejection_reason = f"Title too short ({len(title.split())} words): '{title}'"

            # ── Check 2: Duplicate detection ──────────────────────────
            elif title_lower in seen_titles:
                rejection_reason = f"Duplicate title: '{title}'"

            # ── Check 3: Vagueness check ──────────────────────────────
            elif self._is_vague(title_lower):
                rejection_reason = f"Vague task: '{title}'"

            # ── Check 4: Multi-objective check ────────────────────────
            elif self._is_multi_objective(title):
                rejection_reason = f"Multi-objective task (contains 'and' joining separate objectives): '{title}'"
                result.warnings.append(
                    f"Consider splitting: '{title}'"
                )

            # ── Check 5: Planning task filter ─────────────────────────
            elif self._is_planning_task(title_lower):
                rejection_reason = f"Planning task (not for Builder): '{title}'"

            # ── Check 6: Recursion guard ──────────────────────────────
            elif title_lower in original_set:
                rejection_reason = f"Recursive — matches original coarse task: '{title}'"

            # ── Check 7: Complexity check ─────────────────────────────
            complexity = task.get("complexity")
            if not rejection_reason and complexity and complexity not in {"XS", "S", "M", "L", "XL"}:
                rejection_reason = f"Invalid complexity '{complexity}': '{title}'"

            # ── Check 8: Duplicate UID check ──────────────────────────
            uid = task.get("task_uid")
            if not rejection_reason and uid:
                if uid in seen_uids:
                    rejection_reason = f"Duplicate task_uid '{uid}': '{title}'"
                else:
                    seen_uids.add(uid)

            if rejection_reason:
                result.rejected.append({"task": task, "reason": rejection_reason})
                logger.info("Rejected task: %s", rejection_reason)
            else:
                seen_titles.add(title_lower)
                if uid:
                    seen_uids.add(uid)
                result.accepted.append(task)
                if not task.get("acceptance_criteria"):
                    result.warnings.append(f"Task missing acceptance criteria: '{title}'")
                if not task.get("expected_output"):
                    result.warnings.append(f"Task missing expected output: '{title}'")

                # ── Check 9: Engineering Standards Gate (Initiative 2) ────
                # Soft gate — warnings only to avoid disrupting existing flows.
                meta = task.get("engineering_metadata") or {}
                if not meta.get("engineering_standards"):
                    result.warnings.append(f"Task missing engineering standards: '{title}'")
                if not meta.get("required_deliverables"):
                    result.warnings.append(f"Task missing required deliverables: '{title}'")
                if not meta.get("testing_expectations"):
                    result.warnings.append(f"Task missing testing expectations: '{title}'")
                if not meta.get("security_expectations"):
                    result.warnings.append(f"Task missing security expectations: '{title}'")

        # ── Warnings for potential issues ─────────────────────────────
        if len(result.accepted) == 0 and len(tasks) > 0:
            result.warnings.append("ALL tasks were rejected — decomposition may need review")

        if len(result.accepted) > 150:
            result.warnings.append(
                f"Very high task count ({len(result.accepted)}) — verify this is intentional"
            )

        if self._has_cycle(result.accepted):
            result.warnings.append("Circular dependency cycle detected in accepted tasks DAG")

        logger.info(
            "Validation complete: %d accepted, %d rejected, %d warnings",
            result.accepted_count,
            result.rejected_count,
            len(result.warnings),
        )

        return result

    # ── Internal checks ───────────────────────────────────────────────────

    def _is_vague(self, title_lower: str) -> bool:
        """Check if a title matches vague task patterns."""
        # Word count check (fewer than 3 words is suspicious)
        if len(title_lower.split()) < 3:
            # Allow short but specific titles like "Create Navbar"
            specific_verbs = ["create", "implement", "add", "update", "fix", "configure", "install"]
            if not any(title_lower.startswith(v) for v in specific_verbs):
                return True

        return any(re.match(p, title_lower) for p in _VAGUE_PATTERNS)

    def _is_multi_objective(self, title: str) -> bool:
        """Check if a title joins two unrelated objectives with 'and'."""
        # Split on " and " and check if both halves look like tasks
        if " and " not in title.lower():
            return False

        parts = re.split(r"\s+and\s+", title, flags=re.IGNORECASE)
        if len(parts) < 2:
            return False

        # If both parts start with implementation verbs, it's multi-objective
        impl_verbs = ["create", "build", "implement", "add", "set up", "configure", "install", "deploy"]
        verb_count = sum(
            1 for part in parts
            if any(part.strip().lower().startswith(v) for v in impl_verbs)
        )

        return verb_count >= 2

    def _is_planning_task(self, title_lower: str) -> bool:
        """Check if a title represents a planning task."""
        return any(pv in title_lower for pv in _PLANNING_VERBS)

    def _has_cycle(self, tasks: list[dict]) -> bool:
        """Detect circular dependencies in task list."""
        adj = {t["title"]: t.get("dependencies", []) for t in tasks}
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for dep in adj.get(node, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for t in tasks:
            if t["title"] not in visited:
                if dfs(t["title"]):
                    return True
        return False


# ── Singleton ─────────────────────────────────────────────────────────────

task_validator = TaskValidator()
