import asyncio
import json
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_CARD_DETECTIONS = "card-detections"
KAFKA_TOPIC_SIM_RESULTS = "simulation-results"

async def send_dummy_messages():
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    try:
        # Dummy card detection
        dummy_detection = {
            "frame_id": 12345,
            "detections": [
                {"class": "Ace of Spades", "confidence": 0.98, "bbox": [10, 20, 50, 80]},
                {"class": "King of Hearts", "confidence": 0.95, "bbox": [100, 20, 150, 80]}
            ],
            "timestamp": "2023-10-27T10:00:00Z"
        }
        print(f"Sending dummy card detection to {KAFKA_TOPIC_CARD_DETECTIONS}...")
        await producer.send_and_wait(KAFKA_TOPIC_CARD_DETECTIONS, dummy_detection)
        print("Sent card detection successfully.")

        # Dummy simulation result
        dummy_sim_result = {
            "request_id": "req-98765",
            "win_probability": 0.45,
            "expected_value": -0.05,
            "recommended_action": "hit",
            "timestamp": "2023-10-27T10:00:05Z"
        }
        print(f"Sending dummy simulation result to {KAFKA_TOPIC_SIM_RESULTS}...")
        await producer.send_and_wait(KAFKA_TOPIC_SIM_RESULTS, dummy_sim_result)
        print("Sent simulation result successfully.")

    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(send_dummy_messages())
