"""Sprint 5: Real System Monitoring Service (Feature 9)

Replaces mock CPU/memory formulas with real psutil-based metrics.
Provides actual machine resource data to the frontend.
"""

import os
import time

import psutil

from app.core.websocket_manager import websocket_manager
from app.schemas import SystemStatus
from app.services.agent_service import agent_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service


class SystemService:
    def __init__(self):
        self._start_time = time.time()
        # Prime CPU measurement (first call always returns 0)
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def status(self) -> SystemStatus:
        active_agents = len([agent for agent in agent_service.list() if agent.status == "Running"])
        active_tasks = len([task for task in task_service.list() if task.status in {"Running", "Reviewing"}])
        active_workspaces = len([workspace for workspace in workspace_service.list() if workspace.status in {"Building", "Reviewing", "Planning"}])

        # Real metrics from psutil
        try:
            cpu_usage = int(psutil.cpu_percent(interval=None))
        except Exception:
            cpu_usage = 0

        available_memory_gb = 0.0
        try:
            mem = psutil.virtual_memory()
            memory_usage = int(mem.percent)
            available_memory_gb = round(mem.available / (1024 * 1024 * 1024), 1)
        except Exception:
            memory_usage = 0

        try:
            disk = psutil.disk_usage("/")
            disk_usage = int(disk.percent)
        except Exception:
            try:
                disk = psutil.disk_usage("C:\\")
                disk_usage = int(disk.percent)
            except Exception:
                disk_usage = 0

        # Agent OS process memory
        try:
            process = psutil.Process(os.getpid())
            process_memory_mb = round(process.memory_info().rss / (1024 * 1024), 1)
        except Exception:
            process_memory_mb = 0

        # System uptime
        try:
            boot = psutil.boot_time()
            uptime_seconds = time.time() - boot
            uptime = self._format_uptime(uptime_seconds)
        except Exception:
            uptime = self._format_uptime(time.time() - self._start_time)

        # Count Python & Agent OS processes
        python_processes = 0
        agent_os_processes = 0
        try:
            for proc in psutil.process_iter(["name", "cmdline"]):
                name = (proc.info.get("name") or "").lower()
                cmdline = proc.info.get("cmdline") or []
                cmd_str = " ".join(cmdline).lower()
                if "python" in name or "python" in cmd_str:
                    python_processes += 1
                    if "uvicorn" in cmd_str or "agent" in cmd_str or "main:app" in cmd_str or proc.pid == os.getpid():
                        agent_os_processes += 1
        except Exception:
            pass
        if agent_os_processes == 0:
            agent_os_processes = 1

        return SystemStatus(
            cpu_usage=min(cpu_usage, 100),
            memory_usage=min(memory_usage, 100),
            disk_usage=min(disk_usage, 100),
            active_connections=websocket_manager.connection_count(),
            active_agents=active_agents,
            active_tasks=active_tasks,
            active_workspaces=active_workspaces,
            process_memory_mb=process_memory_mb,
            system_uptime=uptime,
            python_processes=python_processes,
            agent_os_processes=agent_os_processes,
            available_memory_gb=available_memory_gb,
            agent_os_pid=os.getpid(),
        )

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime as human-readable string."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


system_service = SystemService()
