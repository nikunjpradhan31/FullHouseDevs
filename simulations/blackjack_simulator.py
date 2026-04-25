import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import List, Tuple
import random
from game_engine_backend.models.schemas import Card
from game_engine_backend.core.game_state_manager import RANK_VALUES, RANKS, SUITS

class BlackjackGameSimulator:
    def __init__(self, num_decks: int, min_bet: int, max_bet: int):
        self.num_decks = num_decks
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.deck = self._build_deck()
        self.reshuffled = False
        self.shuffle_deck()
        
    def _build_deck(self) -> List[Card]:
        """Build a multi-deck shoe"""
        deck = []
        for _ in range(self.num_decks):
            for suit in SUITS:
                for rank in RANKS:
                    deck.append(Card(rank=rank, suit=suit))
        return deck
    
    def shuffle_deck(self):
        """Shuffle the deck"""
        random.shuffle(self.deck)
    
    def deal_card(self) -> Card:
        """Deal a card from the deck"""
        if len(self.deck) < 52:  # Reshuffle when less than 1 deck remains
            self.deck = self._build_deck()
            self.shuffle_deck()
            self.reshuffled = True
        return self.deck.pop()
    
    def calculate_hand_value(self, hand: List[Card]) -> Tuple[int, bool]:
        """Calculate hand value and check if it's soft (contains ace counted as 11)"""
        value = 0
        aces = 0
        
        for card in hand:
            if card.rank == 'A':
                aces += 1
                value += 11
            else:
                value += RANK_VALUES[card.rank]
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        is_soft = aces > 0 and value <= 21
        return value, is_soft
    
    def should_hit(self, player_hand: List[Card], dealer_upcard: Card) -> bool:
        """Basic strategy decision for hitting"""
        player_value, is_soft = self.calculate_hand_value(player_hand)
        dealer_value = RANK_VALUES[dealer_upcard.rank]
        
        # Basic strategy rules
        if is_soft:
            # Soft hands
            if player_value >= 19:
                return False
            elif player_value == 18:
                return dealer_value in [9, 10, 11]  # 11 is Ace
            else:
                return True
        else:
            # Hard hands
            if player_value >= 17:
                return False
            elif player_value >= 13:
                return dealer_value > 6
            elif player_value == 12:
                return dealer_value < 4 or dealer_value > 6
            else:
                return True
    
    def play_player_hand(self, player_hand: List[Card], dealer_upcard: Card) -> List[Card]:
        """Play out the player's hand using basic strategy"""
        while self.should_hit(player_hand, dealer_upcard):
            player_hand.append(self.deal_card())
            player_value, _ = self.calculate_hand_value(player_hand)
            if player_value > 21:
                break  # Bust
        return player_hand
    
    def play_dealer_hand(self, dealer_hand: List[Card]) -> List[Card]:
        """Play out the dealer's hand (dealer hits on 16, stands on 17)"""
        while True:
            dealer_value, _ = self.calculate_hand_value(dealer_hand)
            if dealer_value < 17:
                dealer_hand.append(self.deal_card())
            else:
                break
        return dealer_hand
    
    def determine_winner(self, player_hand: List[Card], dealer_hand: List[Card]) -> str:
        """Determine the winner of the hand"""
        player_value, _ = self.calculate_hand_value(player_hand)
        dealer_value, _ = self.calculate_hand_value(dealer_hand)
        
        if player_value > 21:
            return "dealer"
        elif dealer_value > 21:
            return "player"
        elif player_value > dealer_value:
            return "player"
        elif dealer_value > player_value:
            return "dealer"
        else:
            return "push"
    
    def calculate_bet_amount(self, strategy, min_bet: int, max_bet: int) -> int:
        """Calculate bet amount based on strategy's true count"""
        if hasattr(strategy, 'true_count'):
            true_count = strategy.true_count
        else:
            # For strategies without true count, use running count divided by decks remaining
            decks_remaining = max(len(self.deck) / 52, 1)
            true_count = strategy.count / decks_remaining
        
        # Basic betting strategy: bet more when count is positive
        if true_count >= 2:
            bet = min_bet * (2 ** int(true_count - 1))
        elif true_count >= 1:
            bet = min_bet * 2
        else:
            bet = min_bet
        
        return min(bet, max_bet)
