"""
Path Security — filesystem isolation for generated projects.

All file operations by Builder/MCP must pass through this module.
Ensures generated projects can ONLY write inside the configured project root
(default: D:/Projects) and never touch Agent OS files, system files, or user
profile directories.
"""

from __future__ import annotations

import os
import logging

from app.core.config import settings

logger = logging.getLogger("path_security")


class SecurityViolationError(Exception):
    """Raised when a filesystem operation violates security policy."""

    def __init__(self, message: str, path: str = "", reason: str = ""):
        self.path = path
        self.reason = reason
        super().__init__(message)


# ── Forbidden Path Prefixes (normalised, lowercase) ──────────────────────

def _build_forbidden_set() -> set[str]:
    """Build the set of forbidden path prefixes from config + dynamic entries."""
    forbidden = set()

    # From config
    for p in settings.forbidden_paths:
        forbidden.add(p.replace("\\", "/").rstrip("/").lower())

    # Agent OS source directory — always forbidden
    source = settings.agent_os_source_dir.replace("\\", "/").rstrip("/").lower()
    forbidden.add(source)

    # Common user-profile sensitive dirs
    home = os.path.expanduser("~").replace("\\", "/").rstrip("/").lower()
    for sub in ("Desktop", "Documents", "Downloads", "AppData"):
        forbidden.add(f"{home}/{sub}".lower())

    return forbidden


FORBIDDEN_PREFIXES: set[str] = _build_forbidden_set()


# ── Public API ────────────────────────────────────────────────────────────

def validate_path(target_path: str, workspace_path: str | None = None) -> str:
    """Validate that *target_path* is safe to read.

    Returns the normalised absolute path on success.
    Raises SecurityViolationError on violation.
    """
    normalised = _normalise(target_path, workspace_path)
    _check_forbidden(normalised, target_path)
    _check_inside_root(normalised, target_path)
    return normalised


def validate_write_path(target_path: str, workspace_path: str | None = None) -> str:
    """Validate that *target_path* is safe to write to.

    Applies all read-path checks PLUS:
    - Rejects absolute paths outside the project root
    - Rejects path traversal (../)
    - Resolves and rejects symlink escapes
    """
    # Reject obvious traversal in the raw input
    raw = target_path.replace("\\", "/")
    if "/../" in raw or raw.startswith("../") or raw.endswith("/.."):
        raise SecurityViolationError(
            f"Path traversal detected: {target_path}",
            path=target_path,
            reason="path_traversal",
        )

    normalised = _normalise(target_path, workspace_path)

    # Resolve symlinks and re-check
    try:
        resolved = os.path.realpath(normalised.replace("/", os.sep)).replace("\\", "/")
    except OSError:
        # Path doesn't exist yet — that's fine, check the parent
        parent = os.path.dirname(normalised.replace("/", os.sep))
        resolved = os.path.realpath(parent).replace("\\", "/") + "/" + os.path.basename(normalised)

    _check_forbidden(resolved, target_path)
    _check_inside_root(resolved, target_path)

    return normalised


def is_safe_path(target_path: str, workspace_path: str | None = None) -> bool:
    """Non-throwing version: returns True if the path is safe."""
    try:
        validate_write_path(target_path, workspace_path)
        return True
    except SecurityViolationError:
        return False


# ── Internal Helpers ──────────────────────────────────────────────────────

def _normalise(target_path: str, workspace_path: str | None) -> str:
    """Normalise a path to an absolute forward-slash path."""
    cleaned = target_path.replace("\\", "/")

    if not os.path.isabs(cleaned):
        if workspace_path:
            base = workspace_path.replace("\\", "/").rstrip("/")
            cleaned = f"{base}/{cleaned}"
        else:
            root = settings.project_root.replace("\\", "/").rstrip("/")
            cleaned = f"{root}/{cleaned}"

    # os.path.abspath handles . and ..
    return os.path.abspath(cleaned.replace("/", os.sep)).replace("\\", "/")


def _check_forbidden(normalised: str, original: str) -> None:
    """Raise if the normalised path starts with any forbidden prefix."""
    lower = normalised.lower()
    for prefix in FORBIDDEN_PREFIXES:
        if lower == prefix or lower.startswith(prefix + "/"):
            logger.warning("Path security violation: %s → forbidden prefix %s", original, prefix)
            raise SecurityViolationError(
                f"Access denied: {original} intersects forbidden path {prefix}",
                path=original,
                reason="forbidden_path",
            )


def _check_inside_root(normalised: str, original: str) -> None:
    """Raise if the normalised path is not inside the project root."""
    root = settings.project_root.replace("\\", "/").rstrip("/").lower()
    lower = normalised.lower()
    if not (lower == root or lower.startswith(root + "/")):
        logger.warning("Path security violation: %s → outside project root %s", original, root)
        raise SecurityViolationError(
            f"Access denied: {original} is outside project root {settings.project_root}",
            path=original,
            reason="outside_root",
        )
