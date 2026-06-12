import os
import subprocess
import uuid
import shlex
from typing import Dict, Any, List

from app.mcp.registry import register_tool
from app.mcp.file_mcp import _validate_path
from app.core.event_bus import event_bus
from app.schemas import Event

ALLOWED_COMMANDS = ["npm", "npx", "node", "python", "pip", "git", "uvicorn"]
BLOCKED_SUBSTRINGS = ["format", "del /s", "rd /s", "shutdown", "diskpart", "|", ">", "<", "&&", "||", ";", "rm -rf"]

active_commands: Dict[str, subprocess.Popen] = {}
command_outputs: Dict[str, str] = {}

def _validate_command(command: str) -> None:
    lower_cmd = command.lower()
    
    # Check blocked substrings
    for blocked in BLOCKED_SUBSTRINGS:
        if blocked in lower_cmd:
            raise ValueError(f"Command blocked due to security rules (contains '{blocked}')")
            
    # Check allowed base command
    parts = shlex.split(command, posix=False)
    if not parts:
        raise ValueError("Empty command")
        
    base_cmd = parts[0].lower()
    
    # Simple check for the base executable name. 
    # E.g. 'npm', 'npm.cmd', 'python.exe' -> strip extensions for check.
    base_name = os.path.splitext(base_cmd)[0]
    
    if base_name not in ALLOWED_COMMANDS:
        raise ValueError(f"Command '{base_name}' is not in the allowed list: {ALLOWED_COMMANDS}")

@register_tool("terminal", "run_command")
async def run_command(command: str, cwd: str) -> Dict[str, Any]:
    safe_cwd = _validate_path(cwd)
    _validate_command(command)
    
    cmd_id = str(uuid.uuid4())
    
    # Note: For windows, shell=True might be needed for commands like npm if they are .cmd, 
    # but we must be careful. We block chaining operators above to mitigate risks.
    process = subprocess.Popen(
        command,
        cwd=safe_cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    active_commands[cmd_id] = process
    command_outputs[cmd_id] = ""
    
    await event_bus.publish(Event(
        type="COMMAND_STARTED", 
        source="Terminal MCP", 
        message=f"Command started: {command}", 
        payload={"cmd_id": cmd_id, "command": command, "cwd": safe_cwd}
    ))
    
    return {"status": "success", "cmd_id": cmd_id, "message": "Command started"}

@register_tool("terminal", "get_command_status")
def get_command_status(cmd_id: str) -> Dict[str, Any]:
    if cmd_id not in active_commands:
        return {"status": "error", "message": "Command ID not found"}
        
    process = active_commands[cmd_id]
    retcode = process.poll()
    
    state = "running" if retcode is None else "completed"
    
    return {"status": "success", "cmd_id": cmd_id, "state": state, "exit_code": retcode}

@register_tool("terminal", "get_command_output")
async def get_command_output(cmd_id: str) -> Dict[str, Any]:
    if cmd_id not in active_commands:
        return {"status": "error", "message": "Command ID not found"}
        
    process = active_commands[cmd_id]
    
    # Non-blocking read of whatever is available
    import fcntl
    import sys
    
    # Windows doesn't have fcntl. So we will do a simple read if process is done,
    # or just read blockingly if wait is fine for small commands. 
    # To do real async streaming on Windows is complex, 
    # so we'll just wait for it to finish or communicate.
    # Since we don't want to block, we can check poll().
    retcode = process.poll()
    if retcode is not None:
        # Process finished, we can read the rest safely
        out, _ = process.communicate()
        command_outputs[cmd_id] += out
        
        await event_bus.publish(Event(
            type="COMMAND_COMPLETED", 
            source="Terminal MCP", 
            message=f"Command completed", 
            payload={"cmd_id": cmd_id, "exit_code": retcode}
        ))
    else:
        # It's still running, we might not be able to read stdout safely without blocking on Windows.
        pass
        
    return {"status": "success", "cmd_id": cmd_id, "output": command_outputs[cmd_id]}

@register_tool("terminal", "kill_command")
def kill_command(cmd_id: str) -> Dict[str, Any]:
    if cmd_id not in active_commands:
        return {"status": "error", "message": "Command ID not found"}
        
    process = active_commands[cmd_id]
    if process.poll() is None:
        process.kill()
        return {"status": "success", "message": "Command killed"}
    
    return {"status": "success", "message": "Command was already finished"}
