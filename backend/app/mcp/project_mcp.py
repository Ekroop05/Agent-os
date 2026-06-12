import os
from typing import Dict, Any, List

from app.mcp.registry import register_tool
from app.services.workspace_service import workspace_service
from app.schemas import WorkspaceCreate

@register_tool("project", "create_project")
def create_project(name: str) -> Dict[str, Any]:
    # Create the workspace in the service
    payload = WorkspaceCreate(
        name=name,
        description=f"Generated Project for {name}",
        active_agents=0,
    )
    workspace = workspace_service.create(payload)
    
    path = workspace.path
    
    # Create scaffolding folders
    folders = ["frontend", "backend", "docs", ".agentos"]
    for folder in folders:
        os.makedirs(os.path.join(path, folder), exist_ok=True)
        
    return {
        "workspace_id": workspace.id,
        "path": workspace.path
    }

@register_tool("project", "delete_project")
def delete_project(workspace_id: str) -> Dict[str, Any]:
    workspace_service.delete(workspace_id)
    return {"status": "deleted", "workspace_id": workspace_id}

@register_tool("project", "list_projects")
def list_projects() -> List[Dict[str, Any]]:
    workspaces = workspace_service.list()
    return [w.model_dump() for w in workspaces]

@register_tool("project", "get_project")
def get_project(workspace_id: str) -> Dict[str, Any]:
    workspace = workspace_service.get(workspace_id)
    return workspace.model_dump()

@register_tool("project", "set_project_root")
def set_project_root(path: str) -> Dict[str, Any]:
    new_root = workspace_service.set_project_root(path)
    return {"project_root": new_root}

@register_tool("project", "get_project_path")
def get_project_path(project_name: str) -> Dict[str, Any]:
    path = workspace_service.path_for_project(project_name)
    return {"project_name": project_name, "path": path}
