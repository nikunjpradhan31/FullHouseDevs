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