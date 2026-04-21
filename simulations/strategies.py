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