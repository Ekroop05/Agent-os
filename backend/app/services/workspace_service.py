from __future__ import annotations

import logging
import os
import re
import shutil
import time

from fastapi import HTTPException

from app.schemas import Workspace, WorkspaceArchiveEntry, WorkspaceCreate
from app.services.time_service import now_label

logger = logging.getLogger("workspace_service")

DEFAULT_PROJECT_ROOT = "D:/Projects"


def slugify(value: str) -> str:
    """Convert a project name to a URL/folder-safe slug.

    Examples:
        'Superhero Website'   -> 'superhero-website'
        'AI Resume Analyzer'  -> 'ai-resume-analyzer'
        'Netflix Clone'       -> 'netflix-clone'
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip())
    slug = slug.strip("-").lower()
    return slug or "generated-project"


def title_case_slug(slug: str) -> str:
    """Convert a slug to Title-Case for folder names.

    Examples:
        'superhero-website'   -> 'Superhero-Website'
        'ai-resume-analyzer'  -> 'AI-Resume-Analyzer'
    """
    return "-".join(part.capitalize() for part in slug.split("-"))


class WorkspaceService:
    def __init__(self):
        self.workspaces: dict[str, Workspace] = {}
        self.project_root = DEFAULT_PROJECT_ROOT
        self.archive: list[WorkspaceArchiveEntry] = []
        self.build_reports: dict[str, dict] = {}  # workspace_id -> report dict

    def list(self) -> list[Workspace]:
        return list(self.workspaces.values())

    def get(self, workspace_id: str) -> Workspace:
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    def create(self, payload: WorkspaceCreate) -> Workspace:
        """Create a workspace with proper naming, slug, and path.

        The project name is derived from payload.name.
        The slug is derived from the project name.
        The path is derived from the slug with duplicate protection.
        """
        # Derive project name — never accept generic/empty names silently
        name = payload.name.strip()
        if not name or name.lower() in ("generated project", "untitled project", "project", ""):
            name = "Generated Project"

        slug = slugify(name)
        workspace_id = f"workspace-{slug}"

        # Handle duplicate workspace IDs in memory
        if workspace_id in self.workspaces:
            version = 2
            while f"{workspace_id}-v{version}" in self.workspaces:
                version += 1
            workspace_id = f"{workspace_id}-v{version}"
            slug = f"{slug}-v{version}"

        # Build path with duplicate protection
        path = payload.path or self._unique_path_for_slug(slug)

        workspace = Workspace(
            id=workspace_id,
            project_name=name,
            name=name,
            slug=slug,
            description=payload.description,
            status="Planning",
            active_agents=payload.active_agents,
            task_count=0,
            created_at=now_label(),
            path=self.normalize_project_path(path),
            progress=0,
            estimated_completion_minutes=None,
            current_agent=None,
            current_task_title=None,
        )
        self.workspaces[workspace_id] = workspace
        return workspace

    def update(self, workspace_id: str, **changes) -> Workspace:
        workspace = self.get(workspace_id)
        updated = workspace.model_copy(update={key: value for key, value in changes.items() if value is not None})
        self.workspaces[workspace_id] = updated
        return updated

    def delete(self, workspace_id: str) -> None:
        """Safe workspace deletion.

        Sprint 4.5 flow:
        1. Stop frontend process
        2. Stop backend process
        3. Release ports
        4. Kill runtime
        5. Verify process exited
        6. Delete workspace files
        7. Remove registry entries
        8. Archive metadata
        9. Complete deletion
        """
        workspace = self.get(workspace_id)

        # Archive before deleting
        self.archive_workspace(workspace)

        # Sprint 4.5: Stop any running processes first
        try:
            from app.services.runtime_manager import runtime_manager
            runtime_manager.stop_runtime(workspace_id)
            runtime_manager.remove_runtime(workspace_id)
            logger.info("Runtime stopped for workspace %s", workspace_id)
        except Exception as e:
            logger.warning("Failed to stop runtime for %s: %s", workspace_id, e)

        # Sprint 4.5: Delete files from disk with retry for locked files
        workspace_path = workspace.path.replace("/", os.sep)
        if os.path.exists(workspace_path):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    shutil.rmtree(
                        workspace_path,
                        onerror=self._on_delete_error,
                    )
                    logger.info("Deleted workspace files: %s", workspace_path)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Retry %d/%d deleting %s: %s",
                            attempt + 1, max_retries, workspace_path, e,
                        )
                        time.sleep(1)  # Wait for file locks to release
                    else:
                        logger.error("Failed to delete workspace files: %s", e)

        del self.workspaces[workspace_id]

    @staticmethod
    def _on_delete_error(func, path, exc_info):
        """Error handler for shutil.rmtree — handle read-only/locked files."""
        import stat
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            logger.warning("Could not delete: %s", path)

    def set_project_root(self, project_root: str) -> str:
        cleaned = project_root.strip().replace("\\", "/").rstrip("/")
        if not cleaned:
            raise HTTPException(status_code=400, detail="Project root is required")
        self.project_root = cleaned
        return self.project_root

    def path_for_project(self, project_name: str) -> str:
        """Generate a unique path for a project name."""
        slug = slugify(project_name)
        return self._unique_path_for_slug(slug)

    def _unique_path_for_slug(self, slug: str) -> str:
        """Generate a unique filesystem path, appending -v2, -v3 etc. if needed."""
        folder_name = title_case_slug(slug)
        base_path = f"{self.project_root}/{folder_name}"

        # Check if the path is already used by an existing workspace in memory
        existing_paths = {ws.path for ws in self.workspaces.values()}

        candidate = base_path
        # Check both in-memory workspaces AND on-disk folders
        version = 2
        while candidate in existing_paths or self._path_exists_on_disk(candidate):
            candidate = f"{base_path}-v{version}"
            version += 1

        return candidate

    def _path_exists_on_disk(self, path: str) -> bool:
        """Check if a project path already exists on disk."""
        native_path = path.replace("/", os.sep)
        return os.path.exists(native_path)

    def normalize_project_path(self, path: str) -> str:
        normalized = path.replace("\\", "/").rstrip("/")
        root = self.project_root.rstrip("/")
        if normalized != root and not normalized.startswith(f"{root}/"):
            raise HTTPException(status_code=400, detail="Workspace path must be inside configured project root")
        return normalized

    # ── Build Progress Helpers ────────────────────────────────────────────

    def recalculate_progress(self, workspace_id: str) -> Workspace:
        """Recompute progress % and ETA from task completion data.

        Progress formula: completed / total * 100
        Failed tasks do NOT count toward progress.
        """
        from app.services.task_service import task_service

        total = task_service.count_total(workspace_id)
        completed = task_service.count_completed(workspace_id)
        failed = task_service.count_failed(workspace_id)

        # Progress is only completed tasks (not failed)
        progress = int((completed / total) * 100) if total > 0 else 0

        avg_duration = task_service.average_task_duration(workspace_id)
        remaining_tasks = total - completed - failed
        eta_minutes = None
        if avg_duration is not None and remaining_tasks > 0:
            eta_minutes = round((avg_duration * remaining_tasks) / 60, 1)

        # Determine workspace status based on task states
        workspace = self.get(workspace_id)
        current_status = workspace.status

        # Don't override terminal states from here — let the orchestrator handle that
        if current_status not in ("Completed", "Failed"):
            if total > 0 and remaining_tasks == 0 and failed == 0:
                current_status = "Completed"
            elif total > 0 and remaining_tasks == 0 and failed > 0:
                # All tasks processed but some failed
                current_status = "Completed"

        return self.update(
            workspace_id,
            progress=progress,
            estimated_completion_minutes=eta_minutes,
            task_count=total,
            status=current_status,
        )

    def update_build_status(
        self,
        workspace_id: str,
        status: str,
        current_agent: str | None = None,
        current_task_title: str | None = None,
    ) -> Workspace:
        """Update the workspace status and optionally the current agent/task."""
        return self.update(
            workspace_id,
            status=status,
            current_agent=current_agent,
            current_task_title=current_task_title,
        )

    # ── Archive Helpers ──────────────────────────────────────────────────

    def archive_workspace(self, workspace: Workspace) -> WorkspaceArchiveEntry:
        """Create an archive entry from a workspace."""
        from app.services.task_service import task_service

        completed = task_service.count_completed(workspace.id)
        failed = task_service.count_failed(workspace.id)
        total = task_service.count_total(workspace.id)

        entry = WorkspaceArchiveEntry(
            id=workspace.id,
            project_name=workspace.project_name,
            slug=workspace.slug,
            path=workspace.path,
            status=workspace.status,
            created_at=workspace.created_at,
            completed_at=workspace.completed_at or now_label(),
            task_count=total,
            tasks_completed=completed,
            tasks_failed=failed,
            progress=workspace.progress,
        )

        # Avoid duplicate archive entries
        if not any(a.id == entry.id for a in self.archive):
            self.archive.append(entry)

        return entry

    def list_archive(self) -> list[WorkspaceArchiveEntry]:
        """Return all archived workspaces."""
        return list(self.archive)

    def store_build_report(self, workspace_id: str, report: dict) -> None:
        """Store a build report for a workspace."""
        self.build_reports[workspace_id] = report

    def get_build_report(self, workspace_id: str) -> dict | None:
        """Retrieve a build report for a workspace."""
        return self.build_reports.get(workspace_id)


workspace_service = WorkspaceService()
