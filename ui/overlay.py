import socket
import struct
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
import threading
import json
from kafka import KafkaConsumer

# -----------------------------
# Webcam connection
# -----------------------------

HOST = "localhost"
PORT = 9999

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
print("Connected to webcam server")

# -----------------------------
# Kafka consumer
# -----------------------------

consumer = KafkaConsumer(
    "simulation-results",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="latest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)

# -----------------------------
# GUI setup
# -----------------------------

root = tk.Tk()
root.title("Blackjack Analyzer Dashboard")
root.geometry("1400x900")

# Layout frames
video_frame = tk.Frame(root)
video_frame.pack(side="right", padx=10, pady=10)

analytics_frame = tk.Frame(root)
analytics_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

# -----------------------------
# Webcam display
# -----------------------------

video_label = tk.Label(video_frame)
video_label.pack()

WEBCAM_WIDTH = 960 # slightly smaller but proportional
WEBCAM_HEIGHT = 540

def update_frame():
    length_bytes = s.recv(4)
    if not length_bytes:
        root.after(10, update_frame)
        return

    length = struct.unpack("!I", length_bytes)[0]

    data = b""
    while len(data) < length:
        packet = s.recv(length - len(data))
        if not packet:
            break
        data += packet

    if data:
        nparr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # resize for smaller display
        frame = cv2.resize(frame, (WEBCAM_WIDTH, WEBCAM_HEIGHT))

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(img)

        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)

    root.after(30, update_frame)

# -----------------------------
# Analytics display
# -----------------------------

title = tk.Label(
    analytics_frame,
    text="Blackjack Game Analytics",
    font=("Arial", 26, "bold")
)
title.pack(pady=10)

# Dealer section
dealer_label = tk.Label(
    analytics_frame,
    text="Dealer Upcard: ---",
    font=("Arial", 18)
)
dealer_label.pack(pady=5)

# Players container
players_frame = tk.Frame(analytics_frame)
players_frame.pack(pady=10, fill="x")

player_boxes = {}  # dictionary to hold each player GUI frame

# -----------------------------
# Recommendation section
# -----------------------------

recommendation_frame = tk.Frame(analytics_frame)
recommendation_frame.pack(pady=30)

recommended_move_label = tk.Label(
    recommendation_frame,
    text="Recommended Move: ---",
    font=("Arial", 20, "bold")
)
recommended_move_label.pack(pady=5)

ev_label = tk.Label(
    recommendation_frame,
    text="Expected Value: ---",
    font=("Arial", 18)
)
ev_label.pack(pady=5)

# -----------------------------
# Kafka listener thread
# -----------------------------

def kafka_listener():
    for message in consumer:
        data = message.value
        print("Kafka message received:", data)
        root.after(0, update_analytics, data)

# -----------------------------
# Update GUI from Kafka data
# -----------------------------

def update_analytics(data):

    # Dealer
    if "dealer_up_card" in data:
        dealer_label.config(text=f"Dealer Upcard: {data['dealer_up_card']}")

    # Ensure at least one player
    players = data.get("players", [data])  # fallback to single if not in list

    for i, player_data in enumerate(players, start=1):
        if i not in player_boxes:
            # Create a new player box
            box = tk.LabelFrame(players_frame, text=f"Player {i}", padx=10, pady=10)
            box.pack(fill="x", pady=5)

            cards_label = tk.Label(box, text="Cards: ---", font=("Arial", 14))
            cards_label.pack(anchor="w")

            count_label = tk.Label(box, text="Count: ---", font=("Arial", 14))
            count_label.pack(anchor="w")

            ev_label_box = tk.Label(box, text="EV: ---", font=("Arial", 14))
            ev_label_box.pack(anchor="w")

            optimal_action_label = tk.Label(box, text="Optimal Action: ---", font=("Arial", 14))
            optimal_action_label.pack(anchor="w")

            # store for updating
            player_boxes[i] = {
                "cards": cards_label,
                "count": count_label,
                "ev": ev_label_box,
                "optimal_action": optimal_action_label
            }

        # Update labels
        box_data = player_boxes[i]
        box_data["cards"].config(text=f"Cards: {player_data.get('player_hand', [])}")
        box_data["count"].config(text=f"Hand Value: {player_data.get('player_hand_value', '---')}")
        box_data["ev"].config(text=f"EV: {player_data.get('optimal_ev', '---')}")
        box_data["optimal_action"].config(text=f"Optimal Action: {player_data.get('optimal_action', '---')}")

    # Update recommendation
    if "recommended_move" in data:
        recommended_move_label.config(text=f"Recommended Move: {data['recommended_move']}")
    if "expected_value" in data:
        ev_label.config(text=f"Expected Value: {data['expected_value']}")

# -----------------------------
# Start threads
# -----------------------------

threading.Thread(target=kafka_listener, daemon=True).start()
update_frame()
root.mainloop()