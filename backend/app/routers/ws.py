from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws_manager import manager

router = APIRouter(prefix="/api/ws", tags=["websocket"])

@router.websocket("/orders/{order_id}")
async def websocket_order_endpoint(websocket: WebSocket, order_id: int):
    await manager.connect(websocket, order_id)
    try:
        while True:
            # Receive data to keep connection open and detect disconnects
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, order_id)
    except Exception:
        manager.disconnect(websocket, order_id)

@router.websocket("/home")
async def websocket_home_endpoint(websocket: WebSocket):
    await manager.connect_home(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_home(websocket)
    except Exception:
        manager.disconnect_home(websocket)

@router.websocket("/votes/{vote_id}")
async def websocket_vote_endpoint(websocket: WebSocket, vote_id: int):
    await manager.connect_vote(websocket, vote_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_vote(websocket, vote_id)
    except Exception:
        manager.disconnect_vote(websocket, vote_id)
