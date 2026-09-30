from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.routers import health, maritime, satellites, simulation, attractors
from app.routers.maritime import engine as maritime_engine  # Or however your maritime router references the engine instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safely trigger the background AIS stream task once the event loop is running
    asyncio.create_task(maritime_engine.connect_live_ais_stream())
    yield

app = FastAPI(title="Polyglot Tech Demo Compute Service", version="1.0.0", lifespan=lifespan)

# Add CORS middleware to allow local desktop requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(satellites.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(maritime.router, prefix="/api")
app.include_router(attractors.router, prefix="/api")