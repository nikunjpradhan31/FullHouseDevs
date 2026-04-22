import tkinter as tk


class AnalyticsPanel:
    def __init__(self, parent):
        self.parent = parent

        self.title = tk.Label(parent, text="Blackjack Game Analytics", font=("Arial", 26, "bold"))
        self.title.pack(pady=10)

        self.dealer_label = tk.Label(parent, text="Dealer Upcard: ---", font=("Arial", 18))
        self.dealer_label.pack(pady=5)

        self.players_frame = tk.Frame(parent)
        self.players_frame.pack(pady=10, fill="x")

        self.player_boxes = {}

        self.recommended_move_label = tk.Label(parent, text="Recommended Move: ---", font=("Arial", 20, "bold"))
        self.recommended_move_label.pack(pady=5)

        self.ev_label = tk.Label(parent, text="Expected Value: ---", font=("Arial", 18))
        self.ev_label.pack(pady=5)

    def update_game_state(self, data):
        game_state = data.get("game_state")
        if not game_state:
            return

        player_cards = game_state["player_hand"]["cards"]
        dealer_cards = game_state["dealer_hand"]["cards"]

        # Format nicely
        player_str = [f"{c['rank']} of {c['suit']}" for c in player_cards]
        dealer_str = [f"{c['rank']} of {c['suit']}" for c in dealer_cards]

        if 1 not in self.player_boxes:
            self._create_player_box(1)

        box = self.player_boxes[1]

        box["cards"].config(text=f"Cards: {player_str}")

        self.dealer_label.config(text=f"Dealer: {dealer_str}")

    def update(self, data):
        # Dealer
        if "dealer_up_card" in data:
            self.dealer_label.config(text=f"Dealer Upcard: {data['dealer_up_card']}")

        # Always single player (matches your backend)
        if 1 not in self.player_boxes:
            self._create_player_box(1)

        box = self.player_boxes[1]

        box["cards"].config(text=f"Cards: {data.get('player_hand', [])}")
        box["count"].config(text=f"Hand Value: {data.get('player_hand_value', '---')}")
        box["ev"].config(text=f"EV: {data.get('optimal_ev', '---')}")
        box["optimal_action"].config(text=f"Optimal Action: {data.get('optimal_action', '---')}")

    def _create_player_box(self, i):
        box = tk.LabelFrame(self.players_frame, text=f"Player {i}", padx=10, pady=10)
        box.pack(fill="x", pady=5)

        cards = tk.Label(box, text="Cards: ---", font=("Arial", 14))
        cards.pack(anchor="w")

        count = tk.Label(box, text="Hand Value: ---", font=("Arial", 14))
        count.pack(anchor="w")

        ev = tk.Label(box, text="EV: ---", font=("Arial", 14))
        ev.pack(anchor="w")

        action = tk.Label(box, text="Optimal Action: ---", font=("Arial", 14))
        action.pack(anchor="w")

        self.player_boxes[i] = {
            "cards": cards,
            "count": count,
            "ev": ev,
            "optimal_action": action
        }