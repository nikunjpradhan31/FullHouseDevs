from models.schemas import Card
from core.game_state_manager import game_state_manager

WEIGHT_DICT = {
    "10": -1, "J": -1, "Q": -1, "K": -1, "A": -1,
    "2": +1, "3": +1, "4": +1, "5": +1, "6": +1,
    "7": 0, "8": 0, "9": 0
}

# TODO: incorporate bet amounts when bet API is implemented for actual card counter detection
ALERT_THRESHOLD = 3
NUM_DECKS = 2

class HiLoTracker:
    def __init__(self):
        self.running_count = 0
        self.cards_seen = 0

    def update(self, card: Card):
        self.running_count += WEIGHT_DICT.get(card.rank, 0)
        self.cards_seen += 1
    
    def _decks_remaining(self):
        if game_state_manager.game_state is not None:
            return max(len(game_state_manager.game_state.deck) / 52, 0.5)
        else:
            return max(((NUM_DECKS * 52) - self.cards_seen) / 52, 0.5)

    @property
    def true_count(self):
        return self.running_count / self._decks_remaining()
    
    @property
    def alert(self):
        return self.true_count > ALERT_THRESHOLD
    
    def reset(self):
        self.running_count = 0
        self.cards_seen = 0

    def get_state(self):
        return {
            "running_count": self.running_count,
            "true_count": round(self.true_count),
            "cards_seen": self.cards_seen,
            "decks_remaining": round(self._decks_remaining()),
            "alert": self.alert
        }
    
hi_lo_tracker = HiLoTracker()
