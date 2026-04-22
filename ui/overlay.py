import tkinter as tk
import threading

from components.video_stream import VideoStream
from components.analytics_panel import AnalyticsPanel
from components.betting_panel import BettingPanel
from components.kafka_listener import KafkaListener
from components.game_state_client import GameStateClient

HOST = "localhost"
PORT = 9999


def main():
    root = tk.Tk()
    root.title("Blackjack Analyzer Dashboard")
    root.geometry("1400x900")

    # Layout
    video_frame = tk.Frame(root)
    video_frame.pack(side="right", padx=10, pady=10)

    analytics_frame = tk.Frame(root)
    analytics_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    # Components
    analytics_panel = AnalyticsPanel(analytics_frame)
    betting_panel = BettingPanel(analytics_frame)
    video_stream = VideoStream(video_frame, HOST, PORT)

    
    # Game state client
    game_state_client = GameStateClient(root, analytics_panel.update_game_state)
    game_state_client.start()

    # Kafka (thread-safe via root.after)
    kafka_listener = KafkaListener(root, analytics_panel.update)
    threading.Thread(target=kafka_listener.start, daemon=True).start()

    # Start video loop
    video_stream.start(root)

    root.mainloop()


if __name__ == "__main__":
    main()