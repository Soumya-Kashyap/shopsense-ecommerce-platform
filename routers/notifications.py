from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket_manager import manager

router = APIRouter(
    tags=["WebSockets (Milestone 3)"]
)


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint at /ws/notifications:
    - Accepts WebSocket connections from admin dashboards
    - Maintains connection in active clients list
    - Listens for messages or disconnect events
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open & handle incoming client messages if any
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
