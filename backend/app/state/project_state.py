"""
Project State Manager — the single source of truth for every conversation.

The LLM never owns state. This module does.
State persists across the full conversation lifecycle and is keyed by conversation_id.
"""

from __future__ import annotations

import uuid
from copy import deepcopy

# ── Phases ────────────────────────────────────────────────────────────────

PHASE_DISCOVERY = "REQUIREMENT_DISCOVERY"
PHASE_ARCHITECTURE = "ARCHITECTURE_GENERATION"
PHASE_APPROVAL = "AWAITING_APPROVAL"
PHASE_CREATION = "PROJECT_CREATION"

# ── Completion weights (sum = 100) ────────────────────────────────────────
# Each field contributes a fixed number of points to requirements_progress.

FIELD_WEIGHTS: dict[str, int] = {
    "project_name": 10,
    "project_type": 12,
    "theme": 5,
    "purpose": 10,
    "target_users": 12,
    "core_features": 15,
    "frontend": 10,
    "backend": 8,
    "database": 6,
    "authentication": 5,
    "deployment": 7,
}

MAX_CLARIFICATION_ROUNDS = 5


def _blank_state(conversation_id: str) -> dict:
    return {
        "conversation_id": conversation_id,
        # ── Project knowledge ────────────────────────────
        "project_name": None,
        "project_type": None,
        "theme": None,
        "purpose": None,
        "target_users": None,
        "core_features": [],
        "frontend": None,
        "backend": None,
        "database": None,
        "authentication": None,
        "deployment": None,
        # ── Question tracking ────────────────────────────
        "asked_questions": {},       # field -> bool
        "answered_questions": {},     # field -> bool
        "clarification_rounds": 0,
        # ── Lifecycle ────────────────────────────────────
        "requirements_complete": False,
        "architecture_generated": False,
        "approved": False,
        "architecture": None,
        # ── Computed (updated by recalculate) ────────────
        "current_phase": PHASE_DISCOVERY,
        "requirements_progress": 0,
        "confidence_score": 5,
        # ── Chat history (kept lean for LLM context) ─────
        "messages": [],
    }


class ProjectStateManager:
    """Manages per-conversation project state.  Thread-safe for a single-process server."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def get_or_create(self, conversation_id: str | None = None) -> dict:
        if conversation_id and conversation_id in self._store:
            return self._store[conversation_id]
        new_id = conversation_id or str(uuid.uuid4())
        state = _blank_state(new_id)
        self._store[new_id] = state
        return state

    def get(self, conversation_id: str) -> dict | None:
        return self._store.get(conversation_id)

    # ── Mutation helpers ──────────────────────────────────────────────────

    def update_field(self, state: dict, field: str, value) -> None:
        """Set a single field and mark it as answered."""
        if field == "core_features" and isinstance(value, list):
            existing = state.get("core_features") or []
            merged = list(dict.fromkeys(existing + value))   # dedupe, preserve order
            state["core_features"] = merged
        else:
            state[field] = value
        state["answered_questions"][field] = True
        self.recalculate(state)

    def update_many(self, state: dict, updates: dict) -> None:
        """Batch-update from an extractor result dict."""
        for field, value in updates.items():
            if value is not None and value != "" and value != []:
                self.update_field(state, field, value)

    def add_message(self, state: dict, role: str, content: str) -> None:
        state["messages"].append({"role": role, "content": content})

    def increment_clarification(self, state: dict) -> None:
        state["clarification_rounds"] += 1

    def mark_question_asked(self, state: dict, field: str) -> None:
        state["asked_questions"][field] = True

    # ── Completion & confidence ───────────────────────────────────────────

    def recalculate(self, state: dict) -> None:
        """Recompute requirements_progress, confidence_score, current_phase."""

        # -- Progress --
        total_weight = sum(FIELD_WEIGHTS.values())
        earned = 0
        for field, weight in FIELD_WEIGHTS.items():
            val = state.get(field)
            if field == "core_features":
                if val and len(val) > 0:
                    earned += weight
            elif val is not None and val != "":
                earned += weight
        progress = min(int((earned / total_weight) * 100), 100)
        state["requirements_progress"] = progress

        # -- Requirements complete --
        # Requirements are complete when: project_name, theme, purpose, audience(target_users), frontend, deployment != null.
        if not state.get("requirements_complete"):
            required_fields = ["project_name", "theme", "purpose", "target_users", "frontend", "deployment"]
            all_required_present = all(
                state.get(f) is not None and state.get(f) != "" and state.get(f) != []
                for f in required_fields
            )
            
            if all_required_present or state["clarification_rounds"] >= MAX_CLARIFICATION_ROUNDS:
                state["requirements_complete"] = True

        # -- Confidence --
        msg_count = len([m for m in state["messages"] if m["role"] == "user"])
        confidence = progress
        if msg_count >= 2:
            confidence = min(confidence + 10, 95)
        if state["architecture_generated"]:
            confidence = max(confidence, 90)
        if state["approved"]:
            confidence = 100
        state["confidence_score"] = confidence

        # -- Phase --
        self._update_phase(state)

    def _update_phase(self, state: dict) -> None:
        # Never move backwards.
        if state["approved"]:
            state["current_phase"] = PHASE_CREATION
            return
            
        if state["architecture_generated"] or state["current_phase"] == PHASE_APPROVAL:
            state["current_phase"] = PHASE_APPROVAL
            return
            
        if state["requirements_complete"] or state["current_phase"] == PHASE_ARCHITECTURE:
            state["current_phase"] = PHASE_ARCHITECTURE
            return
            
        state["current_phase"] = PHASE_DISCOVERY

    # ── Query helpers ─────────────────────────────────────────────────────

    def missing_fields(self, state: dict) -> list[str]:
        """Return fields that are still None/empty AND have not been answered."""
        missing = []
        for field in FIELD_WEIGHTS:
            val = state.get(field)
            is_empty = val is None or val == "" or (isinstance(val, list) and len(val) == 0)
            already_answered = state["answered_questions"].get(field, False)
            if is_empty and not already_answered:
                missing.append(field)
                
        # Deployment is always the final question
        if "deployment" in missing:
            missing.remove("deployment")
            missing.append("deployment")
            
        return missing

    def unanswered_unasked_fields(self, state: dict) -> list[str]:
        """Fields that are unknown AND have never been asked about."""
        return [
            f for f in self.missing_fields(state)
            if not state["asked_questions"].get(f, False)
        ]

    def state_summary_for_llm(self, state: dict) -> str:
        """Compact text summary of current project state for the LLM prompt."""
        lines = ["Current Project State:"]
        for field in FIELD_WEIGHTS:
            val = state.get(field)
            label = field.replace("_", " ").title()
            if field == "core_features" and val:
                lines.append(f"  {label}: {', '.join(val)}")
            elif val is not None and val != "":
                lines.append(f"  {label}: {val}")
            else:
                lines.append(f"  {label}: [unknown]")
        lines.append(f"  Requirements Progress: {state['requirements_progress']}%")
        lines.append(f"  Confidence: {state['confidence_score']}%")
        return "\n".join(lines)

    def recent_messages(self, state: dict, count: int = 8) -> list[dict]:
        """Return the last N messages for LLM context."""
        return state["messages"][-count:]


# ── Singleton ─────────────────────────────────────────────────────────────

project_state_manager = ProjectStateManager()
