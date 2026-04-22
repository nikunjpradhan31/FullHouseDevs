import threading
import time
import requests


class GameStateClient:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.url = "http://localhost:9093/game-state"
        self.running = True

    def start(self):
        threading.Thread(target=self.poll_loop, daemon=True).start()

    def poll_loop(self):
        while self.running:
            try:
                res = requests.get(self.url, timeout=0.2)
                if res.status_code == 200:
                    data = res.json()
                    self.root.after(0, self.callback, data)
            except Exception:
                pass

            time.sleep(0.5)