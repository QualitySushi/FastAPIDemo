from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, satellites, simulation

app = FastAPI(title="Polyglot Tech Demo Compute Service", version="1.0.0")

# Add CORS middleware to allow local desktop requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify ["file://", "http://localhost:8000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(satellites.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")