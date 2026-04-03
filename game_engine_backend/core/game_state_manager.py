from typing import Optional, List
from models.schemas import GameState, Hand, Card

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
NUM_DECKS = 2

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

def build_default_deck() -> List[int]:
    return [
        RANK_VALUES[rank]
        for _ in range(NUM_DECKS)
        for _ in SUITS
        for rank in RANKS
    ]


class GameStateManager:
    def __init__(self):
        self.game_state: Optional[GameState] = None

    def update_card(self, card: Card, location: str):
        current_deck = self.game_state.deck if self.game_state else build_default_deck()

        # Remove card value from deck
        card_value = RANK_VALUES[card.rank]
        if card_value in current_deck:
            current_deck.remove(card_value)

        if location == "player":
            updated_cards = (self.game_state.player_hand.cards if self.game_state else []) + [card]
            player_hand = Hand(
                cards=updated_cards,
                value=self._calculate_hand_value(updated_cards),
                is_soft=self._is_soft(updated_cards)
            )
            dealer_upcard = self.game_state.dealer_upcard if self.game_state else None
        elif location == "dealer":
            player_hand = self.game_state.player_hand if self.game_state else Hand(cards=[], value=0, is_soft=False)
            dealer_upcard = card

        self.game_state = GameState(
            player_hand=player_hand,
            dealer_upcard=dealer_upcard,
            deck=current_deck
        )

    def shuffle(self):
        """On Shuffle reset the whole game state"""
        self.game_state = None

    def round_clear(self):
        """This should be used at the end of a round"""
        if self.game_state is None:
            return
        self.game_state = GameState(
            player_hand=Hand(cards=[], value=0, is_soft=False),
            dealer_upcard=None,
            deck=self.game_state.deck
        )

    def _calculate_hand_value(self, cards: List[Card]) -> int:
        value = 0
        aces = 0
        for card in cards:
            if card.rank in ["J", "Q", "K"]:
                value += 10
            elif card.rank == "A":
                aces += 1
                value += 11
            else:
                value += int(card.rank)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    def _is_soft(self, cards: List[Card]) -> bool:
        value = 0
        aces = 0
        for card in cards:
            if card.rank in ["J", "Q", "K"]:
                value += 10
            elif card.rank == "A":
                aces += 1
                value += 11
            else:
                value += int(card.rank)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return aces > 0


game_state_manager = GameStateManager()