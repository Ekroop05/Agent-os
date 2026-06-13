import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger("websocket_manager")


class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[channel].append(websocket)

    def disconnect(self, channel: str, websocket: WebSocket):
        if websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)

    def connection_count(self, channel: str | None = None) -> int:
        if channel:
            return len(self.active_connections[channel])
        return sum(len(connections) for connections in self.active_connections.values())

    async def broadcast(self, channel: str, message: dict):
        dead_connections = []
        for connection in list(self.active_connections[channel]):
            try:
                await connection.send_json(message)
            except Exception:
                # Catch ALL exceptions (RuntimeError, WebSocketDisconnect,
                # ClientDisconnected, ConnectionClosedError) so a single
                # dead socket never crashes the event bus pipeline.
                dead_connections.append(connection)

        for connection in dead_connections:
            self.disconnect(channel, connection)
            logger.debug("Removed dead WebSocket connection from channel '%s'", channel)


websocket_manager = WebSocketManager()
