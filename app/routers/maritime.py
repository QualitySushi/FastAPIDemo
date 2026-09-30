import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.maritime_engine import MaritimeVoronoiEngine

router = APIRouter(tags=["Maritime Grid"])
engine = MaritimeVoronoiEngine()

@router.websocket("/ws/maritime")
async def websocket_maritime(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            mesh_data = engine.compute_tessellation()
            await websocket.send_text(json.dumps({"success": True, "data": mesh_data}))
            await asyncio.sleep(0.1) # Broadcast updates smoothly
    except WebSocketDisconnect:
        print("Client disconnected from live maritime stream.")