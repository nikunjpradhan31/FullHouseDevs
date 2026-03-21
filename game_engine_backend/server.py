import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import (
    get_kafka_producer, close_kafka_producer,
    start_kafka_consumer, stop_kafka_consumer,
    KAFKA_TOPIC_SIM_REQUESTS
)
from models.schemas import SimulationRequest

load_dotenv()

PORT = int(os.getenv("GAME_ENG_BACKEND_PORT", 9093))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_kafka_producer()
    await start_kafka_consumer()
    yield
    # Shutdown
    await stop_kafka_consumer()
    await close_kafka_producer()

app = FastAPI(title="Game Engine Backend", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game_engine_backend"}

@app.post("/api/simulate")
async def request_simulation(payload: SimulationRequest):
    producer = await get_kafka_producer()
    await producer.send_and_wait(KAFKA_TOPIC_SIM_REQUESTS, payload.model_dump())
    return {"status": "simulation_requested", "request_id": payload.request_id}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
