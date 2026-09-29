import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas import SimulationConfig
from app.services.boids_engine import BoidsEngine

router = APIRouter(tags=["Simulation"])

@router.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await websocket.accept()
    config = SimulationConfig()
    engine = BoidsEngine(config)

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), timeout=0.01
                )
                if message.get("type") == "websocket.receive" and "text" in message:
                    payload = json.loads(message["text"])
                    engine.update(new_config=payload)
                else:
                    engine.update()
            except asyncio.TimeoutError:
                engine.update()

            frame_data = {"particles": engine.get_serialized_state()}
            await websocket.send_text(json.dumps(frame_data))
            await asyncio.sleep(0.033)

    except WebSocketDisconnect:
        print("Client disconnected from boids simulation stream.")