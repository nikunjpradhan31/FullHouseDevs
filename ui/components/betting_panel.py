import tkinter as tk
import requests


class BettingPanel:
    def __init__(self, parent):
        frame = tk.Frame(parent)
        frame.pack(pady=20)

        tk.Label(frame, text="Place Bet", font=("Arial", 18, "bold")).pack()

        self.entry = tk.Entry(frame, font=("Arial", 14))
        self.entry.pack(pady=5)

        self.status = tk.Label(frame, text="Status: ---", font=("Arial", 14))
        self.status.pack(pady=5)

        tk.Button(frame, text="Submit Bet", font=("Arial", 14), command=self.submit_bet).pack(pady=5)

        # --- GAME CONTROL BUTTONS ---

        tk.Button(frame, text="Shuffle", font=("Arial", 14), command=self.shuffle).pack(pady=5)

        tk.Button(frame, text="Initial Deal", font=("Arial", 14), command=self.initial_deal).pack(pady=5)

        tk.Button(frame, text="Player Turn", font=("Arial", 14), command=self.player_turn).pack(pady=5)

        tk.Button(frame, text="End Round", font=("Arial", 14), command=self.end_round).pack(pady=5)

    def submit_bet(self):
        try:
            amount = float(self.entry.get())

            res = requests.post(
                "http://localhost:9093/bet",
                json={"amount": amount}
            )

            if res.status_code == 200:
                data = res.json()
                self.status.config(text=f"Recorded | True Count: {data['true_count']}")
            else:
                self.status.config(text="Error submitting bet")

        except ValueError:
            self.status.config(text="Invalid bet amount")
        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")

    # --- NEW BUTTON ACTIONS ---

    def shuffle(self):
        try:
            res = requests.post("http://localhost:9093/shuffle")

            if res.status_code == 200:
                data = res.json()
                self.status.config(text=f"Shuffled | Phase: {data.get('phase')}")
            else:
                self.status.config(text="Shuffle failed")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")

    def initial_deal(self):
        try:
            res = requests.post("http://localhost:9093/initial-deal")

            if res.status_code == 200:
                data = res.json()
                self.status.config(text=f"Initial Deal | Phase: {data.get('phase')}")
            else:
                self.status.config(text="Initial deal failed")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")

    def player_turn(self):
        try:
            res = requests.post("http://localhost:9093/player-turn")

            if res.status_code == 200:
                data = res.json()
                self.status.config(text=f"Player Turn | Phase: {data.get('phase')}")
            else:
                self.status.config(text="Player turn failed")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")

    def end_round(self):
        try:
            res = requests.post("http://localhost:9093/round-complete")

            if res.status_code == 200:
                data = res.json()
                self.status.config(text=f"Round Complete | Phase: {data.get('phase')}")
            else:
                self.status.config(text="Error ending round")

        except Exception as e:
            self.status.config(text=f"Error: {str(e)}")