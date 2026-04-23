import json
import asyncio
from aiokafka import AIOKafkaConsumer


class KafkaListener:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.loop = asyncio.new_event_loop()

    async def _consume(self):
        consumer = AIOKafkaConsumer(
            "simulation-results",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8"))
        )

        await consumer.start()
        try:
            async for msg in consumer:
                data = msg.value
                self.root.after(0, self.callback, data)
        finally:
            await consumer.stop()

    def start(self):
        print("KafkaListener started...")
        self.loop.run_until_complete(self._consume())