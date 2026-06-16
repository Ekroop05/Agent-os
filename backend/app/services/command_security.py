"""
Command Security — restricts commands that generated projects may execute.

Builder and MCP terminal tools must validate commands through this module
before execution. Blocks dangerous system-level operations while allowing
standard development commands.
"""

from __future__ import annotations

import logging
import re
import shlex

logger = logging.getLogger("command_security")


class CommandBlockedError(Exception):
    """Raised when a command violates the security policy."""

    def __init__(self, message: str, command: str = "", reason: str = ""):
        self.command = command
        self.reason = reason
        super().__init__(message)


# ── Allowlist ─────────────────────────────────────────────────────────────
# Commands that are explicitly permitted. Each entry is a prefix that the
# tokenised command must start with.

COMMAND_ALLOWLIST: list[str] = [
    "npm install",
    "npm run",
    "npm start",
    "npm test",
    "npm init",
    "npm ci",
    "npx",
    "node",
    "pip install",
    "pip list",
    "pip freeze",
    "python -m",
    "python -c",
    "uvicorn",
    "vite",
    "git init",
    "git add",
    "git commit",
    "git status",
    "git log",
    "git diff",
    "git clone",
    "git checkout",
    "git branch",
    "git pull",
    "git push",
    "mkdir",
    "cd",
    "dir",
    "ls",
    "cat",
    "type",
    "echo",
    "copy",
    "move",
    "ren",
]

# ── Blocklist ─────────────────────────────────────────────────────────────
# Patterns that are ALWAYS blocked, even if they match an allowlist prefix.
# These are checked as case-insensitive regex patterns.

COMMAND_BLOCKLIST_PATTERNS: list[tuple[str, str]] = [
    (r"\bformat\s+[a-zA-Z]:", "Format drive command"),
    (r"\breg\s+(add|delete|query)", "Registry modification"),
    (r"\bshutdown\b", "System shutdown"),
    (r"\brestart-computer\b", "System restart"),
    (r"\bstop-computer\b", "System stop"),
    (r"\bnet\s+user\b", "User account modification"),
    (r"\bnet\s+localgroup\b", "Local group modification"),
    (r"\bnetsh\b", "Network configuration"),
    (r"\bnmap\b", "Network scanning"),
    (r"\btaskkill\b", "Process termination"),
    (r"\bkill\s+-9\b", "Force kill process"),
    (r"\bdel\s+/s\b", "Recursive delete"),
    (r"\brmdir\s+/s\b", "Recursive directory delete"),
    (r"\brm\s+-rf\s+/", "Recursive root delete"),
    (r"\bSet-ExecutionPolicy\b", "Execution policy change"),
    (r"\bNew-LocalUser\b", "User creation"),
    (r"\bNew-LocalGroup\b", "Group creation"),
    (r"\bpowershell\s+.*-[Ee]nc", "Encoded PowerShell"),
    (r"\bcmd\s+/c\s+.*&&\s*del\b", "Chained delete"),
    (r"\bchmod\s+777\b", "Dangerous permission change"),
    (r"\bchown\s+root\b", "Root ownership change"),
    (r"\bcurl\s+.*\|\s*(bash|sh)\b", "Pipe to shell"),
    (r"\bwget\s+.*\|\s*(bash|sh)\b", "Pipe to shell"),
    (r"\b__import__\b", "Python dynamic import"),
    (r"\bexec\s*\(", "Dynamic execution"),
    (r"\beval\s*\(", "Dynamic evaluation"),
    (r"\bos\.system\b", "OS system call"),
    (r"\bsubprocess\..*shell\s*=\s*True", "Subprocess with shell"),
    (r"\bschtasks\b", "Scheduled task manipulation"),
    (r"\bsc\s+(create|delete|start|stop)\b", "Service manipulation"),
    (r"\bwmic\b", "WMI command"),
    (r"\bcertutil\b", "Certificate utility abuse"),
    (r"\bbitsadmin\b", "Background transfer abuse"),
]


# ── Public API ────────────────────────────────────────────────────────────

def validate_command(command: str) -> str:
    """Validate a command against the allowlist and blocklist.

    Returns the sanitised command string on success.
    Raises CommandBlockedError if the command is blocked.
    """
    stripped = command.strip()
    if not stripped:
        raise CommandBlockedError("Empty command", command=command, reason="empty")

    # 1. Check blocklist first (always wins)
    _check_blocklist(stripped)

    # 2. Check allowlist
    _check_allowlist(stripped)

    return stripped


def is_safe_command(command: str) -> bool:
    """Non-throwing version: returns True if the command is safe."""
    try:
        validate_command(command)
        return True
    except CommandBlockedError:
        return False


def sanitize_command(command: str) -> str:
    """Strip known dangerous flags from a command.

    This is a best-effort sanitiser — validate_command() should still be
    called after sanitisation.
    """
    sanitised = command.strip()

    # Remove shell operator chains that could be used for injection
    # But keep simple && for chaining safe commands
    sanitised = re.sub(r"\|\s*(bash|sh|cmd|powershell)\b", "", sanitised)

    # Remove encoded execution flags
    sanitised = re.sub(r"-[Ee]nc(?:oded)?[Cc]ommand\s+\S+", "", sanitised)

    return sanitised.strip()


# ── Internal Helpers ──────────────────────────────────────────────────────

def _check_blocklist(command: str) -> None:
    """Raise if command matches any blocklist pattern."""
    for pattern, description in COMMAND_BLOCKLIST_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning("Command blocked: %s — %s", command[:80], description)
            raise CommandBlockedError(
                f"Command blocked: {description}",
                command=command,
                reason=description,
            )


def _check_allowlist(command: str) -> None:
    """Raise if command does not match any allowlist prefix."""
    lower = command.lower().strip()

    for allowed in COMMAND_ALLOWLIST:
        if lower.startswith(allowed.lower()):
            return  # Match found

    logger.warning("Command not in allowlist: %s", command[:80])
    raise CommandBlockedError(
        f"Command not in allowlist: {command[:60]}",
        command=command,
        reason="not_in_allowlist",
    )
