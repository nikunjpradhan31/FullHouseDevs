# cv_backend/core/kafka.py
import json
import os
import time
import asyncio
import threading
from queue import Queue
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_CARD_DETECTIONS = "card-detections"

# Message queue for thread-safe sending
_message_queue = Queue()
_producer = None
_server_producer = None
_loop = None
_thread = None

def _start_kafka_thread():
    """Start background thread with its own event loop"""
    global _loop, _thread
    
    def run():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_init_producer())
        _loop.run_forever()
    
    _thread = threading.Thread(target=run, daemon=True)
    _thread.start()

async def _init_producer():
    """Initialize Kafka producer"""
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await _producer.start()
    print("[KAFKA] Producer connected")
    
    # Start processing queue
    asyncio.create_task(_process_queue())

async def _process_queue():
    """Process messages from queue and send to Kafka"""
    global _message_queue
    while True:
        try:
            # Get message from queue (now with 3 items)
            label, zone, timestamp = await asyncio.get_event_loop().run_in_executor(
                None, _message_queue.get
            )
            
            # Parse label
            if len(label) >= 3 and label[0:2].isdigit():
                rank = label[:2]
                suit_code = label[2]
            else:
                rank = label[0]
                suit_code = label[1]
            
            suit_map = {'h': 'Hearts', 'd': 'Diamonds', 'c': 'Clubs', 's': 'Spades'}
            suit = suit_map.get(suit_code.lower(), 'Unknown')
            
            message = {
                "rank": rank,
                "suit": suit,
                "zone": zone,
                "timestamp": timestamp,  # Use the capture time from detector
                "raw_label": label
            }
            
            await _producer.send_and_wait(KAFKA_TOPIC_CARD_DETECTIONS, message)
            print(f"[KAFKA] Sent: {rank} of {suit} -> {zone} at {timestamp}")
            
        except Exception as e:
            print(f"[KAFKA ERROR] {e}")

def send_card_detection(label: str, zone: str, timestamp: float):
    """
    Send card detection to Kafka.
    Called from detector.py - synchronous and non-blocking.
    
    Args:
        label: YOLO label like "Ah", "10s"
        zone: "dealer", "player_1", etc.
        timestamp: Time when card was captured (from time.time())
    """
    global _message_queue, _thread
    
    # Start background thread if not running
    if _thread is None or not _thread.is_alive():
        _start_kafka_thread()
    
    # Add to queue with timestamp
    _message_queue.put((label, zone, timestamp))

async def get_kafka_producer():
    global _server_producer
    if _server_producer is None:
        _server_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await _server_producer.start()
    return _server_producer

async def close_kafka_producer():
    global _server_producer
    if _server_producer is not None:
        await _server_producer.stop()
