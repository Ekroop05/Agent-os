from __future__ import annotations

from fastapi import HTTPException

from app.schemas import Workspace, WorkspaceCreate
from app.services.time_service import now_label

DEFAULT_PROJECT_ROOT = "D:/Projects"


def slugify(value: str) -> str:
    slug = "".join(character if character.isalnum() else "-" for character in value.strip())
    return "-".join(part for part in slug.split("-") if part) or "Generated-Project"


class WorkspaceService:
    def __init__(self):
        self.workspaces: dict[str, Workspace] = {}
        self.project_root = DEFAULT_PROJECT_ROOT

    def list(self) -> list[Workspace]:
        return list(self.workspaces.values())

    def get(self, workspace_id: str) -> Workspace:
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    def create(self, payload: WorkspaceCreate) -> Workspace:
        workspace_id = f"workspace-{slugify(payload.name).lower()}"
        path = payload.path or self.path_for_project(payload.name)
        workspace = Workspace(
            id=workspace_id,
            name=payload.name,
            description=payload.description,
            status="Active",
            active_agents=payload.active_agents,
            task_count=0,
            created_at=now_label(),
            path=self.normalize_project_path(path),
        )
        self.workspaces[workspace_id] = workspace
        return workspace

    def update(self, workspace_id: str, **changes) -> Workspace:
        workspace = self.get(workspace_id)
        updated = workspace.model_copy(update={key: value for key, value in changes.items() if value is not None})
        self.workspaces[workspace_id] = updated
        return updated

    def delete(self, workspace_id: str) -> None:
        self.get(workspace_id)
        del self.workspaces[workspace_id]

    def set_project_root(self, project_root: str) -> str:
        cleaned = project_root.strip().replace("\\", "/").rstrip("/")
        if not cleaned:
            raise HTTPException(status_code=400, detail="Project root is required")
        self.project_root = cleaned
        return self.project_root

    def path_for_project(self, project_name: str) -> str:
        return f"{self.project_root}/{slugify(project_name)}"

    def normalize_project_path(self, path: str) -> str:
        normalized = path.replace("\\", "/").rstrip("/")
        root = self.project_root.rstrip("/")
        if normalized != root and not normalized.startswith(f"{root}/"):
            raise HTTPException(status_code=400, detail="Workspace path must be inside configured project root")
        return normalized

    # ── Build Progress Helpers ────────────────────────────────────────────

    def recalculate_progress(self, workspace_id: str) -> Workspace:
        """Recompute progress % and ETA from task completion data."""
        from app.services.task_service import task_service

        total = task_service.count_total(workspace_id)
        completed = task_service.count_completed(workspace_id)
        progress = int((completed / total) * 100) if total > 0 else 0

        avg_duration = task_service.average_task_duration(workspace_id)
        remaining_tasks = total - completed
        eta_minutes = None
        if avg_duration is not None and remaining_tasks > 0:
            eta_minutes = round((avg_duration * remaining_tasks) / 60, 1)

        build_status = "Building"
        if progress >= 100:
            build_status = "Completed"

        return self.update(
            workspace_id,
            progress=progress,
            estimated_completion_minutes=eta_minutes,
            task_count=total,
            build_status=build_status,
        )

    def update_build_status(
        self,
        workspace_id: str,
        build_status: str,
        current_agent: str | None = None,
        current_task_title: str | None = None,
    ) -> Workspace:
        return self.update(
            workspace_id,
            build_status=build_status,
            current_agent=current_agent,
            current_task_title=current_task_title,
        )


workspace_service = WorkspaceService()
