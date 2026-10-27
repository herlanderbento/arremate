from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auction.infra.ws.connection_manager import lot_rooms

router = APIRouter(tags=["Lot room"])


@router.websocket("/ws/lots/{lot_id}")
async def lot_room(websocket: WebSocket, lot_id: UUID):
    await lot_rooms.connect(lot_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        lot_rooms.disconnect(lot_id, websocket)
