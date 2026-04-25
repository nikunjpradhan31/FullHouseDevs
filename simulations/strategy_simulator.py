import sys
import os
# Add the project root to Python path so we can import from game_engine_backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from strategies import RedSevenCount, ReverePointCount, HiLoCount, OmegaIICount, KOCount, KISS3Count, BasePlayer, NormalPlayer
from blackjack_simulator import BlackjackGameSimulator
from game_engine_backend.models.schemas import Card
from game_engine_backend.core.game_state_manager import build_default_deck, RANK_VALUES, RANKS, SUITS
from game_engine_backend.monte_carlo.blackjackSim import BlackjackSimulator as MonteCarloSimulator
import random
from typing import List, Dict, Tuple, Optional
import json
import time

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

NUM_DECKS = 6
MIN_BET = 10
MAX_BET = 1000
MIN_DETECTION_ROUNDS = 20
COUNT_ALIGNMENT_THRESHOLD = 0.6
RAISED_BET_MINIMUM = 12
TRUE_COUNT_SIGNAL_THRESHOLD = 1.3


# Simulates blackjack rounds with Monte Carlo EV analysis
def simulate_blackjack():
    """Simulate blackjack with card counting strategies and Monte Carlo detection."""
    simulator = BlackjackGameSimulator(NUM_DECKS, MIN_BET, MAX_BET)
    monte_carlo = MonteCarloSimulator()
    
    strategies = {
        'BasePlayer': BasePlayer(),
        'NormalPlayer': NormalPlayer(),
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
            'hands_played': 0,
            'count_aligned_bets': 0,
            'count_misaligned_bets': 0,
            'raised_bet_hands': 0,
            'raised_bet_true_count_total': 0.0
        }
        for name in strategies.keys()
    }
    
    for round_num in range(1, 251):
        # Deal initial hands
        player_hand = [simulator.deal_card(), simulator.deal_card()]
        dealer_hand = [simulator.deal_card(), simulator.deal_card()]

        if simulator.reshuffled:
            for strategy in strategies.values():
                if hasattr(strategy, 'reset'):
                    strategy.reset()
            simulator.reshuffled = False
        
        # Update strategies with seen cards
        all_cards = player_hand + dealer_hand
        for card in all_cards:
            for strategy in strategies.values():
                strategy.update(card)

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
            optimal_ev_per_unit = mc_result['optimal_ev']
        except Exception as e:
            print(f"Error in Monte Carlo for round {round_num}: {e}")
            optimal_ev_per_unit = 0

        final_player_hand = simulator.play_player_hand(player_hand.copy(), dealer_hand[0])
        final_dealer_hand = simulator.play_dealer_hand(dealer_hand.copy())
        winner = simulator.determine_winner(final_player_hand, final_dealer_hand)

        # Calculate bets and run Monte Carlo analysis for each strategy
        for name, strategy in strategies.items():
            if name != 'BasePlayer' and results[name]['rounds_to_threshold'] is not None:
                continue  # Skip if already flagged
            if hasattr(strategy, 'get_bet'):
                bet_amount = strategy.get_bet(MIN_BET, MAX_BET)
            else:
                bet_amount = simulator.calculate_bet_amount(strategy, MIN_BET, MAX_BET)
            results[name]['hands_played'] += 1

            bet_multiple = bet_amount / MIN_BET if MIN_BET else 1
            true_count = getattr(strategy, 'true_count', 0)
            if bet_multiple > 1:
                results[name]['raised_bet_hands'] += 1
                results[name]['raised_bet_true_count_total'] += true_count
                if true_count > 0:
                    results[name]['count_aligned_bets'] += 1
                else:
                    results[name]['count_misaligned_bets'] += 1

            expected_ev = optimal_ev_per_unit * bet_amount
            results[name]['total_ev_expected'] += expected_ev
            
            # Calculate actual profit/loss
            if winner == "player":
                profit = bet_amount
            elif winner == "dealer":
                profit = -bet_amount
            else:  # push
                profit = 0

            if name == 'NormalPlayer':
                strategy.update_result(winner)

            results[name]['total_profit'] += profit
            results[name]['total_ev_actual'] += profit
            
            # Calculate EV deviation for this hand
            ev_dev = profit - expected_ev
            results[name]['ev_deviation'] += ev_dev

            # Check if strategy should be flagged (EV deviation indicates card counting)
            if name != 'BasePlayer' and round_num >= MIN_DETECTION_ROUNDS:
                avg_ev_dev = results[name]['ev_deviation'] / results[name]['hands_played']
                raised_bet_hands = results[name]['raised_bet_hands']
                count_alignment_rate = (
                    results[name]['count_aligned_bets'] / raised_bet_hands
                    if raised_bet_hands > 0 else 0.0
                )
                avg_true_count_on_raised_bets = (
                    results[name]['raised_bet_true_count_total'] / raised_bet_hands
                    if raised_bet_hands > 0 else 0.0
                )
                if (
                    raised_bet_hands >= RAISED_BET_MINIMUM
                    and count_alignment_rate >= COUNT_ALIGNMENT_THRESHOLD
                    and avg_true_count_on_raised_bets >= TRUE_COUNT_SIGNAL_THRESHOLD
                ):
                    results[name]['rounds_to_threshold'] = round_num
                    print(
                        f"{name} flagged at round {round_num} with avg EV dev: {avg_ev_dev:.4f}, "
                        f"count-aligned betting rate {count_alignment_rate:.4f}, and "
                        f"avg true count on raised bets {avg_true_count_on_raised_bets:.4f}."
                    )
    return results

if __name__ == "__main__":
    results = simulate_blackjack()
    for strategy_name, data in results.items():
        hands = data.get('hands_played', 0)
        dev = data.get('ev_deviation', 0)
        data['avg_ev_dev_per_hand'] = dev / hands if hands > 0 else 0
        raised_bet_hands = data.get('raised_bet_hands', 0)
        data['count_alignment_rate'] = (
            data['count_aligned_bets'] / raised_bet_hands if raised_bet_hands > 0 else 0
        )
        data['avg_true_count_on_raised_bets'] = (
            data['raised_bet_true_count_total'] / raised_bet_hands
            if raised_bet_hands > 0 else 0
        )

    print("Strategy Detection Results (Monte Carlo EV Analysis):")
    print("=" * 70)
    for strategy_name, data in results.items():
        print(f"\n{strategy_name}:")
        print(f"  Hands Played: {data['hands_played']}")
        if data['rounds_to_threshold']:
            print(f" !! FLAGGED at round {data['rounds_to_threshold']}")
        else:
            print(f"  ✓ Not detected after 250 hands")
        print(f"  Total Profit: ${data['total_profit']:.2f}")
        print(f"  Expected EV: ${data['total_ev_expected']:.2f}")
        print(f"  Actual EV: ${data['total_ev_actual']:.2f}")
        print(f"  EV Deviation: ${data['ev_deviation']:.2f}")
        print(f"  Avg Deviation/Hand: ${data['avg_ev_dev_per_hand']:.4f}")
        print(f"  Raised Bet Hands: {data['raised_bet_hands']}")
        print(f"  Count Alignment Rate: {data['count_alignment_rate']:.4f}")
        print(f"  Avg True Count On Raised Bets: {data['avg_true_count_on_raised_bets']:.4f}")
        
    output_dir = "simulations/results"
    timestamp = int(time.time())
    file_name = f"blackjack_results_{timestamp}.json"
    file_path = os.path.join(output_dir, file_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(file_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"\nSuccessfully exported results to {file_path}")
    except Exception as e:
        print(f"Error saving JSON: {e}")
