import json
from kafka import KafkaConsumer


class KafkaListener:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback

        self.consumer = KafkaConsumer(
            "simulation-results",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8"))
        )

    def start(self):
        for msg in self.consumer:
            # Thread-safe UI update
            self.root.after(0, self.callback, msg.value)