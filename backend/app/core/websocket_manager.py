from collections import defaultdict

from fastapi import WebSocket


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
        for connection in list(self.active_connections[channel]):
            try:
                await connection.send_json(message)
            except RuntimeError:
                self.disconnect(channel, connection)


websocket_manager = WebSocketManager()
