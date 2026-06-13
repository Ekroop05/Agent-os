from app.core.websocket_manager import websocket_manager
from app.schemas import Event
from app.services.activity_service import activity_service
from app.services.system_service import system_service


class EventBus:
    async def publish(self, event: Event):
        activity = activity_service.create(
            source=event.source,
            event_type=event.type,
            message=event.message,
            severity=event.severity,
        )

        await websocket_manager.broadcast("activity", activity.model_dump())
        await websocket_manager.broadcast("system", system_service.status().model_dump())

        # Build the standardized event envelope
        envelope = {
            "event_type": event.type,
            "source": event.source,
            "message": event.message,
            "severity": event.severity,
            "payload": event.payload or {},
        }

        channels = self._channels_for_event(event.type)
        for channel in channels:
            await websocket_manager.broadcast(channel, envelope)

        # Broadcast workspace state whenever build-related events happen
        if event.type.startswith(("BUILD_", "SECURITY_")):
            workspace_id = (event.payload or {}).get("workspace_id")
            if workspace_id:
                await self._broadcast_workspace(workspace_id)

        return activity

    def _channels_for_event(self, event_type: str) -> list[str]:
        """Return ALL channels an event should be broadcast to.

        IMPORTANT: Domain channels ('agents', 'tasks', 'workspaces') receive
        events whose payloads are full domain objects (Agent, Task, Workspace).
        Build pipeline events are notification-only and go to 'build' only.
        """
        if event_type.startswith("AGENT_"):
            return ["agents"]
        if event_type.startswith("TASK_"):
            return ["tasks"]
        if event_type.startswith("WORKSPACE_"):
            return ["workspaces"]
        # Build pipeline events go to the build channel ONLY.
        # They are notifications, not full task/workspace state objects.
        # The actual task state updates come through TASK_STARTED / TASK_COMPLETED
        # events which are published separately.
        if event_type.startswith("BUILD_"):
            return ["build"]
        if event_type.startswith("SECURITY_"):
            return ["build"]
        if event_type.startswith("FILE_"):
            return ["build"]
        if event_type.startswith("ARCHITECT_"):
            return ["build"]
        return []

    async def _broadcast_workspace(self, workspace_id: str) -> None:
        """Push the current workspace state to all workspace listeners."""
        try:
            from app.services.workspace_service import workspace_service
            workspace = workspace_service.get(workspace_id)
            envelope = {
                "event_type": "WORKSPACE_STATE_SYNC",
                "source": "Event Bus",
                "message": f"Workspace state sync: {workspace.name}",
                "severity": "info",
                "payload": workspace.model_dump(),
            }
            await websocket_manager.broadcast("workspaces", envelope)
        except Exception:
            pass


event_bus = EventBus()
