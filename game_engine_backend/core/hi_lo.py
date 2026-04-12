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

NUM_DECKS = 2

# Tracks the Hi-Lo running and true count from live card detections to identify potential card counters
class HiLoTracker:
    def __init__(self):
        self.running_count = 0
        self.cards_seen = 0
        self.bet_history = []
        self.min_bet = 25 # Assuming player is betting with $25 chips

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
    
    # Called on shuffle - resets count for new shoe
    def reset(self):
        self.running_count = 0
        self.cards_seen = 0
        self.bet_history = []

    # Keep track of a player's bets over multiple hands to identify a potential card counter
    def record_bet(self, bet_amount):
        self.bet_history.append((self.true_count, bet_amount))

    # Checks if player's bets match the Hi-Lo betting formula (true_count - 1) * min_bet
    # First checks bet spread ratio — real counters spread at least 1:4 (e.g. $25 to $100+)
    # Then checks if 7 out of 8 rounds match the expected bet within one chip ($25)
    def is_counting(self):
        if len(self.bet_history) < 8:
            return False
        matches = 0
        recent = self.bet_history[-8:]

        min_bet_seen = min(bet for _, bet in recent)
        max_bet_seen = max(bet for _, bet in recent)
        spread_ratio = max_bet_seen / min_bet_seen if min_bet_seen > 0 else 1
        if spread_ratio < 4:
            return False
        
        for true_count, bet_amount in recent:
            expected_bet = (true_count - 1) * self.min_bet
            if abs(bet_amount - expected_bet) <= self.min_bet:
                matches += 1
        return matches >= 7

    # Returns current Hi-Lo state for the /hi-lo API endpoint
    def get_state(self):
        return {
            "running_count": self.running_count,
            "true_count": round(self.true_count, 2),
            "cards_seen": self.cards_seen,
            "decks_remaining": round(self._decks_remaining(), 2),
            "bet_history": self.bet_history,
            "is_counting": self.is_counting()
        }

# Global instance shared across kafka.py and server.py  
hi_lo_tracker = HiLoTracker()
