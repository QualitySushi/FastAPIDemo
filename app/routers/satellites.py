import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.services.satellite_service import (
    get_satellite_constellation_positions,
    initialize_satellites,
)

router = APIRouter(tags=["Satellites"])

@router.get("/satellites")  # Clean path becomes /api/satellites
def get_satellites_snapshot():
    """HTTP REST endpoint serving a single snapshot of the current satellite constellation positions."""
    try:
        satellites_payload = get_satellite_constellation_positions()
        if not satellites_payload:
            initialize_satellites()
            satellites_payload = get_satellite_constellation_positions()
            
            if not satellites_payload:
                raise HTTPException(status_code=404, detail="No satellite telemetry snapshot available yet")
                
        return satellites_payload
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/satellites")  # Clean path becomes /ws/satellites (or /api/ws/satellites if preferred)
async def satellite_websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time multi-satellite orbital tracking telemetry stream."""
    await websocket.accept()
    initialize_satellites()
    
    try:
        while True:
            satellites_payload = get_satellite_constellation_positions()
            if satellites_payload:
                await websocket.send_text(json.dumps(satellites_payload))
            else:
                await websocket.send_json({"error": "Failed to resolve satellite constellation"})
            
            await asyncio.sleep(1.0)
            
    except WebSocketDisconnect:
        print("Client disconnected from satellite stream.")
    except Exception as e:
        print(f"Error in satellite stream: {e}")