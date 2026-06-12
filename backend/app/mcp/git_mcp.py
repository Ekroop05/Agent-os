import subprocess
import shlex
from typing import Dict, Any

from app.mcp.registry import register_tool
from app.mcp.file_mcp import _validate_path
from app.core.event_bus import event_bus
from app.schemas import Event

def _run_git(args: list[str], cwd: str) -> Dict[str, Any]:
    safe_cwd = _validate_path(cwd)
    cmd = ["git"] + args
    
    try:
        result = subprocess.run(cmd, cwd=safe_cwd, capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@register_tool("git", "git_init")
def git_init(cwd: str) -> Dict[str, Any]:
    return _run_git(["init"], cwd)

@register_tool("git", "git_status")
def git_status(cwd: str) -> Dict[str, Any]:
    return _run_git(["status"], cwd)

@register_tool("git", "git_add")
def git_add(cwd: str, files: str = ".") -> Dict[str, Any]:
    # Need to be careful with arbitrary arguments here. We will just use the exact list.
    return _run_git(["add", files], cwd)

@register_tool("git", "git_commit")
async def git_commit(cwd: str, message: str) -> Dict[str, Any]:
    res = _run_git(["commit", "-m", message], cwd)
    if res["status"] == "success":
        await event_bus.publish(Event(
            type="GIT_COMMIT_CREATED",
            source="Git MCP",
            message=f"Git commit created: {message}",
            payload={"cwd": cwd, "message": message}
        ))
    return res

@register_tool("git", "git_branch")
def git_branch(cwd: str) -> Dict[str, Any]:
    return _run_git(["branch"], cwd)

@register_tool("git", "git_checkout")
def git_checkout(cwd: str, branch_name: str, create: bool = False) -> Dict[str, Any]:
    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch_name)
    return _run_git(args, cwd)

@register_tool("git", "git_log")
def git_log(cwd: str, max_count: int = 10) -> Dict[str, Any]:
    return _run_git(["log", f"-n {max_count}", "--oneline"], cwd)
