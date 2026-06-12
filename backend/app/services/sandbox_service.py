from pathlib import Path

from app.schemas import SandboxState
from app.services.workspace_service import workspace_service


class SandboxService:
    def get_state(self) -> SandboxState:
        root = workspace_service.project_root
        projects = self._projects(root)
        mappings = [
            {"workspace_id": workspace.id, "name": workspace.name, "path": workspace.path}
            for workspace in workspace_service.list()
        ]
        return SandboxState(project_root=root, projects=projects, workspace_mappings=mappings)

    def update_root(self, project_root: str) -> SandboxState:
        workspace_service.set_project_root(project_root)
        return self.get_state()

    def _projects(self, root: str) -> list[dict]:
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            return []
        return [
            {"name": item.name, "path": item.as_posix()}
            for item in root_path.iterdir()
            if item.is_dir()
        ]


sandbox_service = SandboxService()
