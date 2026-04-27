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
Simulates several blackjack betting/counting strategies and compares their results against a Monte Carlo EV baseline.

The Monte Carlo simulator estimates the optimal EV for each hand. The simulation also tracks whether raised bets line up
with a shared shoe-level count signal. The detector converts each counting strategy's true count into a normalized betting
signal, then averages those normalized signals to estimate the table state behind raised bets.

Simulation Structure:
- Simulate 250 rounds of blackjack with a standard 6-deck shoe
- For each round:
    1. Deal hands and update every strategy with the exposed cards
    2. Run Monte Carlo analysis to estimate the hand's optimal EV
    3. Convert each strategy's true count into a normalized betting signal and average the results
    4. Let each strategy bet/play the hand and record actual profit
    5. Track EV deviation and raised-bet alignment with the shared normalized count signal
    6. Flag strategies whose raised-bet behavior looks count-driven

Outputs:
- Rounds until a strategy is flagged by the betting-pattern detector
- Total profit and EV tracking for each strategy
- Raised-bet alignment rate and shared normalized count signal on raised bets
'''

NUM_DECKS = 6
MIN_BET = 10
MAX_BET = 1000
MIN_DETECTION_ROUNDS = 20
COUNT_ALIGNMENT_THRESHOLD = 0.6
RAISED_BET_MINIMUM = 12
SHARED_COUNT_SIGNAL_THRESHOLD = 1.1


def normalize_true_count_signal(true_count: float) -> float:
    """Anchor raw true counts to the first raise threshold used by the betting model."""
    return max(true_count - 1.0, 0.0)


def normalize_by_betting_correlation(true_count: float, system_name: str) -> float:
    """
    Convert true count to betting-equivalent signal using betting correlation.

    This creates comparable betting signals across different counting systems by:
    1. Applying betting correlation to account for system efficiency
    2. Using threshold to focus on positive betting opportunities
    """
    betting_correlations = {
        'HiLo': 0.97,
        'KO': 0.95,
        'OmegaII': 0.92,
        'RedSeven': 0.99,
        'ReverePoint': 0.95,
        'KISS3': 0.95
    }
    bc = betting_correlations.get(system_name, 0.95)

    # Convert true count to betting-equivalent signal
    # Systems typically start raising bets at TC >= 1
    betting_signal = max(true_count - 1.0, 0.0) * bc

    return betting_signal


# Simulates blackjack rounds with Monte Carlo EV baselines and betting-pattern detection
def simulate_blackjack():
    """Simulate blackjack strategies and flag count-driven betting patterns."""
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
    counting_strategy_names = [
        name for name in strategies
        if name not in {'BasePlayer', 'NormalPlayer'}
    ]
    
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
            'raised_bet_shared_signal_total': 0.0
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

        # Normalize each counting system onto the same betting scale before averaging.
        # Use betting correlation normalization to create comparable betting signals
        shared_count_signal = (
            sum(
                normalize_by_betting_correlation(
                    getattr(strategies[name], 'true_count', 0), name
                )
                for name in counting_strategy_names
            )
            / len(counting_strategy_names)
            if counting_strategy_names else 0.0
        )

        # Calculate bets and record how often raised bets align with the shared count signal.
        for name, strategy in strategies.items():
            if name != 'BasePlayer' and results[name]['rounds_to_threshold'] is not None:
                continue  # Skip if already flagged
            if hasattr(strategy, 'get_bet'):
                bet_amount = strategy.get_bet(MIN_BET, MAX_BET)
            else:
                bet_amount = simulator.calculate_bet_amount(strategy, MIN_BET, MAX_BET)
            results[name]['hands_played'] += 1

            bet_multiple = bet_amount / MIN_BET if MIN_BET else 1
            if bet_multiple > 1:
                results[name]['raised_bet_hands'] += 1
                results[name]['raised_bet_shared_signal_total'] += shared_count_signal
                if shared_count_signal > 0:
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

            # Flag strategies when raised bets consistently track the shared normalized count signal.
            if name != 'BasePlayer' and round_num >= MIN_DETECTION_ROUNDS:
                avg_ev_dev = results[name]['ev_deviation'] / results[name]['hands_played']
                raised_bet_hands = results[name]['raised_bet_hands']
                count_alignment_rate = (
                    results[name]['count_aligned_bets'] / raised_bet_hands
                    if raised_bet_hands > 0 else 0.0
                )
                avg_shared_count_signal_on_raised_bets = (
                    results[name]['raised_bet_shared_signal_total'] / raised_bet_hands
                    if raised_bet_hands > 0 else 0.0
                )
                if (
                    raised_bet_hands >= RAISED_BET_MINIMUM
                    and count_alignment_rate >= COUNT_ALIGNMENT_THRESHOLD
                    and avg_shared_count_signal_on_raised_bets >= SHARED_COUNT_SIGNAL_THRESHOLD
                ):
                    results[name]['rounds_to_threshold'] = round_num
                    print(
                        f"{name} flagged at round {round_num} with avg EV dev: {avg_ev_dev:.4f}, "
                        f"count-aligned betting rate {count_alignment_rate:.4f}, and "
                        f"avg shared betting correlation-normalized count signal on raised bets {avg_shared_count_signal_on_raised_bets:.4f}."
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
        data['avg_shared_count_signal_on_raised_bets'] = (
            data['raised_bet_shared_signal_total'] / raised_bet_hands
            if raised_bet_hands > 0 else 0
        )

    print("Strategy Detection Results (Monte Carlo EV + Betting Pattern Analysis):")
    print("=" * 70)
    for strategy_name, data in results.items():
        print(f"\n{strategy_name}:")
        print(f"  Hands Played: {data['hands_played']}")
        if data['rounds_to_threshold']:
            print(f" !! FLAGGED at round {data['rounds_to_threshold']}")
        else:
            print("  Not detected after 250 hands")
        print(f"  Total Profit: ${data['total_profit']:.2f}")
        print(f"  Expected EV: ${data['total_ev_expected']:.2f}")
        print(f"  Actual EV: ${data['total_ev_actual']:.2f}")
        print(f"  EV Deviation: ${data['ev_deviation']:.2f}")
        print(f"  Avg Deviation/Hand: ${data['avg_ev_dev_per_hand']:.4f}")
        print(f"  Raised Bet Hands: {data['raised_bet_hands']}")
        print(f"  Count Alignment Rate: {data['count_alignment_rate']:.4f}")
        print(f"  Avg Shared Betting Correlation-Normalized Count Signal On Raised Bets: {data['avg_shared_count_signal_on_raised_bets']:.4f}")
        
    output_dir = "simulations/results"
    timestamp = int(time.time())
    file_name = f"blackjack_results_new_{timestamp}.json"
    file_path = os.path.join(output_dir, file_name)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(file_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"\nSuccessfully exported results to {file_path}")
    except Exception as e:
        print(f"Error saving JSON: {e}")
