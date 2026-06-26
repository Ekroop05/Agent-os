"""Sprint 5: Workspace Snapshot Service (Feature 6)

Safe Edit Mode — creates filesystem snapshots of workspace files
before modifications, enabling rollback and before/after comparison.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("workspace_snapshot")


class WorkspaceSnapshotService:
    """Creates and manages workspace file snapshots for safe editing."""

    def __init__(self):
        self._snapshots: dict[str, list[dict]] = {}  # workspace_id -> list of snapshot metadata

    def create_snapshot(self, workspace_id: str, workspace_path: str, label: str = "") -> dict:
        """Create a snapshot of the current workspace files."""
        src = Path(workspace_path)
        if not src.exists() or not src.is_dir():
            return {"error": f"Workspace path does not exist: {workspace_path}"}

        snapshot_id = f"snap-{uuid.uuid4().hex[:8]}"
        snap_dir = src / ".snapshots" / snapshot_id

        try:
            # Copy all workspace files (excluding .snapshots, node_modules, .git, etc.)
            self._copy_tree(src, snap_dir)

            # Build file manifest
            file_count = sum(1 for _ in snap_dir.rglob("*") if _.is_file())

            metadata = {
                "snapshot_id": snapshot_id,
                "workspace_id": workspace_id,
                "label": label or f"Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "created_at": datetime.now().isoformat(),
                "file_count": file_count,
                "path": str(snap_dir).replace("\\", "/"),
            }

            # Store metadata
            if workspace_id not in self._snapshots:
                self._snapshots[workspace_id] = []
            self._snapshots[workspace_id].append(metadata)

            # Also write metadata to disk for persistence
            meta_path = snap_dir / "_snapshot_meta.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            logger.info("Snapshot created: %s (%d files)", snapshot_id, file_count)
            return metadata

        except Exception as e:
            logger.error("Failed to create snapshot: %s", e)
            return {"error": str(e)}

    def list_snapshots(self, workspace_id: str, workspace_path: str = "") -> list[dict]:
        """List all snapshots for a workspace."""
        # Try in-memory first
        snapshots = self._snapshots.get(workspace_id, [])

        # Also scan disk if workspace_path is provided and no in-memory data
        if not snapshots and workspace_path:
            snap_root = Path(workspace_path) / ".snapshots"
            if snap_root.exists():
                for snap_dir in sorted(snap_root.iterdir()):
                    meta_path = snap_dir / "_snapshot_meta.json"
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text(encoding="utf-8"))
                            snapshots.append(meta)
                        except (json.JSONDecodeError, OSError):
                            pass
                self._snapshots[workspace_id] = snapshots

        return snapshots

    def restore_snapshot(self, workspace_id: str, workspace_path: str, snapshot_id: str) -> dict:
        """Restore workspace files from a snapshot."""
        src = Path(workspace_path)
        snap_dir = src / ".snapshots" / snapshot_id

        if not snap_dir.exists():
            return {"error": f"Snapshot not found: {snapshot_id}"}

        try:
            # Create a backup of current state first (auto-snapshot before restore)
            self.create_snapshot(workspace_id, workspace_path, label=f"Pre-restore backup")

            # Restore files from snapshot
            restored = 0
            for snap_file in snap_dir.rglob("*"):
                if snap_file.is_file() and snap_file.name != "_snapshot_meta.json":
                    rel = snap_file.relative_to(snap_dir)
                    target = src / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snap_file, target)
                    restored += 1

            logger.info("Restored snapshot %s: %d files", snapshot_id, restored)
            return {"restored": True, "snapshot_id": snapshot_id, "files_restored": restored}

        except Exception as e:
            logger.error("Failed to restore snapshot: %s", e)
            return {"error": str(e)}

    def compare_snapshot(self, workspace_path: str, snapshot_id: str) -> dict:
        """Compare current workspace state with a snapshot."""
        src = Path(workspace_path)
        snap_dir = src / ".snapshots" / snapshot_id

        if not snap_dir.exists():
            return {"error": f"Snapshot not found: {snapshot_id}"}

        skip = {".snapshots", "node_modules", ".git", "__pycache__", "dist", "build", ".venv"}

        # Build file sets
        current_files = self._list_files(src, skip)
        snapshot_files = self._list_snapshot_files(snap_dir)

        added = sorted(current_files - snapshot_files)
        removed = sorted(snapshot_files - current_files)
        common = current_files & snapshot_files

        # Check for modifications (compare file sizes as a fast heuristic)
        modified = []
        for rel in sorted(common):
            curr_path = src / rel
            snap_path = snap_dir / rel
            if curr_path.exists() and snap_path.exists():
                if curr_path.stat().st_size != snap_path.stat().st_size:
                    modified.append(rel)

        return {
            "snapshot_id": snapshot_id,
            "files_added": added,
            "files_modified": modified,
            "files_removed": removed,
            "added_count": len(added),
            "modified_count": len(modified),
            "removed_count": len(removed),
            "total_changes": len(added) + len(modified) + len(removed),
        }

    def _copy_tree(self, src: Path, dst: Path):
        """Copy a directory tree, skipping node_modules, .git, .snapshots, etc."""
        skip = {"node_modules", ".git", "__pycache__", ".snapshots", "dist", "build", ".venv", "venv"}
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name in skip:
                continue
            target = dst / item.name
            if item.is_dir():
                self._copy_tree(item, target)
            elif item.is_file():
                shutil.copy2(item, target)

    def _list_files(self, root: Path, skip: set) -> set[str]:
        """List all relative file paths in a directory."""
        files = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for f in filenames:
                rel = str(Path(dirpath, f).relative_to(root)).replace("\\", "/")
                files.add(rel)
        return files

    def _list_snapshot_files(self, snap_dir: Path) -> set[str]:
        """List all relative file paths in a snapshot directory."""
        files = set()
        for dirpath, dirnames, filenames in os.walk(snap_dir):
            for f in filenames:
                if f == "_snapshot_meta.json":
                    continue
                rel = str(Path(dirpath, f).relative_to(snap_dir)).replace("\\", "/")
                files.add(rel)
        return files


workspace_snapshot = WorkspaceSnapshotService()
