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

        channel = self.channel_for_event(event.type)
        if channel and event.payload:
            await websocket_manager.broadcast(channel, event.payload)

        return activity

    def channel_for_event(self, event_type: str) -> str | None:
        if event_type.startswith("AGENT_"):
            return "agents"
        if event_type.startswith("TASK_"):
            return "tasks"
        if event_type.startswith("WORKSPACE_"):
            return "workspaces"
        if event_type.startswith("BUILD_"):
            return "build"
        if event_type.startswith("SECURITY_"):
            return "build"
        if event_type.startswith("FILE_"):
            return "build"
        return None


event_bus = EventBus()
