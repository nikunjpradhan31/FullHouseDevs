import os
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import get_kafka_producer, close_kafka_producer, KAFKA_TOPIC_CARD_DETECTIONS
from models.schemas import CardDetectionPayload, CardDetection, Coordinate

load_dotenv()

# async def produce_dummy_detections():
#     while True:
#         try:
#             producer = await get_kafka_producer()
#             dummy_payload = CardDetectionPayload(
#                 frame_id="dummy_frame_1",
#                 timestamp=time.time(),
#                 detections=[
#                     CardDetection(
#                         rank="A",
#                         suit="Spades",
#                         confidence=0.99,
#                         box=Coordinate(x=10.0, y=20.0, w=50.0, h=80.0)
#                     )
#                 ]
#             )
#             await producer.send_and_wait(KAFKA_TOPIC_CARD_DETECTIONS, dummy_payload.model_dump())
#             print(f"Sent dummy card detection: {dummy_payload.model_dump()}")
#         except Exception as e:
#             print(f"Error sending dummy detection: {e}")
#         await asyncio.sleep(5)

PORT = int(os.getenv("CV_BACKEND_PORT", 9094))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await get_kafka_producer()
    #task = asyncio.create_task(produce_dummy_detections())
    yield
    # Shutdown
    #task.cancel()
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
