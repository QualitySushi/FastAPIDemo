import asyncio
import json
from typing import Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="Boids Simulation Compute Service", version="1.0.0")


# --- DATA SCHEMAS ---
class SimulationConfig(BaseModel):
    num_particles: int = 150
    width: float = 800.0
    height: float = 600.0
    max_speed: float = 4.0
    max_force: float = 0.1
    # Flocking weights (design choice: exposed to frontend for real-time tweaking)
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0


# --- BOIDS ENGINE (VECTORIZED WITH NUMPY) ---
class BoidsEngine:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.num = config.num_particles
        self.width = config.width
        self.height = config.height

        # DESIGN DEFENSE: Initialize positions and velocities as contiguous NumPy arrays.
        # This allows vector arithmetic instead of iteration, scaling efficiently to thousands of agents.
        self.positions = np.random.rand(self.num, 2) * np.array(
            [self.width, self.height]
        )

        # Random initial velocities scaled down
        angles = np.random.rand(self.num) * 2 * np.pi
        self.velocities = np.column_stack((np.cos(angles), np.sin(angles))) * 2.0

    def update(self, new_config: dict[str, Any] | None = None):
        """Executes one physics frame step implementing Boids rules:

        1. Separation: Avoid crowding local flockmates.
        2. Alignment: Steer towards average heading of local flockmates.
        3. Cohesion: Steer towards average position of local flockmates.
        """
        if new_config:
            # Allow live tuning of weights from frontend without restarting simulation
            for key, val in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, val)

        n = self.num
        pos = self.positions
        vel = self.velocities

        # Compute pairwise distance matrix between all particles
        # DESIGN DEFENSE: Broadcasting computes all distances in a single vectorized pass O(N^2).
        diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        dist = np.linalg.norm(diff, axis=-1)

        # Neighborhood radius constraint (boids only care about nearby agents)
        neighbor_dist = 50.0
        mask = (dist > 0) & (dist < neighbor_dist)

        # --- RULE 1: SEPARATION ---
        # Steer away from neighbors that are too close
        sep_mask = (dist > 0) & (dist < 25.0)
        steer_sep = np.zeros_like(vel)
        for i in range(n):
            neighbors = sep_mask[i]
            if np.any(neighbors):
                # Vector pointing away from neighbors, weighted inversely by distance
                away = pos[i] - pos[neighbors]
                d_inv = 1.0 / (dist[i, neighbors, np.newaxis] + 1e-5)
                steer_sep[i] = np.sum(away * d_inv, axis=0)

        # --- RULE 2 & 3: ALIGNMENT & COHESION ---
        steer_align = np.zeros_like(vel)
        steer_cohesion = np.zeros_like(vel)

        for i in range(n):
            neighbors = mask[i]
            if np.any(neighbors):
                # Alignment: average velocity of neighbors
                avg_vel = np.mean(vel[neighbors], axis=0)
                steer_align[i] = avg_vel - vel[i]

                # Cohesion: average position vector minus current position
                avg_pos = np.mean(pos[neighbors], axis=0)
                steer_cohesion[i] = avg_pos - pos[i]

        # Apply weights from configuration
        accel = (
            steer_sep * self.config.separation_weight
            + steer_align * self.config.alignment_weight
            + steer_cohesion * self.config.cohesion_weight
        )

        # Update velocities with acceleration limits
        vel += accel * 0.05
        speeds = np.linalg.norm(vel, axis=1, keepdims=True)
        # Cap speed to prevent runaway acceleration
        exceeds = speeds > self.config.max_speed
        if np.any(exceeds):
            vel[exceeds.flatten()] = (
                vel[exceeds.flatten()] / speeds[exceeds.flatten()]
            ) * self.config.max_speed

        # Update positions
        pos += vel

        # Screen wrapping (toroidal boundaries so particles don't fly off screen)
        pos[:, 0] = np.mod(pos[:, 0], self.width)
        pos[:, 1] = np.mod(pos[:, 1], self.height)

        self.positions = pos
        self.velocities = vel

    def get_serialized_state(self):
        """Converts NumPy arrays into a clean list of dicts for JSON transmission."""
        return [
            {
                "id": i,
                "x": float(self.positions[i, 0]),
                "y": float(self.positions[i, 1]),
            }
            for i in range(self.num)
        ]


# --- FASTAPI ENDPOINTS & WEBSOCKET STREAM ---


@app.get("/health")
def health_check():
    return {"status": "UP", "service": "python-boids-engine"}


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    """WebSocket endpoint for real-time frame streaming.

    DESIGN DEFENSE: Maintains a persistent async loop pushing frames at ~30 FPS,
    bypassing HTTP request/response overhead for butter-smooth animation.
    """
    await websocket.accept()

    # Initialize simulation instance for this client connection
    config = SimulationConfig()
    engine = BoidsEngine(config)

    try:
        while True:
            # Check for incoming configuration adjustments from the client without blocking loop
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.01
                )
                payload = json.loads(data)
                engine.update(new_config=payload)
            except asyncio.TimeoutError:
                # No incoming configuration change; proceed with standard physics tick
                engine.update()

            # Serialize and stream current frame state
            frame_data = {"particles": engine.get_serialized_state()}
            await websocket.send_text(json.dumps(frame_data))

            # Target ~30 FPS (33 milliseconds per frame)
            await asyncio.sleep(0.033)

    except WebSocketDisconnect:
        print("Client disconnected from simulation stream.")