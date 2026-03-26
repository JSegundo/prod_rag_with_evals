import time

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}
        self.pending_messages: dict[str, list[dict]] = {}

    async def connect(self, file_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[file_id] = websocket

        # Send initial connection message
        await websocket.send_json({
            "type": "status_update",
            "fileId": file_id,
            "status": "connected",
            "metadata": {"timestamp": int(time.time())},
        })

        # Deliver any pending messages
        pending = self.pending_messages.pop(file_id, [])
        for msg in pending:
            await websocket.send_json(msg)

    def disconnect(self, file_id: str):
        self.connections.pop(file_id, None)

    async def send_status(self, file_id: str, status: str, metadata: dict | None = None):
        msg = {
            "type": "status_update",
            "fileId": file_id,
            "status": status,
            "metadata": metadata or {},
        }

        ws = self.connections.get(file_id)
        if ws:
            try:
                await ws.send_json(msg)
            except Exception:
                # Connection might be closed, queue the message
                self.connections.pop(file_id, None)
                self.pending_messages.setdefault(file_id, []).append(msg)
        else:
            self.pending_messages.setdefault(file_id, []).append(msg)


manager = ConnectionManager()
