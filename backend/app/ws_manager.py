from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Maps order_id to a list of connected WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # List of connections for the home page
        self.home_connections: List[WebSocket] = []
        # Maps vote_id to a list of connected WebSockets
        self.vote_connections: Dict[int, List[WebSocket]] = {}

    # --- Orders ---
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

    # --- Home ---
    async def connect_home(self, websocket: WebSocket):
        await websocket.accept()
        self.home_connections.append(websocket)

    def disconnect_home(self, websocket: WebSocket):
        if websocket in self.home_connections:
            self.home_connections.remove(websocket)

    async def broadcast_home_update(self):
        for connection in list(self.home_connections):
            try:
                await connection.send_text("update")
            except Exception:
                self.disconnect_home(connection)

    # --- Votes ---
    async def connect_vote(self, websocket: WebSocket, vote_id: int):
        await websocket.accept()
        if vote_id not in self.vote_connections:
            self.vote_connections[vote_id] = []
        self.vote_connections[vote_id].append(websocket)

    def disconnect_vote(self, websocket: WebSocket, vote_id: int):
        if vote_id in self.vote_connections:
            if websocket in self.vote_connections[vote_id]:
                self.vote_connections[vote_id].remove(websocket)
            if not self.vote_connections[vote_id]:
                del self.vote_connections[vote_id]

    async def broadcast_vote_update(self, vote_id: int):
        if vote_id in self.vote_connections:
            for connection in list(self.vote_connections[vote_id]):
                try:
                    await connection.send_text("update")
                except Exception:
                    self.disconnect_vote(connection, vote_id)

manager = ConnectionManager()
