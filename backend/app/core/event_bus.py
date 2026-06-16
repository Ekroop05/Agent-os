import uuid
from collections import deque

from app.core.websocket_manager import websocket_manager
from app.schemas import Event, TimelineEvent
from app.services.activity_service import activity_service
from app.services.system_service import system_service
from app.services.time_service import now_label


class EventBus:
    def __init__(self):
        # Sprint 4.5: Timeline accumulator for global event history
        self._timeline: deque[TimelineEvent] = deque(maxlen=200)

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

        # Sprint 4.5: Accumulate timeline events
        self._timeline.append(TimelineEvent(
            id=f"evt-{uuid.uuid4().hex[:8]}",
            timestamp=now_label(),
            event_type=event.type,
            source=event.source,
            message=event.message,
            severity=event.severity,
            workspace_id=(event.payload or {}).get("workspace_id"),
            job_id=(event.payload or {}).get("job_id"),
        ))

        # Broadcast workspace state whenever build-related events happen
        if event.type.startswith(("BUILD_", "SECURITY_")):
            workspace_id = (event.payload or {}).get("workspace_id")
            if workspace_id:
                await self._broadcast_workspace(workspace_id)

        return activity

    def get_timeline(self, limit: int = 100) -> list[dict]:
        """Return the most recent timeline events."""
        items = list(self._timeline)
        items.reverse()  # Most recent first
        return [e.model_dump() for e in items[:limit]]

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
        # Build pipeline events
        if event_type.startswith("BUILD_"):
            return ["build"]
        if event_type.startswith("SECURITY_"):
            return ["build"]
        if event_type.startswith("FILE_"):
            return ["build"]
        if event_type.startswith("ARCHITECT_"):
            return ["build"]
        # Sprint 4.5: Job events
        if event_type.startswith("JOB_"):
            return ["jobs"]
        # Sprint 4.5: Runtime events
        if event_type.startswith("RUNTIME_"):
            return ["runtimes"]
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
