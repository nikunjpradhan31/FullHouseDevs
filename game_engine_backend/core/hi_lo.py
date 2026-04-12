from models.schemas import Card
from core.game_state_manager import game_state_manager

# Hi-Lo weights: low cards (2-6) are counted as +1, high cards (10-A) as -1, neutral (7-9) as 0
# As low cards are seen and removed, running count rises — more high cards remain, favoring the player
# As high cards are seen and removed, running count falls — fewer high cards remain, favoring the dealer
WEIGHT_DICT = {
    "10": -1, "J": -1, "Q": -1, "K": -1, "A": -1,
    "2": +1, "3": +1, "4": +1, "5": +1, "6": +1,
    "7": 0, "8": 0, "9": 0
}

# TODO: incorporate bet amounts when bet API is implemented for actual card counter detection
ALERT_THRESHOLD = 2 # True count above this means the deck favors the player / flag security to watch table
NUM_DECKS = 2

# Tracks the Hi-Lo running and true count from live card detections to identify potential card counters
class HiLoTracker:
    def __init__(self):
        self.running_count = 0
        self.cards_seen = 0

    # Called every time a card is detected, regardless of whether it's the dealer's or player's
    def update(self, card: Card):
        self.running_count += WEIGHT_DICT.get(card.rank, 0)
        self.cards_seen += 1
    
    # Uses the game state deck for accuracy, falls back to cards_seen estimate if not yet initialized
    def _decks_remaining(self):
        if game_state_manager.game_state is not None:
            return max(len(game_state_manager.game_state.deck) / 52, 0.5)
        else:
            return max(((NUM_DECKS * 52) - self.cards_seen) / 52, 0.5)

    # Normalizes running count by decks remaining so the count is comparable at any point in the shoe
    @property
    def true_count(self):
        return self.running_count / self._decks_remaining()
    
    # True when deck is statistically favorable for the player
    # Alerts security to watch table - see if true count continues to go up
    # If so, see if anyone is raising their bets as true count increases
    @property
    def alert(self):
        return self.true_count > ALERT_THRESHOLD
    
    # Called on shuffle - resets count for new shoe
    def reset(self):
        self.running_count = 0
        self.cards_seen = 0

    # Global instance shared across kafka.py and server.py
    def get_state(self):
        return {
            "running_count": self.running_count,
            "true_count": round(self.true_count),
            "cards_seen": self.cards_seen,
            "decks_remaining": round(self._decks_remaining()),
            "alert": self.alert
        }
    
hi_lo_tracker = HiLoTracker()
