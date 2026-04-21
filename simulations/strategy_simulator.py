import sys
import os
# Add the project root to Python path so we can import from game_engine_backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies import RedSevenCount, ReverePointCount, HiLoCount, OmegaIICount, KOCount, KISS3Count
from blackjack_simulator import BlackjackGameSimulator
from game_engine_backend.models.schemas import Card
from game_engine_backend.core.game_state_manager import build_default_deck, RANK_VALUES, RANKS, SUITS
from game_engine_backend.monte_carlo.blackjackSim import BlackjackSimulator as MonteCarloSimulator
import random
from typing import List, Dict, Tuple, Optional

'''
Simulates each card counting strategy and compares the game engine's performance to flag each strategy against the Monte Carlo EV. 
The game engine's Monte Carlo simulator analyzes each hand and predicts expected value. If a strategy's actual results 
consistently exceed the Monte Carlo EV predictions, it indicates card counting. If the strategy is not flagged by the ROUND_THRESHOLD, 
the strategy is considered undetectable by the game engine.

Simulation Structure:
- Simulate up to ROUND_THRESHOLD rounds of blackjack with a standard 6-deck shoe
- For each round:
    1. Deal hands and update card counting strategies
    2. Run Monte Carlo simulation to get optimal EV for that hand
    3. Play the hand and record actual result
    4. Track EV deviation (actual - expected)
    5. Flag strategy if cumulative EV deviation exceeds threshold

Outputs:
- Rounds until strategy detected via EV deviation
- Cumulative EV advantage gained through card counting
- Total profit before detection
'''

EV_DEVIATION_THRESHOLD = 0.15  # Flag if cumulative EV deviation per hand exceeds 15% on average
NUM_DECKS = 6
MIN_BET = 10
MAX_BET = 1000


# Simulates blackjack rounds with Monte Carlo EV analysis
def simulate_blackjack():
    """Simulate blackjack with card counting strategies and Monte Carlo detection."""
    simulator = BlackjackGameSimulator(NUM_DECKS, MIN_BET, MAX_BET)
    monte_carlo = MonteCarloSimulator()
    
    strategies = {
        'RedSeven': RedSevenCount(),
        'ReverePoint': ReverePointCount(),
        'HiLo': HiLoCount(),
        'OmegaII': OmegaIICount(),
        'KO': KOCount(),
        'KISS3': KISS3Count()
    }
    
    results = {
        name: {
            'rounds_to_threshold': None,
            'total_profit': 0,
            'total_ev_expected': 0.0,
            'total_ev_actual': 0.0,
            'ev_deviation': 0.0,
            'hands_played': 0
        }
        for name in strategies.keys()
    }
    
    for round_num in range(1, 1001):
        # Deal initial hands
        player_hand = [simulator.deal_card(), simulator.deal_card()]
        dealer_hand = [simulator.deal_card(), simulator.deal_card()]
        
        # Update strategies with seen cards
        all_cards = player_hand + dealer_hand
        for card in all_cards:
            for strategy in strategies.values():
                strategy.update(card)
        
        # Calculate bets and run Monte Carlo analysis for each strategy
        for name, strategy in strategies.items():
            if results[name]['rounds_to_threshold'] is not None:
                continue  # Skip if already flagged
                
            bet_amount = simulator.calculate_bet_amount(strategy, MIN_BET, MAX_BET)
            results[name]['hands_played'] += 1
            
            # Run Monte Carlo simulation to get expected value
            dealer_upcard_value = RANK_VALUES[dealer_hand[0].rank] if dealer_hand else None
            player_card_values = [RANK_VALUES[card.rank] for card in player_hand]
            remaining_deck_values = [RANK_VALUES[card.rank] for card in simulator.deck]
            try:
                mc_result = monte_carlo.analyze(
                    player_cards=player_card_values,
                    dealer_up_card=dealer_upcard_value,
                    remaining_deck=remaining_deck_values,
                    num_simulations=10000
                )
                expected_ev = mc_result['optimal_ev'] * bet_amount
                results[name]['total_ev_expected'] += expected_ev
            except Exception as e:
                print(f"Error in Monte Carlo for {name}: {e}")
                expected_ev = 0
            
            # Play out the hand
            final_player_hand = simulator.play_player_hand(player_hand.copy(), dealer_hand[0])
            final_dealer_hand = simulator.play_dealer_hand(dealer_hand.copy())
            winner = simulator.determine_winner(final_player_hand, final_dealer_hand)
            
            # Calculate actual profit/loss
            if winner == "player":
                profit = bet_amount
            elif winner == "dealer":
                profit = -bet_amount
            else:  # push
                profit = 0
            
            results[name]['total_profit'] += profit
            results[name]['total_ev_actual'] += profit
            
            # Calculate EV deviation for this hand
            ev_dev = profit - expected_ev
            results[name]['ev_deviation'] += ev_dev
            
            # Check if strategy should be flagged (EV deviation indicates card counting)
            if round_num > 20:
                avg_ev_dev = results[name]['ev_deviation'] / results[name]['hands_played']
                # Flag if cumulative EV deviation is significant (more hands won than expected)
                if avg_ev_dev > EV_DEVIATION_THRESHOLD:
                    results[name]['rounds_to_threshold'] = round_num
                    print(f"{name} flagged at round {round_num} with avg EV dev: {avg_ev_dev:.4f}")
    return results

if __name__ == "__main__":
    results = simulate_blackjack()
    
    print("Strategy Detection Results (Monte Carlo EV Analysis):")
    print("=" * 70)
    for strategy_name, data in results.items():
        rounds = data['rounds_to_threshold']
        total_profit = data['total_profit']
        total_ev_expected = data['total_ev_expected']
        total_ev_actual = data['total_ev_actual']
        ev_deviation = data['ev_deviation']
        hands_played = data['hands_played']
        
        avg_ev_dev = ev_deviation / hands_played if hands_played > 0 else 0
        
        print(f"\n{strategy_name}:")
        print(f"  Hands Played: {hands_played}")
        if rounds:
            print(f" !! FLAGGED at round {rounds}")
        else:
            print(f"  ✓ Not detected after 1000 hands")
        print(f"  Total Profit: ${total_profit:.2f}")
        print(f"  Expected EV: ${total_ev_expected:.2f}")
        print(f"  Actual EV: ${total_ev_actual:.2f}")
        print(f"  EV Deviation: ${ev_deviation:.2f}")
        print(f"  Avg Deviation/Hand: ${avg_ev_dev:.4f}")