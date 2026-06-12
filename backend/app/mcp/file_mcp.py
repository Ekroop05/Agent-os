import os
import glob
from typing import Dict, Any, List

from app.mcp.registry import register_tool
from app.services.workspace_service import workspace_service
from app.core.event_bus import event_bus
from app.schemas import Event

ALLOWED_ROOT = workspace_service.project_root

BLOCKED_PATHS = [
    "c:/windows",
    "c:/program files",
    "c:/program files (x86)",
    "c:/users",
    # Block agent os source code - assuming it's running from somewhere not D:/Projects,
    # but the simplest block is ensuring path.startswith(ALLOWED_ROOT) and not going up.
]

def _validate_path(file_path: str) -> str:
    # Resolve absolute path
    if not os.path.isabs(file_path):
        file_path = os.path.join(ALLOWED_ROOT, file_path)
    
    normalized = os.path.abspath(file_path).replace("\\", "/")
    
    if not normalized.lower().startswith(ALLOWED_ROOT.lower()):
        raise ValueError(f"Access denied: {file_path} is outside allowed root {ALLOWED_ROOT}")
    
    for blocked in BLOCKED_PATHS:
        if normalized.lower().startswith(blocked.lower()):
            raise ValueError(f"Access denied: Path intersects with blocked path {blocked}")
            
    return normalized

@register_tool("file", "create_file")
async def create_file(file_path: str, content: str) -> Dict[str, Any]:
    safe_path = _validate_path(file_path)
    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    await event_bus.publish(Event(type="FILE_CREATED", source="File MCP", message=f"File created: {safe_path}", payload={"path": safe_path}))
    return {"status": "success", "path": safe_path}

@register_tool("file", "read_file")
def read_file(file_path: str) -> Dict[str, Any]:
    safe_path = _validate_path(file_path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"File not found: {safe_path}")
    
    if os.path.getsize(safe_path) > 5 * 1024 * 1024: # 5MB limit
        raise ValueError(f"File too large to read: {safe_path}")
        
    with open(safe_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {"status": "success", "path": safe_path, "content": content}

@register_tool("file", "update_file")
async def update_file(file_path: str, content: str) -> Dict[str, Any]:
    safe_path = _validate_path(file_path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"File not found: {safe_path}")
        
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    await event_bus.publish(Event(type="FILE_UPDATED", source="File MCP", message=f"File updated: {safe_path}", payload={"path": safe_path}))
    return {"status": "success", "path": safe_path}

@register_tool("file", "delete_file")
async def delete_file(file_path: str) -> Dict[str, Any]:
    safe_path = _validate_path(file_path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"File not found: {safe_path}")
        
    os.remove(safe_path)
    await event_bus.publish(Event(type="FILE_DELETED", source="File MCP", message=f"File deleted: {safe_path}", payload={"path": safe_path}))
    return {"status": "success", "path": safe_path}

@register_tool("file", "create_directory")
async def create_directory(dir_path: str) -> Dict[str, Any]:
    safe_path = _validate_path(dir_path)
    os.makedirs(safe_path, exist_ok=True)
    return {"status": "success", "path": safe_path}

@register_tool("file", "list_directory")
def list_directory(dir_path: str, recursive: bool = False) -> Dict[str, Any]:
    safe_path = _validate_path(dir_path)
    if not os.path.exists(safe_path):
        raise FileNotFoundError(f"Directory not found: {safe_path}")
        
    items = []
    if recursive:
        for root, dirs, files in os.walk(safe_path):
            for d in dirs:
                items.append(os.path.join(root, d).replace("\\", "/"))
            for f in files:
                items.append(os.path.join(root, f).replace("\\", "/"))
    else:
        for item in os.listdir(safe_path):
            items.append(os.path.join(safe_path, item).replace("\\", "/"))
            
    return {"status": "success", "path": safe_path, "items": items}

@register_tool("file", "search_files")
def search_files(dir_path: str, pattern: str) -> Dict[str, Any]:
    safe_path = _validate_path(dir_path)
    search_pattern = os.path.join(safe_path, "**", pattern)
    matches = glob.glob(search_pattern, recursive=True)
    return {"status": "success", "path": safe_path, "pattern": pattern, "matches": [m.replace("\\", "/") for m in matches]}
