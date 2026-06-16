"""
Runtime Manager — process tracking, port allocation, and zombie prevention.

Manages the lifecycle of generated project processes:
- Allocates unique ports that never collide with Agent OS
- Tracks PIDs for frontend/backend processes
- Detects and kills orphaned/zombie processes
- Enables safe workspace deletion by stopping processes first
- Persists registry to disk for crash recovery
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import signal
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.schemas import RuntimeEntry
from app.services.time_service import now_label

logger = logging.getLogger("runtime_manager")


class RuntimeManager:
    """Manages generated project runtimes — ports, processes, health."""

    def __init__(self):
        self.registry: dict[str, RuntimeEntry] = {}
        self._allocated_ports: set[int] = set(settings.reserved_ports)
        self._next_frontend_port: int = settings.port_range_frontend[0]
        self._next_backend_port: int = settings.port_range_backend[0]
        self._health_task: asyncio.Task | None = None
        self._registry_path = os.path.join(
            settings.data_dir.replace("/", os.sep), "runtime_registry.json"
        )

        # Load persisted registry on init
        self._load_registry()

    # ── Port Allocation ───────────────────────────────────────────────────

    def allocate_ports(self, workspace_id: str) -> tuple[int, int]:
        """Allocate a unique frontend + backend port pair for a workspace.

        Returns (frontend_port, backend_port).
        """
        # Check if workspace already has ports
        entry = self.registry.get(workspace_id)
        if entry and entry.frontend_port and entry.backend_port:
            return entry.frontend_port, entry.backend_port

        frontend_port = self._find_available_port(
            settings.port_range_frontend[0],
            settings.port_range_frontend[1],
        )
        backend_port = self._find_available_port(
            settings.port_range_backend[0],
            settings.port_range_backend[1],
        )

        self._allocated_ports.add(frontend_port)
        self._allocated_ports.add(backend_port)

        logger.info(
            "Allocated ports for %s: frontend=%d, backend=%d",
            workspace_id, frontend_port, backend_port,
        )

        return frontend_port, backend_port

    def _find_available_port(self, start: int, end: int) -> int:
        """Find the next available port in range, checking both registry and OS."""
        for port in range(start, end + 1):
            if port in self._allocated_ports:
                continue
            if port in settings.reserved_ports:
                continue
            if self._is_port_in_use(port):
                self._allocated_ports.add(port)
                continue
            return port

        raise RuntimeError(f"No available ports in range {start}–{end}")

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        """Check if a port is currently in use at the OS level."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                return sock.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False

    # ── Process Registration ──────────────────────────────────────────────

    def register_runtime(
        self,
        workspace_id: str,
        project_name: str = "",
        frontend_port: int | None = None,
        backend_port: int | None = None,
    ) -> RuntimeEntry:
        """Register a new runtime entry (ports allocated, processes not yet started)."""
        if not frontend_port or not backend_port:
            frontend_port, backend_port = self.allocate_ports(workspace_id)

        entry = RuntimeEntry(
            workspace_id=workspace_id,
            project_name=project_name,
            frontend_port=frontend_port,
            backend_port=backend_port,
            status="stopped",
            started_at=now_label(),
        )
        self.registry[workspace_id] = entry
        self._persist_registry()
        return entry

    def register_process(
        self,
        workspace_id: str,
        pid: int,
        role: str = "frontend",  # "frontend" | "backend"
    ) -> RuntimeEntry:
        """Register a running process PID for a workspace."""
        entry = self.registry.get(workspace_id)
        if not entry:
            entry = self.register_runtime(workspace_id)

        updates: dict[str, Any] = {"status": "running"}
        if role == "frontend":
            updates["frontend_pid"] = pid
        elif role == "backend":
            updates["backend_pid"] = pid

        updated = entry.model_copy(update=updates)
        self.registry[workspace_id] = updated
        self._persist_registry()

        logger.info("Registered %s PID %d for workspace %s", role, pid, workspace_id)
        return updated

    # ── Process Control ───────────────────────────────────────────────────

    def stop_runtime(self, workspace_id: str) -> bool:
        """Stop all processes for a workspace and release ports."""
        entry = self.registry.get(workspace_id)
        if not entry:
            return False

        stopped = False

        for pid in (entry.frontend_pid, entry.backend_pid):
            if pid and self._is_process_alive(pid):
                self._kill_process(pid)
                stopped = True

        # Release ports
        if entry.frontend_port:
            self._allocated_ports.discard(entry.frontend_port)
        if entry.backend_port:
            self._allocated_ports.discard(entry.backend_port)

        # Update registry
        updated = entry.model_copy(update={
            "status": "stopped",
            "frontend_pid": None,
            "backend_pid": None,
        })
        self.registry[workspace_id] = updated
        self._persist_registry()

        logger.info("Stopped runtime for workspace %s", workspace_id)
        return stopped

    def stop_all(self) -> int:
        """Stop all registered runtimes. Returns count of workspaces stopped."""
        count = 0
        for workspace_id in list(self.registry.keys()):
            if self.stop_runtime(workspace_id):
                count += 1
        return count

    # ── Health Checking ───────────────────────────────────────────────────

    def check_health(self, workspace_id: str) -> dict:
        """Check process health for a workspace."""
        entry = self.registry.get(workspace_id)
        if not entry:
            return {"workspace_id": workspace_id, "status": "not_registered"}

        frontend_alive = bool(entry.frontend_pid and self._is_process_alive(entry.frontend_pid))
        backend_alive = bool(entry.backend_pid and self._is_process_alive(entry.backend_pid))

        # Calculate uptime
        uptime_seconds = 0.0
        if entry.started_at and entry.status == "running":
            try:
                started = datetime.strptime(entry.started_at, "%Y-%m-%d %H:%M:%S")
                uptime_seconds = (datetime.now() - started).total_seconds()
            except (ValueError, TypeError):
                pass

        # Update status if processes died
        if entry.status == "running" and not frontend_alive and not backend_alive:
            updated = entry.model_copy(update={"status": "stopped"})
            self.registry[workspace_id] = updated
            self._persist_registry()

        return {
            "workspace_id": workspace_id,
            "status": entry.status,
            "frontend_alive": frontend_alive,
            "backend_alive": backend_alive,
            "frontend_port": entry.frontend_port,
            "backend_port": entry.backend_port,
            "uptime_seconds": round(uptime_seconds, 1),
        }

    def get_runtime(self, workspace_id: str) -> RuntimeEntry | None:
        """Get runtime entry for a workspace."""
        return self.registry.get(workspace_id)

    def list_runtimes(self) -> list[RuntimeEntry]:
        """List all registered runtimes."""
        return list(self.registry.values())

    # ── Orphan Cleanup ────────────────────────────────────────────────────

    def cleanup_orphans(self) -> int:
        """Detect and kill orphaned processes. Returns count cleaned."""
        cleaned = 0
        for workspace_id, entry in list(self.registry.items()):
            if entry.status != "running":
                continue

            frontend_alive = bool(entry.frontend_pid and self._is_process_alive(entry.frontend_pid))
            backend_alive = bool(entry.backend_pid and self._is_process_alive(entry.backend_pid))

            if not frontend_alive and not backend_alive:
                # Processes died on their own — clean up registry
                updated = entry.model_copy(update={
                    "status": "stopped",
                    "frontend_pid": None,
                    "backend_pid": None,
                })
                self.registry[workspace_id] = updated
                cleaned += 1
                logger.info("Cleaned orphaned entry for workspace %s", workspace_id)

        if cleaned:
            self._persist_registry()
            logger.info("Cleaned %d orphaned runtime entries", cleaned)

        return cleaned

    async def start_health_monitor(self) -> None:
        """Start periodic health monitoring as background task."""
        if self._health_task and not self._health_task.done():
            return

        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("Runtime health monitor started (interval=%ds)", settings.orphan_cleanup_interval_seconds)

    async def _health_loop(self) -> None:
        """Periodic health check loop."""
        while True:
            try:
                await asyncio.sleep(settings.orphan_cleanup_interval_seconds)
                self.cleanup_orphans()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health monitor error: %s", e)

    # ── Process Utilities ─────────────────────────────────────────────────

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if a process with the given PID is alive."""
        try:
            os.kill(pid, 0)  # Signal 0 = check existence, don't actually kill
            return True
        except (OSError, ProcessLookupError):
            return False

    @staticmethod
    def _kill_process(pid: int) -> bool:
        """Kill a process by PID. Returns True if successfully killed."""
        try:
            # On Windows, os.kill with SIGTERM works; for forceful kill use taskkill
            if os.name == "nt":
                import subprocess
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=10,
                )
            else:
                os.kill(pid, signal.SIGTERM)
                # Wait briefly, then force kill if still alive
                import time
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

            logger.info("Killed process PID %d", pid)
            return True
        except Exception as e:
            logger.warning("Failed to kill PID %d: %s", pid, e)
            return False

    # ── Persistence ───────────────────────────────────────────────────────

    def _persist_registry(self) -> None:
        """Save runtime registry to disk."""
        try:
            os.makedirs(os.path.dirname(self._registry_path), exist_ok=True)
            data = {
                wid: entry.model_dump()
                for wid, entry in self.registry.items()
            }
            with open(self._registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.warning("Failed to persist runtime registry: %s", e)

    def _load_registry(self) -> None:
        """Load runtime registry from disk."""
        if not os.path.exists(self._registry_path):
            return
        try:
            with open(self._registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for wid, entry_data in data.items():
                self.registry[wid] = RuntimeEntry(**entry_data)
                # Track allocated ports
                if entry_data.get("frontend_port"):
                    self._allocated_ports.add(entry_data["frontend_port"])
                if entry_data.get("backend_port"):
                    self._allocated_ports.add(entry_data["backend_port"])
            logger.info("Loaded %d runtime entries from disk", len(self.registry))
        except Exception as e:
            logger.warning("Failed to load runtime registry: %s", e)

    def remove_runtime(self, workspace_id: str) -> None:
        """Remove a runtime entry from the registry entirely."""
        entry = self.registry.pop(workspace_id, None)
        if entry:
            if entry.frontend_port:
                self._allocated_ports.discard(entry.frontend_port)
            if entry.backend_port:
                self._allocated_ports.discard(entry.backend_port)
            self._persist_registry()


# ── Singleton ─────────────────────────────────────────────────────────────

runtime_manager = RuntimeManager()
