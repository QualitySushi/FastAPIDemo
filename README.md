# Polyglot Tech Demo Compute Service

A FastAPI-based compute service for the Polyglot Tech Demo. The service provides real-time mathematical simulations, chaotic attractor generation, satellite orbital telemetry, and maritime spatial tessellation through REST and WebSocket interfaces.

The service is designed as the Python compute layer in a polyglot architecture:

```text
Frontend / Desktop App
        │
        ▼
Express Gateway :4000
        │
        ▼
FastAPI Compute Service :8000
        │
        ├── Boids simulation
        ├── Chaotic attractors
        ├── Satellite telemetry
        └── Maritime AIS / Voronoi processing
```

---

## Architecture

The FastAPI service follows a separation-of-concerns structure:

```text
compute-service/
├── app/
│   ├── routers/
│   │   ├── health.py
│   │   ├── satellites.py
│   │   ├── simulation.py
│   │   ├── maritime.py
│   │   └── attractors.py
│   │
│   ├── services/
│   │   ├── attractor_engine.py
│   │   ├── boids_engine.py
│   │   ├── maritime_engine.py
│   │   └── satellite_service.py
│   │
│   ├── schemas.py
│   └── main.py
│
├── requirements.txt
└── README.md
```

### Application Layer

`app/main.py` creates the FastAPI application, configures CORS, and registers the service routers under the `/api` prefix.

### Router Layer

`app/routers/` contains the HTTP and WebSocket transport layer.

Routers are responsible for:

- HTTP endpoint definitions
- WebSocket connection handling
- Receiving configuration updates
- Returning serialized simulation state
- Managing connection lifecycle events

### Service Layer

`app/services/` contains the compute and domain logic.

The service implementations include:

- `AttractorEngine` — chaotic attractor generation and parameter updates
- `BoidsEngine` — flocking simulation and particle state updates
- `MaritimeVoronoiEngine` — AIS ingestion, vessel projection, fallback movement, and Voronoi tessellation
- `satellite_service.py` — TLE retrieval, satellite initialization, and orbital position calculation

This keeps mathematical and external-data processing separate from the FastAPI transport layer.

---

## API

The service runs on:

```text
http://localhost:8000
```

All HTTP routers are mounted under:

```text
/api
```

### Health

```http
GET /api/health
```

Provides a basic service health response.

### Satellite Telemetry

```http
GET /api/satellites
```

Returns the current 3D Cartesian positions of the cached satellite constellation.

The satellite service:

1. Attempts to retrieve the CelesTrak stations TLE group.
2. Falls back to a single satellite request if the group request fails.
3. Uses local fallback TLE data if network access is unavailable.
4. Initializes up to 50 satellite objects.
5. Calculates current geocentric positions using Skyfield.

Returned satellite data includes:

```json
{
  "id": "sat-0",
  "name": "ISS (ZARYA)",
  "x": 1234.56,
  "y": 2345.67,
  "z": 3456.78,
  "time": "..."
}
```

### Boids Simulation

The simulation router provides the Boids compute stream.

The simulation configuration is represented by `SimulationConfig`:

```python
class SimulationConfig(BaseModel):
    num_particles: int = 150
    width: float = 800.0
    height: float = 600.0
    max_speed: float = 4.0
    max_force: float = 0.1
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0
```

The `BoidsEngine` uses NumPy arrays for particle positions and velocities and calculates:

- Separation
- Alignment
- Cohesion
- Velocity limiting
- Position updates
- Screen wrapping

### Maritime Mesh

The maritime service exposes the maritime computation layer.

The `MaritimeVoronoiEngine` combines:

- Live AIS position data
- Geographic-to-canvas projection
- Fallback vessel movement
- SciPy Voronoi tessellation

The current geographic bounding box is configured around the English Channel and Strait of Dover.

When fewer than four live vessels are available, the engine uses its persistent fallback vessel positions. When sufficient live AIS data is available, the live vessel positions are used for tessellation.

The resulting data contains:

```json
{
  "isLive": true,
  "vesselCount": 20,
  "bbox": [[49.8, -1.5], [51.5, 2.0]],
  "polygons": [],
  "points": []
}
```

### Chaotic Attractors

```text
WebSocket /api/ws/attractor
```

The attractor WebSocket maintains an `AttractorEngine` instance for each connected client.

Supported attractors include:

- Clifford
- De Jong
- Aizawa
- Lorenz

The engine currently generates:

- 2D trajectories for Clifford and De Jong
- 3D trajectories for Aizawa and Lorenz

The default engine point count is `50,000`.

The WebSocket accepts configuration updates such as:

```json
{
  "attractor_type": "clifford",
  "a": -1.4,
  "b": 1.6,
  "c": 1.0,
  "d": 0.7
}
```

The response is serialized as:

```json
{
  "success": true,
  "type": "clifford",
  "points": []
}
```

The attractor stream generates a new frame approximately every 16 milliseconds after each update cycle.

---

## Compute Engines

### AttractorEngine

`AttractorEngine` manages attractor configuration and trajectory generation.

Its responsibilities include:

- Selecting the attractor type
- Applying default parameters
- Detecting configuration changes
- Regenerating trajectories
- Serializing generated point data

For Aizawa and Lorenz systems, the engine uses fourth-order Runge-Kutta integration.

For Clifford and De Jong, it generates iterative 2D maps.

### BoidsEngine

`BoidsEngine` maintains NumPy arrays containing particle positions and velocities.

The engine calculates pairwise distances between particles and uses neighborhood masks to determine the forces contributing to each particle's acceleration.

### MaritimeVoronoiEngine

`MaritimeVoronoiEngine` manages both live and fallback maritime data.

Its responsibilities include:

- Connecting to the AIS stream
- Filtering position reports
- Projecting latitude/longitude coordinates to the visualization canvas
- Maintaining fallback vessel positions
- Calculating Voronoi regions
- Returning polygon, point, and vessel metadata

### Satellite Service

The satellite service uses:

- `requests` for TLE retrieval
- `Skyfield` for orbital propagation
- `NumPy` for position data handling
- `sgp4` as part of the orbital calculation dependency stack

Satellite objects are cached after initialization rather than recreated for every position request.

---

## WebSocket Flow

The service is intended to sit behind the Express WebSocket gateway.

For example:

```text
Browser / Electron
       │
       │ ws://localhost:4000/ws/attractor
       ▼
Express Gateway
       │
       │ proxy
       ▼
FastAPI
       │
       │ /api/ws/attractor
       ▼
AttractorEngine
```

The same architecture is used for the other real-time simulation streams.

The Express gateway provides the public WebSocket entry point while FastAPI performs the actual computation.

---

## Dependencies

The service currently uses:

- FastAPI
- Uvicorn
- Pydantic
- NumPy
- SciPy
- Requests
- Skyfield
- SGP4
- WebSockets

Pinned core dependencies are maintained in `requirements.txt`.

---

## Running Locally

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI service:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The service will then be available at:

```text
http://localhost:8000
```

FastAPI's interactive documentation is available at:

```text
http://localhost:8000/docs
```

---

## Configuration

The current application is configured primarily through code and the Pydantic simulation schema.

The Boids defaults are defined in `SimulationConfig`.

Satellite retrieval uses CelesTrak as its external TLE source and contains local fallback data so satellite initialization can continue when the external service is unavailable.

The maritime engine uses an external AIS WebSocket stream and currently contains its stream configuration inside the service implementation.

### Production Note

External credentials and API keys should be supplied through environment variables or another secret-management mechanism rather than committed directly to source control.

CORS is currently configured with:

```python
allow_origins=["*"]
```

This is convenient for local development but should be restricted to known application origins for a production deployment.

---

## Performance Considerations

This service performs several computationally intensive operations:

- Boids pairwise distance calculations
- 50,000-point attractor generation
- RK4 integration for 3D attractors
- SciPy Voronoi tessellation
- Satellite propagation across the cached constellation
- Continuous WebSocket serialization

The frontend therefore treats each compute feature as an independently enabled module rather than requiring every stream to start simultaneously.

This allows the application to enable only the simulation required for the current demonstration and avoids unnecessary WebSocket connections and compute workloads.

---

## Service Responsibilities

The FastAPI service is intentionally focused on computation and data processing.

It does **not** own the frontend presentation layer.

```text
Frontend
    │
    │ Visualization / Controls
    ▼
Express Gateway
    │
    │ Routing / Proxy
    ▼
FastAPI Compute Service
    │
    ├── Mathematical computation
    ├── Simulation state
    ├── External data processing
    └── Serialized results
```

This separation allows the frontend, Express gateway, and Python compute service to evolve independently while communicating through explicit HTTP and WebSocket contracts.

---

## Current Service Scope

| Feature | Transport | Compute Layer |
|---|---|---|
| Health | HTTP | FastAPI |
| Satellite telemetry | HTTP | Skyfield / SGP4 |
| Boids simulation | WebSocket | NumPy |
| Maritime mesh | HTTP / WebSocket | NumPy / SciPy / AIS |
| Chaotic attractors | WebSocket | NumPy / RK4 |

---

## Project Role

The FastAPI application is the **Python compute layer** of the Polyglot Tech Demo.

Its purpose is to demonstrate how a Python scientific-computing service can provide real-time computational workloads to a JavaScript-based application through clearly separated HTTP and WebSocket interfaces.
