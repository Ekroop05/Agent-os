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
