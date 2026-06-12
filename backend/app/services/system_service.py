import os

from app.core.websocket_manager import websocket_manager
from app.schemas import SystemStatus
from app.services.agent_service import agent_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service


class SystemService:
    def status(self) -> SystemStatus:
        active_agents = len([agent for agent in agent_service.list() if agent.status == "Running"])
        active_tasks = len([task for task in task_service.list() if task.status in {"Running", "Reviewing"}])
        active_workspaces = len([workspace for workspace in workspace_service.list() if workspace.status == "Active"])
        memory_usage = min(95, 38 + active_agents * 7 + active_tasks * 3)
        cpu_usage = min(96, 24 + active_agents * 8 + active_tasks * 5)

        try:
            load = os.getloadavg()[0]
            cpu_usage = min(100, int(load * 20))
        except (AttributeError, OSError):
            pass

        return SystemStatus(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            active_connections=websocket_manager.connection_count(),
            active_agents=active_agents,
            active_tasks=active_tasks,
            active_workspaces=active_workspaces,
        )


system_service = SystemService()
