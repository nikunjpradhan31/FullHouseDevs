''' 
Counting Strategies:
    Red Seven Count
    Revere Point Count
    Omega II Count
    K-O Count
    KISS 3 Count
    Hi-Lo Count
'''

NUM_DECKS = 6

class RedSevenCount:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        elif card.rank == '7' and card.suit in ['hearts', 'diamonds']:
            self.count += 1

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class ReverePointCount:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        elif card.rank == '7':
            self.count += 0.5

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class OmegaIICount:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        elif card.rank == '7':
            self.count += 0.5
        elif card.rank == '8':
            self.count += 0.5

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class KOCount:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        # No adjustment for 7, 8, 9

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class KISS3Count:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        elif card.rank == '7':
            self.count += 0.5
        elif card.rank == '8':
            self.count += 0.5
        elif card.rank == '9':
            self.count += 0.5

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class HiLoCount:
    def __init__(self):
        self.count = 0
        self.cards_seen = 0

    def reset(self):
        self.count = 0
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1
        if card.rank in ['2', '3', '4', '5', '6']:
            self.count += 1
        elif card.rank in ['10', 'J', 'Q', 'K', 'A']:
            self.count -= 1
        # No adjustment for 7, 8, 9

    @property
    def true_count(self):
        decks_remaining = max((NUM_DECKS * 52 - self.cards_seen) / 52, 0.5)
        return self.count / decks_remaining

class BasePlayer:
    def __init__(self):
        self.cards_seen = 0

    def reset(self):
        self.cards_seen = 0

    def update(self, card):
        self.cards_seen += 1

    @property
    def true_count(self):
        return 0

    def get_bet(self, min_bet, max_bet):
            """Always bets the minimum."""
            return min_bet

class NormalPlayer(BasePlayer):
    def __init__(self):
        super().__init__()
        self.last_result = None
        self.current_bet = 10

    def update_result(self, result: str):
        self.last_result = result

    def reset(self):
        super().reset()
        self.last_result = None
        self.current_bet = 10

    def get_bet(self, min_bet, max_bet):
        """
        Increase bet by 50% after a win, reset after a loss.
        """
        if self.last_result == "player":
            self.current_bet = min(self.current_bet * 1.5, max_bet)
        elif self.last_result == "dealer":
            self.current_bet = min_bet
        return self.current_bet
