import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.attractor_engine import AttractorEngine

router = APIRouter(tags=["Attractors"])


@router.websocket("/ws/attractor")
async def websocket_attractor(websocket: WebSocket):
    await websocket.accept()

    # Initialize engine with default Clifford parameters
    engine = AttractorEngine(attractor_type="clifford")

    try:
        while True:
            payload = None

            try:
                # Check for an incoming frontend configuration update
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=0.01
                )

                if "text" in message:
                    payload = json.loads(message["text"])
                    print("WEBSOCKET RECEIVED TEXT:", payload)

                elif "bytes" in message:
                    payload = json.loads(message["bytes"].decode("utf-8"))
                    print("WEBSOCKET RECEIVED BYTES:", payload)

            except asyncio.TimeoutError:
                pass

            except Exception as e:
                print("Error processing incoming WS message:", e)

            if payload is not None:
                engine.update(new_config=payload)
            else:
                engine.update()

            frame_data = {
                "success": True,
                "type": engine.attractor_type,
                "points": engine.get_serialized_state()
            }

            await websocket.send_text(json.dumps(frame_data))
            await asyncio.sleep(0.016)

    except WebSocketDisconnect:
        print("Client disconnected from attractor simulation stream.")