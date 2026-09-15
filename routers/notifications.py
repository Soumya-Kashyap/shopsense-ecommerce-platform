from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket_manager import manager

router = APIRouter(
    tags=["Real-Time WebSockets"]
)


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(websocket: WebSocket):
    """
    WebSocket Live Event Broadcast Channel:
    - Accepts WebSocket connections from administrative dashboards.
    - Tracks client connection lifecycle.
    - Receives real-time sale transaction event broadcasts.
    """
    await manager.connect(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
