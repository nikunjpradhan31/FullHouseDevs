from typing import Optional, List, Dict, Any
from game_engine_backend.models.schemas import GameState, Hand, Card
from enum import Enum
from game_engine_backend.monte_carlo.blackjackSim import BlackjackSimulator

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
NUM_DECKS = 2

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}

''' Dealer Flow:
on_dealer_turn() → transition_to(DEALER_TURN)
    ↓
execute_dealer_turn() → evaluate hand
    ↓
Return: "hit" | "stand" | "bust"
    ↓
If "stand"/"bust" → on_round_complete()
    ↓
If "hit" → wait for next dealer card
'''

''' Player Flow:
1. Player receives initial cards → Simulation runs → Display recommendation
2. Player hits → New card detected → Hand updates → New simulation → Updated recommendation
3. Player stands → Transition to DEALER_TURN
4. Player doubles → Double bet → One card → Final simulation → Transition to DEALER_TURN
5. Player splits → Create two hands → Separate simulations for each → Play each hand
'''

class GamePhase(Enum):
    IDLE = "idle"
    SHUFFLING = "shuffling"
    INITIAL_DEAL = "initial_deal"
    PLAYER_TURN = "player_turn"
    DEALER_TURN = "dealer_turn"
    ROUND_COMPLETE = "round_complete"

def build_default_deck() -> List[int]:
    """
    Creates a standard blackjack deck with the specified number of decks.

    Returns:
        List[int]: A list containing card values (2-11) representing a full deck.
                    Each card value appears NUM_DECKS * 4 times (once per suit).
                    Face cards (J, Q, K) are represented as 10, Aces as 11.
    """
    return [
        RANK_VALUES[rank]
        for _ in range(NUM_DECKS)
        for _ in SUITS
        for rank in RANKS
    ]


class GameStateManager:
    def __init__(self):
        self.current_phase = GamePhase.IDLE
        self.game_state: Optional[GameState] = None
        self.monte_carlo = BlackjackSimulator()
        self.monte_carlo_result: Optional[Dict[str, Any]] = None

    def update_card(self, card: Card, location: str) -> bool:
        """
        Add a detected card to the game state and remove it from the deck.

        This method is called when the CV pipeline detects a new card on the table.
        It updates the appropriate hand (player or dealer), removes the card from
        the remaining deck, and determines if a simulation should be triggered.

        Args:
            card (Card): The detected card with rank and suit.
            location (str): Where the card was placed ("player" or "dealer").

        Returns:
            bool: True if the player hand changed (should trigger simulation),
                    False otherwise. Dealer card changes never trigger simulation.

        Note:
            - Cards are removed from deck by value only (not by exact rank/suit)
            - If the card value isn't found in deck, a warning is logged
            - Player hand changes during PLAYER_TURN phase trigger simulations
            - Dealer cards are added to the dealer hand
        """
        # Initialize deck if not exists
        current_deck = self.game_state.deck if self.game_state else build_default_deck()

        # Remove card by rank & suit
        card_value = RANK_VALUES[card.rank]
        if card_value in current_deck:
            current_deck.remove(card_value)
        else:
            print(f"Warning: Card {card.rank} of {card.suit} not found in deck")

        hand_changed = False

        if location == "player":
            old_hand = self.game_state.player_hand if self.game_state else None
            updated_cards = (self.game_state.player_hand.cards if self.game_state else []) + [card]
            player_hand = Hand(
                cards=updated_cards,
                value=self._calculate_hand_value(updated_cards),
                is_soft=self._is_soft(updated_cards)
            )
            dealer_hand = self.game_state.dealer_hand if self.game_state else Hand(cards=[], value=0, is_soft=False)

            # Check if hand actually changed
            if old_hand is None or len(old_hand.cards) != len(updated_cards):
                hand_changed = True

        elif location == "dealer":
            player_hand = self.game_state.player_hand if self.game_state else Hand(cards=[], value=0, is_soft=False)
            updated_dealer_cards = (self.game_state.dealer_hand.cards if self.game_state else []) + [card]
            dealer_hand = Hand(
                cards=updated_dealer_cards,
                value=self._calculate_hand_value(updated_dealer_cards),
                is_soft=self._is_soft(updated_dealer_cards)
            )
            # Dealer card changes don't trigger simulation
            hand_changed = False

        self.game_state = GameState(
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            deck=current_deck
        )

        if hand_changed and self.current_phase == GamePhase.PLAYER_TURN:
            self._run_monte_carlo_simulation()

        return hand_changed

    def get_current_phase(self) -> GamePhase:
        """
        Get the current phase of the blackjack game.

        Returns:
            GamePhase: The current game phase (IDLE, SHUFFLING, INITIAL_DEAL,
                        PLAYER_TURN, DEALER_TURN, or ROUND_COMPLETE).
        """
        return self.current_phase

    def transition_to(self, new_phase: GamePhase) -> bool:
        """
        Attempt to transition the game to a new phase.

        Validates that the transition is allowed based on the current phase
        and the defined state machine rules. Only specific transitions are
        permitted to maintain game flow integrity.

        Args:
            new_phase (GamePhase): The target phase to transition to.

        Returns:
            bool: True if the transition was successful, False if invalid.

        Valid transitions:
        - IDLE → SHUFFLING
        - SHUFFLING → INITIAL_DEAL
        - INITIAL_DEAL → PLAYER_TURN
        - PLAYER_TURN → DEALER_TURN or ROUND_COMPLETE
        - DEALER_TURN → ROUND_COMPLETE
        - ROUND_COMPLETE → IDLE or SHUFFLING
        """
        valid_transitions = {
            GamePhase.IDLE: [GamePhase.SHUFFLING],
            GamePhase.SHUFFLING: [GamePhase.INITIAL_DEAL],
            GamePhase.INITIAL_DEAL: [GamePhase.PLAYER_TURN],
            GamePhase.PLAYER_TURN: [GamePhase.DEALER_TURN, GamePhase.ROUND_COMPLETE],
            GamePhase.DEALER_TURN: [GamePhase.ROUND_COMPLETE],
            GamePhase.ROUND_COMPLETE: [GamePhase.IDLE, GamePhase.SHUFFLING]
        }

        if new_phase in valid_transitions.get(self.current_phase, []):
            self.current_phase = new_phase
            print(f"Game phase transitioned: {self.current_phase.value}")
            return True
        else:
            print(f"Invalid transition from {self.current_phase.value} to {new_phase.value}")
            return False

    def on_shuffle(self):
        """
        Handle a shuffle event detected from the CV pipeline.

        Resets the game state to None (clearing all hands and deck tracking)
        and transitions the game phase to SHUFFLING. This prepares the game
        for a new round with a fresh deck.
        """
        self.game_state = None
        self.transition_to(GamePhase.SHUFFLING)

    def on_initial_deal(self):
        """
        Transition to the initial deal phase.

        Called when the dealer begins dealing the first two cards to player
        and dealer. This phase represents the start of a new hand.
        """
        self.transition_to(GamePhase.INITIAL_DEAL)
        if self.game_state and len(self.game_state.player_hand.cards) == 2 and len(self.game_state.dealer_hand.cards) >= 1:
            self._run_monte_carlo_simulation()

    def on_player_turn(self):
        """
        Transition to the player turn phase.

        Called when it's the player's turn to make decisions (hit, stand,
        double, split). During this phase, card additions to the player hand
        will trigger Monte Carlo simulations.
        """
        self.transition_to(GamePhase.PLAYER_TURN)
        if self.game_state and len(self.game_state.player_hand.cards) >= 2:
            self._run_monte_carlo_simulation()

    def on_dealer_turn(self):
        """
        Transition to the dealer turn phase and execute dealer logic.

        Called when the player has finished their turn and the dealer must
        play according to house rules (hit on 16, stand on 17).

        This method transitions to DEALER_TURN phase and immediately evaluates
        the dealer's hand to determine if they should hit, stand, or if busted.
        """
        success = self.transition_to(GamePhase.DEALER_TURN)
        if success:
            # Execute dealer logic immediately
            dealer_action = self.execute_dealer_turn()
            if dealer_action in ["stand", "bust"]:
                # Dealer is done, move to round complete
                print(f"Dealer {dealer_action}s - round complete")
                self.on_round_complete()

    def on_round_complete(self):
        """
        Transition to the round complete phase.

        Called when the current hand is finished (player bust, dealer bust,
        or final comparison). The game is ready for the next hand or shuffle.
        """
        self.transition_to(GamePhase.ROUND_COMPLETE)

    def round_clear(self):
        """
        Clear the current round and prepare for the next hand.

        Resets both player and dealer hands to empty while preserving the current deck
        (cards already dealt remain out). Transitions to ROUND_COMPLETE phase.

        This should be called at the end of each hand to prepare for the next round.
        """
        if self.game_state is None:
            return
        self.game_state = GameState(
            player_hand=Hand(cards=[], value=0, is_soft=False),
            dealer_hand=Hand(cards=[], value=0, is_soft=False),
            deck=self.game_state.deck
        )
    def execute_dealer_turn(self) -> str:
        """
        Execute the dealer's turn according to standard blackjack rules.

        The dealer must hit on 16 or less and stand on 17 or more.
        This method evaluates the current dealer hand and determines the action.

        Returns:
            str: The dealer's action - "hit", "stand", or "bust"

        Note:
            This method only evaluates the current state. Actual card drawing
            should be handled by the CV pipeline detecting new cards.
        """
        if self.game_state is None or not self.game_state.dealer_hand.cards:
            print("No dealer hand to evaluate")
            return "stand"

        dealer_value = self.game_state.dealer_hand.value

        if dealer_value > 21:
            print(f"Dealer busts with {dealer_value}")
            return "bust"
        elif dealer_value <= 16:
            print(f"Dealer hits on {dealer_value}")
            return "hit"
        else:
            print(f"Dealer stands on {dealer_value}")
            return "stand"

    def is_dealer_done(self) -> bool:
        """
        Check if the dealer has completed their turn.

        Returns:
            bool: True if dealer should stand or has busted, False if dealer needs to hit
        """
        if self.game_state is None or not self.game_state.dealer_hand.cards:
            return True

        dealer_value = self.game_state.dealer_hand.value
        return dealer_value >= 17 or dealer_value > 21

    def get_dealer_upcard(self) -> Optional[Card]:
        """
        Get the dealer's upcard (first card dealt to dealer).

        Returns:
            Optional[Card]: The dealer's first card, or None if no cards dealt
        """
        if self.game_state and self.game_state.dealer_hand.cards:
            return self.game_state.dealer_hand.cards[0]
        return None

    def _calculate_hand_value(self, cards: List[Card]) -> int:
        """
        Calculate the total value of a blackjack hand.

        Follows standard blackjack rules:
        - Number cards (2-10) = face value
        - Face cards (J, Q, K) = 10
        - Aces = 11 (soft) or 1 (hard) depending on total

        Args:
            cards (List[Card]): List of cards in the hand.

        Returns:
            int: The calculated hand value (17-21 for blackjack, can exceed 21).
        """
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
        """
        Determine if a blackjack hand is "soft" (contains an Ace counting as 11).

        A hand is soft if it contains at least one Ace that can be counted as 11
        without busting the hand (total <= 21).

        Args:
            cards (List[Card]): List of cards in the hand.

        Returns:
            bool: True if the hand is soft, False if hard.
        """
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

    def _run_monte_carlo_simulation(self) -> None:
        """
        Run the Monte Carlo simulation for the current game state.

        Analyzes all possible actions (hit, stand, double, split) and determines
        the optimal action based on expected value. Results are stored in
        self.monte_carlo_result.
        """
        if not self.game_state:
            return

        # Convert card objects to values for Monte Carlo
        player_values = [RANK_VALUES[card.rank] for card in self.game_state.player_hand.cards]
        dealer_upcard = None
        
        if self.game_state.dealer_hand.cards:
            dealer_upcard = RANK_VALUES[self.game_state.dealer_hand.cards[0].rank]
        
        if not player_values or dealer_upcard is None:
            return

        try:
            self.monte_carlo_result = self.monte_carlo.analyze(
                player_cards=player_values,
                dealer_up_card=dealer_upcard,
                remaining_deck=self.game_state.deck,
                num_simulations=100000
            )
            print(f"Monte Carlo simulation complete: Optimal action = {self.monte_carlo_result.get('optimal_action')}")
        except Exception as e:
            print(f"Error running Monte Carlo simulation: {e}")
            self.monte_carlo_result = None

    def get_monte_carlo_result(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recent Monte Carlo simulation results.

        Returns:
            Optional[Dict[str, Any]]: The simulation results including player hand,
                dealer upcard, probabilities for each action, and optimal action.
                Returns None if no simulation has been run yet.
        """
        return self.monte_carlo_result


game_state_manager = GameStateManager()
"""
Global instance of GameStateManager for the blackjack game engine.

This singleton instance is used throughout the application to maintain
the current game state and handle state transitions. It should be imported
and used by other modules that need to interact with the game state.
"""