from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/status/{file_id}")
async def status_websocket(websocket: WebSocket, file_id: str):
    await manager.connect(file_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(file_id)
