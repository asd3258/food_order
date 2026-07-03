from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Maps order_id to a list of connected WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, order_id: int):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

    def disconnect(self, websocket: WebSocket, order_id: int):
        if order_id in self.active_connections:
            if websocket in self.active_connections[order_id]:
                self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def broadcast_order_update(self, order_id: int):
        """Send a generic update ping to all clients watching this order."""
        if order_id in self.active_connections:
            # Create a copy of the list in case of concurrent disconnects
            for connection in list(self.active_connections[order_id]):
                try:
                    await connection.send_text("update")
                except Exception:
                    # If sending fails, it usually means the connection is dead
                    self.disconnect(connection, order_id)

manager = ConnectionManager()
