import json
import os
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_CARD_DETECTIONS = "card-detections"

consumer_task = None

# async def get_kafka_producer():
#     global producer
#     if producer is None:
#         producer = AIOKafkaProducer(
#             bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#             value_serializer=lambda v: json.dumps(v).encode('utf-8')
#         )
#         await producer.start()
#     return producer

# async def close_kafka_producer():
#     global producer
#     if producer is not None:
#         await producer.stop()

async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC_CARD_DETECTIONS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="game-engine-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        request_timeout_ms=5000,
        retry_backoff_ms=500

    )
    await consumer.start()
    try:
        async for msg in consumer:
            topic = msg.topic
            data = msg.value
            if topic == KAFKA_TOPIC_CARD_DETECTIONS:
                print(f"Received card detection: {data}")
                # Process detection and potentially trigger simulation request

    finally:
        await consumer.stop()

async def start_kafka_consumer():
    global consumer_task
    consumer_task = asyncio.create_task(consume_messages())

async def stop_kafka_consumer():
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
