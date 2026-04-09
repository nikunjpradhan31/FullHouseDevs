import os
import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import (
    start_kafka_consumer, stop_kafka_consumer,
)
load_dotenv()



PORT = int(os.getenv("GAME_ENG_BACKEND_PORT", 9093))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await start_kafka_consumer()
    yield
    # Shutdown
    #task.cancel()
    await stop_kafka_consumer()

app = FastAPI(title="Game Engine Backend", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game_engine_backend"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
