from pydantic import BaseModel

class SimulationConfig(BaseModel):
    num_particles: int = 150
    width: float = 800.0
    height: float = 600.0
    max_speed: float = 4.0
    max_force: float = 0.1
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0