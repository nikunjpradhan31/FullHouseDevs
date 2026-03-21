import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import get_kafka_producer, close_kafka_producer, KAFKA_TOPIC_CARD_DETECTIONS
from models.schemas import CardDetectionPayload

load_dotenv()

PORT = int(os.getenv("CV_BACKEND_PORT", 9094))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_kafka_producer()
    yield
    # Shutdown
    await close_kafka_producer()

app = FastAPI(title="Vision Backend", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "cv_backend"}

@app.post("/api/detections")
async def publish_detections(payload: CardDetectionPayload):
    producer = await get_kafka_producer()
    await producer.send_and_wait(KAFKA_TOPIC_CARD_DETECTIONS, payload.model_dump())
    return {"status": "published", "topic": KAFKA_TOPIC_CARD_DETECTIONS}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
