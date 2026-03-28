import json
import os
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_SIM_REQUESTS = "simulation-requests"
KAFKA_TOPIC_SIM_RESULTS = "simulation-results"

producer = None
consumer_task = None

async def get_kafka_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await producer.start()
    return producer

async def close_kafka_producer():
    global producer
    if producer is not None:
        await producer.stop()

async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC_SIM_REQUESTS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="monte-carlo-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        retry_backoff_ms=500, 
        reconnect_backoff_ms=1000
    )
    await consumer.start()
    try:
        async for msg in consumer:
            data = msg.value
            print(f"Received simulation request: {data}")
            # Process simulation request
            # ... run monte carlo simulation ...
            # Mock result
            result = {
                "request_id": data.get("request_id"),
                "win_probability": 0.42,
                "loss_probability": 0.49,
                "push_probability": 0.09,
                "recommended_action": "hit"
            }
            
            prod = await get_kafka_producer()
            await prod.send_and_wait(KAFKA_TOPIC_SIM_RESULTS, result)
            print(f"Sent simulation result for request: {data.get('request_id')}")
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
