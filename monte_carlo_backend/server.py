import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import (
    get_kafka_producer, close_kafka_producer,
    start_kafka_consumer, stop_kafka_consumer
)

load_dotenv()

PORT = int(os.getenv("MONTE_CARLO_PORT", 9095))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_kafka_producer()
    await start_kafka_consumer()
    yield
    # Shutdown
    await stop_kafka_consumer()
    await close_kafka_producer()

app = FastAPI(title="Monte Carlo Backend", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "monte_carlo_backend"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
