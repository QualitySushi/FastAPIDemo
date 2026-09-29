from typing import Any
import numpy as np
from app.schemas import SimulationConfig

class BoidsEngine:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.num = config.num_particles
        self.width = config.width
        self.height = config.height

        self.positions = np.random.rand(self.num, 2) * np.array(
            [self.width, self.height]
        )

        angles = np.random.rand(self.num) * 2 * np.pi
        self.velocities = np.column_stack((np.cos(angles), np.sin(angles))) * 2.0

    def update(self, new_config: dict[str, Any] | None = None):
        if new_config:
            for key, val in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, val)

        n = self.num
        pos = self.positions
        vel = self.velocities

        diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        dist = np.linalg.norm(diff, axis=-1)

        neighbor_dist = 50.0
        mask = (dist > 0) & (dist < neighbor_dist)

        sep_mask = (dist > 0) & (dist < 25.0)
        steer_sep = np.zeros_like(vel)
        for i in range(n):
            neighbors = sep_mask[i]
            if np.any(neighbors):
                away = pos[i] - pos[neighbors]
                d_inv = 1.0 / (dist[i, neighbors, np.newaxis] + 1e-5)
                steer_sep[i] = np.sum(away * d_inv, axis=0)

        steer_align = np.zeros_like(vel)
        steer_cohesion = np.zeros_like(vel)

        for i in range(n):
            neighbors = mask[i]
            if np.any(neighbors):
                avg_vel = np.mean(vel[neighbors], axis=0)
                steer_align[i] = avg_vel - vel[i]

                avg_pos = np.mean(pos[neighbors], axis=0)
                steer_cohesion[i] = avg_pos - pos[i]

        accel = (
            steer_sep * self.config.separation_weight
            + steer_align * self.config.alignment_weight
            + steer_cohesion * self.config.cohesion_weight
        )

        vel += accel * 0.05
        speeds = np.linalg.norm(vel, axis=1, keepdims=True)
        exceeds = speeds > self.config.max_speed
        if np.any(exceeds):
            vel[exceeds.flatten()] = (
                vel[exceeds.flatten()] / speeds[exceeds.flatten()]
            ) * self.config.max_speed

        pos += vel
        pos[:, 0] = np.mod(pos[:, 0], self.width)
        pos[:, 1] = np.mod(pos[:, 1], self.height)

        self.positions = pos
        self.velocities = vel

    def get_serialized_state(self):
        return [
            {
                "id": i,
                "x": float(self.positions[i, 0]),
                "y": float(self.positions[i, 1]),
            }
            for i in range(self.num)
        ]