from __future__ import annotations

from fastapi import HTTPException

from app.schemas import Task, TaskCreate, TaskUpdate
from app.services.time_service import now_label


class TaskService:
    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def list(self) -> list[Task]:
        return list(self.tasks.values())

    def list_by_workspace(self, workspace_id: str) -> list[Task]:
        return [task for task in self.tasks.values() if task.workspace_id == workspace_id]

    def next_pending_task(self, workspace_id: str) -> Task | None:
        """Return the first Pending task for a workspace, in creation order."""
        for task in self.tasks.values():
            if task.workspace_id == workspace_id and task.status == "Pending":
                return task
        return None

    def count_completed(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id and task.status == "Completed"
        )

    def count_total(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id
        )

    def count_failed(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id and task.status == "Failed"
        )

    def count_running(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id and task.status == "Running"
        )

    def count_security_approved(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id and task.security_status == "Approved"
        )

    def count_security_rejected(self, workspace_id: str) -> int:
        return sum(
            1 for task in self.tasks.values()
            if task.workspace_id == workspace_id and task.security_status == "Rejected"
        )

    def count_output_files(self, workspace_id: str) -> int:
        """Count total output files across all tasks in a workspace."""
        return sum(
            len(task.output_files)
            for task in self.tasks.values()
            if task.workspace_id == workspace_id
        )

    def get_current_task(self, workspace_id: str) -> 'Task | None':
        """Return the currently Running task for a workspace.

        If no Running task, returns None (meaning idle/completed).
        """
        for task in self.tasks.values():
            if task.workspace_id == workspace_id and task.status == "Running":
                return task
        return None

    def average_task_duration(self, workspace_id: str) -> float | None:
        """Average duration in seconds for completed tasks in this workspace."""
        durations = [
            task.duration_seconds
            for task in self.tasks.values()
            if task.workspace_id == workspace_id
            and task.status == "Completed"
            and task.duration_seconds is not None
        ]
        if not durations:
            return None
        return sum(durations) / len(durations)

    def get(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    def create(self, payload: TaskCreate) -> Task:
        task_id = f"task-{len(self.tasks) + 1:03}"
        task = Task(
            id=task_id,
            title=payload.title,
            description=payload.description,
            assigned_agent=payload.assigned_agent,
            priority=payload.priority,
            status="Pending",
            created_at=now_label(),
            workspace_id=payload.workspace_id,
        )
        self.tasks[task_id] = task
        return task

    def update(self, payload: TaskUpdate) -> Task:
        task = self.get(payload.id)
        changes = payload.model_dump(exclude={"id"}, exclude_none=True)

        # ── Security Validation (P5) ─────────────────────────────────────
        # Only tasks with status "Completed" can have security_status set to "Approved".
        # Failed / Blocked / Pending / Running tasks CANNOT be Approved.
        if changes.get("security_status") == "Approved":
            effective_status = changes.get("status") or task.status
            if effective_status != "Completed":
                # Silently downgrade to Rejected with explanation
                changes["security_status"] = "Rejected"
                changes["security_notes"] = (
                    f"Cannot approve: task status is '{effective_status}', not 'Completed'. "
                    f"Only completed tasks are eligible for security approval."
                )

        # Auto-set started_at when transitioning to Running
        if changes.get("status") == "Running" and not task.started_at:
            changes.setdefault("started_at", now_label())

        # Auto-set completed_at and duration when completing
        if changes.get("status") == "Completed":
            if "completed_at" not in changes:
                changes["completed_at"] = now_label()
            if task.started_at and "duration_seconds" not in changes:
                from datetime import datetime
                try:
                    started = datetime.strptime(task.started_at, "%Y-%m-%d %H:%M:%S")
                    completed = datetime.strptime(changes["completed_at"], "%Y-%m-%d %H:%M:%S")
                    changes["duration_seconds"] = (completed - started).total_seconds()
                except (ValueError, TypeError):
                    pass

        updated = task.model_copy(update=changes)
        self.tasks[payload.id] = updated
        return updated

    def delete(self, task_id: str) -> None:
        self.get(task_id)
        del self.tasks[task_id]


task_service = TaskService()
