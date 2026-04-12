"""
Blackjack Win Probability Simulator

Simulates all N hands simultaneously as NumPy array operations rather than
looping one hand at a time.

Card values: 2-10 = face value, J/Q/K = 10, Ace = 11

Ranks: 2-10 = face value, 11 = Jack, 12 = Queen, 13 = King, 14 = Ace
Splitting uses rank equality, so K+Q (both value 10) are NOT a splittable pair,
but K+K or Q+Q are.

"""

import numpy as np
import time
from typing import Optional


# Ranks: 2-10 natural, 11=Jack, 12=Queen, 13=King, 14=Ace
# Values: J/Q/K → 10, Ace → 11
RANKS  = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] * 8, dtype=np.int8)
VALUES = np.array([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 8, dtype=np.int8)

# For convenience when only values are needed (e.g. dealer deck)
FULL_DECK = VALUES.copy()


def rank_to_value(rank: np.ndarray) -> np.ndarray:
    """Convert rank array to value array. Works on scalars and arrays."""
    r = np.asarray(rank)
    v = np.where(r >= 11, np.where(r == 14, 11, 10), r)
    return v.astype(np.int32)


def hand_value_single(hand: list) -> int:
    total = sum(hand)
    aces = hand.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def hand_value_vec(cards: np.ndarray) -> np.ndarray:
    totals = cards.sum(axis=1).astype(np.int32)
    aces = (cards == 11).sum(axis=1).astype(np.int32)
    for _ in range(4):
        over = (totals > 21) & (aces > 0)
        totals -= over.astype(np.int32) * 10
        aces -= over.astype(np.int32)
    return totals


def is_soft_vec(cards: np.ndarray, totals: np.ndarray) -> np.ndarray:
    # A hand is soft if it contains an ace that is currently counted as 11.
    # An ace counts as 11 when the raw sum <= 21 (no conversion needed yet).
    # Once the raw sum > 21 an ace gets converted to 1, making the hand hard.
    # So: soft iff hand contains an 11 AND raw sum (pre-conversion) <= 21.
    has_ace = (cards == 11).any(axis=1)
    raw = cards.sum(axis=1).astype(np.int32)
    return has_ace & (raw <= 21)


def build_available_deck(remaining_deck, player_cards, dealer_up_card):
    """
    Returns (avail_values, avail_ranks) after removing known cards.
    player_cards and dealer_up_card are VALUES (2-11).
    When remaining_deck is None we use the full double deck.
    """
    if remaining_deck is not None:
        base_values = np.array(remaining_deck, dtype=np.int8)
        # Reconstruct ranks from values: 10-valued cards get rank 10
        # (we have no rank info from the caller, so treat all 10s as rank 10)
        base_ranks = np.where(base_values == 11,
                              np.int8(14),        # Ace → rank 14
                              base_values.astype(np.int8))
    else:
        base_values = VALUES.copy()
        base_ranks  = RANKS.copy()

    avail_v = list(base_values)
    avail_r = list(base_ranks)

    known = list(player_cards or [])
    if dealer_up_card is not None:
        known.append(dealer_up_card)

    for card_val in known:
        try:
            idx = avail_v.index(card_val)
            avail_v.pop(idx)
            avail_r.pop(idx)
        except ValueError:
            pass

    return np.array(avail_v, dtype=np.int8), np.array(avail_r, dtype=np.int8)


def deal_from_deck(values: np.ndarray, ranks: np.ndarray, N: int, n_cards: int):
    """
    Returns (dealt_values, dealt_ranks, remaining_values, remaining_ranks).
    Each row is an independently shuffled draw from the same deck.
    """
    indices = np.argsort(np.random.rand(N, len(values)), axis=1)
    shuf_v = values[indices]
    shuf_r = ranks[indices]
    return (shuf_v[:, :n_cards],
            shuf_r[:, :n_cards],
            shuf_v[:, n_cards:],
            shuf_r[:, n_cards:])


def simulate_dealer(up_cards, hole_cards, remaining_values):
    """Dealer always uses values only — rank is irrelevant for hit/stand."""
    N = len(up_cards)
    MAX_COLS = 12
    hands = np.zeros((N, MAX_COLS), dtype=np.int32)
    hands[:, 0] = up_cards
    hands[:, 1] = hole_cards
    n_cols = np.full(N, 2, dtype=np.int32)
    draw_idx = np.zeros(N, dtype=np.int32)

    for _ in range(MAX_COLS - 2):
        col_mask = np.arange(MAX_COLS)[None, :] < n_cols[:, None]
        totals = hand_value_vec(np.where(col_mask, hands, 0))
        must_hit = (totals < 17) & (draw_idx < remaining_values.shape[1])
        if not must_hit.any():
            break
        safe_idx = np.minimum(draw_idx, remaining_values.shape[1] - 1)
        drawn = np.where(must_hit, remaining_values[np.arange(N), safe_idx], 0)
        flat_idx = np.clip(np.arange(N) * MAX_COLS + n_cols, 0, N * MAX_COLS - 1)
        hands.flat[flat_idx] = np.where(must_hit, drawn, hands.flat[flat_idx])
        n_cols += must_hit.astype(np.int32)
        draw_idx += must_hit.astype(np.int32)

    col_mask = np.arange(MAX_COLS)[None, :] < n_cols[:, None]
    final = hand_value_vec(np.where(col_mask, hands, 0))
    return np.where(final > 21, 0, final)


def should_hit(totals, soft, dealer_up):
    du, pv = dealer_up, totals
    hard_hit = (
        (~soft & (pv <= 11)) |
        (~soft & (pv == 12) & ~np.isin(du, [4, 5, 6])) |
        (~soft & (pv >= 13) & (pv <= 16) & ~np.isin(du, [2, 3, 4, 5, 6]))
    )
    soft_hit = (
        (soft & (pv <= 17)) |
        (soft & (pv == 18) & np.isin(du, [9, 10, 11]))
    )
    return hard_hit | soft_hit


def should_double(totals, soft, dealer_up):
    du, pv = dealer_up, totals
    hard_double = (
        (~soft & (pv == 11)) |
        (~soft & (pv == 10) & ~np.isin(du, [10, 11])) |
        (~soft & (pv == 9)  & np.isin(du, [3, 4, 5, 6])) |
        (~soft & (pv == 8)  & np.isin(du, [5, 6]))
    )
    soft_double = (
        (soft & (pv == 19) & np.isin(du, [6])) |
        (soft & (pv == 18) & np.isin(du, [2, 3, 4, 5, 6])) |
        (soft & (pv == 17) & np.isin(du, [3, 4, 5, 6])) |
        (soft & (pv == 16) & np.isin(du, [4, 5, 6])) |
        (soft & (pv == 15) & np.isin(du, [4, 5, 6])) |
        (soft & (pv == 14) & np.isin(du, [5, 6])) |
        (soft & (pv == 13) & np.isin(du, [5, 6]))
    )
    return hard_double | soft_double


def should_split(card_rank, dealer_up):
    """
    Split decision based on RANK (not value).
    Ranks: 2-10 natural, 11=Jack, 12=Queen, 13=King, 14=Ace.
    10-value cards (10, J, Q, K) are never split — they have different ranks
    and are excluded from the split table.
    Aces (rank 14) are always split.
    """
    du = dealer_up
    # Aces (rank 14) and 8s always split
    always_split = np.isin(card_rank, [14, 8])
    split_vs_dealer = (
        (np.isin(card_rank, [9]) & np.isin(du, [2, 3, 4, 5, 6, 8, 9])) |
        (np.isin(card_rank, [7]) & np.isin(du, [2, 3, 4, 5, 6, 7])) |
        (np.isin(card_rank, [6]) & np.isin(du, [2, 3, 4, 5, 6])) |
        (np.isin(card_rank, [4]) & np.isin(du, [5, 6])) |
        (np.isin(card_rank, [3]) & np.isin(du, [2, 3, 4, 5, 6, 7])) |
        (np.isin(card_rank, [2]) & np.isin(du, [2, 3, 4, 5, 6, 7]))
    )
    return always_split | split_vs_dealer


def simulate_player(initial_values, dealer_up, remaining_values, split_aces=False):
    """
    Player strategy uses values only — rank only matters at split decision time.
    split_aces=True enforces the casino rule that split aces receive exactly one
    additional card and may not hit further, regardless of the total.
    """
    N, k = initial_values.shape
    MAX_COLS = 12
    hands = np.zeros((N, MAX_COLS), dtype=np.int32)
    hands[:, :k] = initial_values
    n_cols = np.full(N, k, dtype=np.int32)
    draw_idx = np.zeros(N, dtype=np.int32)

    for _ in range(MAX_COLS - k):
        col_mask = np.arange(MAX_COLS)[None, :] < n_cols[:, None]
        masked = np.where(col_mask, hands, 0)
        pv = hand_value_vec(masked)
        soft = is_soft_vec(masked, pv)

        if np.ndim(split_aces) == 0:
            # scalar — same rule applies to all hands
            if split_aces:
                hit = (draw_idx == 0) & (draw_idx < remaining_values.shape[1])
            else:
                hit = should_hit(pv, soft, dealer_up) & (pv <= 21) & (draw_idx < remaining_values.shape[1])
        else:
            # per-row array — ace-split hands get one card, others play normally
            one_card = (draw_idx == 0) & (draw_idx < remaining_values.shape[1])
            normal   = should_hit(pv, soft, dealer_up) & (pv <= 21) & (draw_idx < remaining_values.shape[1])
            hit = np.where(split_aces, one_card, normal)

        if not hit.any():
            break
        safe_idx = np.minimum(draw_idx, remaining_values.shape[1] - 1)
        drawn = np.where(hit, remaining_values[np.arange(N), safe_idx], 0)
        flat_idx = np.clip(np.arange(N) * MAX_COLS + n_cols, 0, N * MAX_COLS - 1)
        hands.flat[flat_idx] = np.where(hit, drawn, hands.flat[flat_idx])
        n_cols += hit.astype(np.int32)
        draw_idx += hit.astype(np.int32)

    col_mask = np.arange(MAX_COLS)[None, :] < n_cols[:, None]
    return hand_value_vec(np.where(col_mask, hands, 0)), draw_idx


def _advance_deck(padded, offsets, M):
    col_idx = offsets[:, None] + np.arange(M)[None, :]
    col_idx = np.clip(col_idx, 0, padded.shape[1] - 1)
    return padded[np.arange(len(offsets))[:, None], col_idx]


def _tally(outcomes, N, scale=1, ev_override=None):
    base = outcomes if scale == 1 else outcomes // scale
    win  = int((base > 0).sum())
    lose = int((base < 0).sum())
    push = int((base == 0).sum())
    ev = float(ev_override.mean()) if ev_override is not None else float(outcomes.mean())
    return {
        'win_probability':  round(win  / (win + lose + push), 4),
        'lose_probability': round(lose / (win + lose + push), 4),
        'push_probability': round(push / (win + lose + push), 4),
        'ev': round(ev, 4),
        'simulations': win + lose + push,
    }


def simulate_stand(avail_v, avail_r, player_cards, dealer_up, N):
    pv = hand_value_single(player_cards)
    dealt_v, _, remaining_v, _ = deal_from_deck(avail_v, avail_r, N, 1)
    hole = dealt_v[:, 0].astype(np.int32)
    up = np.full(N, dealer_up, dtype=np.int32)
    dv = simulate_dealer(up, hole, remaining_v.astype(np.int32))
    outcomes = np.where(dv == 0, 1, np.where(pv > dv, 1, np.where(pv < dv, -1, 0)))
    return _tally(outcomes, N)


def simulate_hit(avail_v, avail_r, player_cards, dealer_up, N):
    n_pc = len(player_cards)
    dealt_v, _, remaining_v, _ = deal_from_deck(avail_v, avail_r, N, 2)
    hole      = dealt_v[:, 0].astype(np.int32)
    first_hit = dealt_v[:, 1].astype(np.int32)
    up  = np.full(N, dealer_up, dtype=np.int32)
    rem = remaining_v.astype(np.int32)

    initial = np.zeros((N, n_pc + 1), dtype=np.int32)
    initial[:, :n_pc] = np.array(player_cards, dtype=np.int32)[None, :]
    initial[:, n_pc]  = first_hit

    pf, draw_idx = simulate_player(initial, up, rem)

    M = rem.shape[1]
    padded = np.concatenate([rem, np.zeros((N, M), dtype=np.int32)], axis=1)
    dv = simulate_dealer(up, hole, _advance_deck(padded, draw_idx, M))

    outcomes = np.where(pf > 21, -1,
               np.where(dv == 0, 1,
               np.where(pf > dv, 1,
               np.where(pf < dv, -1, 0))))
    return _tally(outcomes, N)


def simulate_double(avail_v, avail_r, player_cards, dealer_up, N):
    dealt_v, _, remaining_v, _ = deal_from_deck(avail_v, avail_r, N, 2)
    hole     = dealt_v[:, 0].astype(np.int32)
    hit_card = dealt_v[:, 1].astype(np.int32)
    up = np.full(N, dealer_up, dtype=np.int32)

    pc = np.tile(np.array(player_cards, dtype=np.int32), (N, 1))
    fv = hand_value_vec(np.concatenate([pc, hit_card[:, None]], axis=1))
    dv = simulate_dealer(up, hole, remaining_v.astype(np.int32))

    outcomes = np.where(fv > 21, -2,
               np.where(dv == 0, 2,
               np.where(fv > dv, 2,
               np.where(fv < dv, -2, 0))))
    return _tally(outcomes, N, scale=2)


def simulate_split(avail_v, avail_r, player_cards, dealer_up, N):
    """Split: card identity comes from values; rank is preserved for correctness."""
    card_val = player_cards[0]
    dealt_v, _, remaining_v, _ = deal_from_deck(avail_v, avail_r, N, 3)
    hole      = dealt_v[:, 0].astype(np.int32)
    new_cards = [dealt_v[:, 1].astype(np.int32), dealt_v[:, 2].astype(np.int32)]
    up  = np.full(N, dealer_up, dtype=np.int32)
    rem = remaining_v.astype(np.int32)

    M = rem.shape[1]
    padded = np.concatenate([rem, np.zeros((N, M), dtype=np.int32)], axis=1)
    draw_offset = np.zeros(N, dtype=np.int32)
    hand_finals = []

    is_ace_split = (card_val == 11)
    for new_card in new_cards:
        initial = np.stack([np.full(N, card_val, dtype=np.int32), new_card], axis=1)
        pf, consumed = simulate_player(initial, up, _advance_deck(padded, draw_offset, M),
                                       split_aces=is_ace_split)
        draw_offset += consumed
        hand_finals.append(pf)

    dv = simulate_dealer(up, hole, _advance_deck(padded, draw_offset, M))

    total_ev = np.zeros(N, dtype=np.float64)
    for pf in hand_finals:
        total_ev += np.where(pf > 21, -1.0,
                    np.where(dv == 0, 1.0,
                    np.where(pf > dv, 1.0,
                    np.where(pf < dv, -1.0, 0.0))))

    avg_ev = total_ev / 2.0
    return _tally(np.sign(avg_ev).astype(np.int32), N, ev_override=avg_ev)


class BlackjackSimulator:

    def analyze(self, player_cards, dealer_up_card, remaining_deck=None, num_simulations=100000):
        """
        player_cards:   your current hand as VALUES, e.g. [10, 6]. Ace = 11.
        dealer_up_card: dealer's visible card VALUE.
        remaining_deck: cards left in shoe as VALUES (Ace=11). Pass the full
                        remaining deck including player/dealer cards — they'll
                        be removed. None uses a full double deck (104 cards).

        Split eligibility uses RANK equality: two Kings split, King+Queen do not.
        When remaining_deck is supplied as values only, all 10-value cards are
        assigned rank 10, so K+Q from an external deck will correctly not split.
        """
        avail_v, avail_r = build_available_deck(remaining_deck, player_cards, dealer_up_card)
        pv = hand_value_single(player_cards)
        N  = num_simulations

        actions = {
            'stand': simulate_stand(avail_v, avail_r, player_cards, dealer_up_card, N),
            'hit':   simulate_hit(avail_v, avail_r, player_cards, dealer_up_card, N),
        }

        if len(player_cards) == 2:
            actions['double'] = simulate_double(avail_v, avail_r, player_cards, dealer_up_card, N)

        # --- Pair check: use the rank of each card ---
        # player_cards are values; map back to a canonical rank.
        # Ace (value 11) → rank 14; all others: rank == value.
        # This correctly prevents K+Q splits (both value 10, but caller
        # must supply them as value 10 — indistinguishable without rank info).
        # When dealing from the internal deck we DO have ranks.
        if len(player_cards) == 2 and len(avail_v) >= 4:
            v0, v1 = player_cards
            # Same value AND neither is a face-card ambiguity (10 could be 10/J/Q/K).
            # For the mid-hand API we conservatively allow splitting 10s only when
            # the caller explicitly passes the same value for both cards — casino
            # rules still say don't split 10s, so EV will reject it anyway.
            if v0 == v1:
                # Only offer split if basic strategy would ever consider it.
                # 10-value pairs (10, J, Q, K) are never in the split table,
                # so should_split will return False and split won't be offered.
                dummy_rank = np.array([v0 if v0 != 11 else 14])
                if should_split(dummy_rank, np.array([dealer_up_card])).any():
                    actions['split'] = simulate_split(avail_v, avail_r, player_cards, dealer_up_card, N)

        for action, r in actions.items():
            r['action'] = action

        best = max(actions, key=lambda a: actions[a]['ev'])

        return {
            'player_hand':       player_cards,
            'player_hand_value': pv,
            'dealer_up_card':    dealer_up_card,
            'deck_size':         len(remaining_deck) if remaining_deck else 104,
            'cards_in_sim':      len(avail_v),
            'actions':           actions,
            'optimal_action':    best,
            'optimal_ev':        actions[best]['ev'],
        }

    def analyze_start(self, remaining_deck=None, num_simulations=100000):
        """
        Win/lose/push probability and EV at the very start of a hand
        before any cards are dealt. Applies full basic strategy including
        splits and doubles.

        Split pairs are identified by RANK, so K+Q is NOT a pair.
        """
        if remaining_deck is not None:
            base_v = np.array(remaining_deck, dtype=np.int8)
            base_r = np.where(base_v == 11, np.int8(14), base_v).astype(np.int8)
        else:
            base_v = VALUES.copy()
            base_r = RANKS.copy()

        N = num_simulations

        dealt_v, dealt_r, remaining_v, _ = deal_from_deck(base_v, base_r, N, 4)

        p1_v = dealt_v[:, 0].astype(np.int32)
        p2_v = dealt_v[:, 1].astype(np.int32)
        up_v = dealt_v[:, 2].astype(np.int32)
        hole_v = dealt_v[:, 3].astype(np.int32)

        p1_r = dealt_r[:, 0].astype(np.int32)  # ranks for pair check
        p2_r = dealt_r[:, 1].astype(np.int32)

        initial_two = np.stack([p1_v, p2_v], axis=1)
        player_bj = hand_value_vec(initial_two) == 21
        dealer_bj = hand_value_vec(np.stack([up_v, hole_v], axis=1)) == 21

        pv_init   = hand_value_vec(initial_two)
        soft_init = is_soft_vec(initial_two, pv_init)

        # Pair check uses RANKS — K+Q (both rank 10-value but different ranks) is NOT a pair
        is_pair  = (p1_r == p2_r)
        do_split = is_pair & should_split(p1_r, up_v) & ~player_bj

        do_double = should_double(pv_init, soft_init, up_v) & ~player_bj & ~do_split

        rem = remaining_v.astype(np.int32)
        M   = rem.shape[1]
        padded = np.concatenate([rem, np.zeros((N, M), dtype=np.int32)], axis=1)

        # ---- split ev ----
        split_card1 = rem[np.arange(N), 0]
        split_card2 = rem[np.arange(N), 1]
        split_rem   = _advance_deck(padded, np.full(N, 2, dtype=np.int32), M)

        hand_a = np.stack([p1_v, split_card1], axis=1)
        hand_b = np.stack([p1_v, split_card2], axis=1)

        # Aces (rank 14) get exactly one card each after the split
        ace_split = (p1_r == 14)
        padded_split = np.concatenate([split_rem, np.zeros((N, M), dtype=np.int32)], axis=1)
        pf_a, consumed_a = simulate_player(hand_a, up_v, split_rem, split_aces=ace_split)
        pf_b, consumed_b = simulate_player(hand_b, up_v, _advance_deck(padded_split, consumed_a, M), split_aces=ace_split)

        total_split_consumed = 2 + consumed_a + consumed_b
        dv_split = simulate_dealer(up_v, hole_v, _advance_deck(padded, total_split_consumed, M))

        ev_a = np.where(pf_a > 21, -1.0, np.where(dv_split == 0, 1.0, np.where(pf_a > dv_split, 1.0, np.where(pf_a < dv_split, -1.0, 0.0))))
        ev_b = np.where(pf_b > 21, -1.0, np.where(dv_split == 0, 1.0, np.where(pf_b > dv_split, 1.0, np.where(pf_b < dv_split, -1.0, 0.0))))
        ev_split = ev_a + ev_b

        # ---- double ev ----
        double_card  = rem[np.arange(N), 0]
        doubled_hand = np.concatenate([initial_two, double_card[:, None]], axis=1)
        pf_double    = hand_value_vec(doubled_hand)
        dv_double    = simulate_dealer(up_v, hole_v, _advance_deck(padded, np.ones(N, dtype=np.int32), M))

        ev_double = np.where(pf_double > 21, -2.0,
                    np.where(dv_double == 0, 2.0,
                    np.where(pf_double > dv_double, 2.0,
                    np.where(pf_double < dv_double, -2.0, 0.0))))

        # ---- normal hit/stand ev ----
        pf_normal, consumed = simulate_player(initial_two, up_v, rem)
        pf_normal = np.where(player_bj, 21, pf_normal)
        dv_normal = simulate_dealer(up_v, hole_v, _advance_deck(padded, consumed, M))

        ev_normal = np.where(player_bj & dealer_bj, 0.0,
                    np.where(player_bj, 1.5,
                    np.where(dealer_bj, -1.0,
                    np.where(pf_normal > 21, -1.0,
                    np.where(dv_normal == 0, 1.0,
                    np.where(pf_normal > dv_normal, 1.0,
                    np.where(pf_normal < dv_normal, -1.0, 0.0)))))))

        ev = np.where(do_split,  ev_split,
             np.where(do_double, ev_double,
             ev_normal))

        win  = int((ev > 0).sum())
        lose = int((ev < 0).sum())
        push = int((ev == 0).sum())
        total = win + lose + push

        return {
            'phase':            'start_of_hand',
            'deck_size':        len(base_v),
            'simulations':      total,
            'win_probability':  round(win  / total, 4),
            'lose_probability': round(lose / total, 4),
            'push_probability': round(push / total, 4),
            'ev':               round(float(ev.mean()), 4),
        }

    def print_analysis(self, result):
        if 'phase' in result:
            print(f"  Deck size: {result['deck_size']} cards  |  Simulations: {result['simulations']:,}")
            print(f"  Win:  {result['win_probability']*100:.1f}%")
            print(f"  Lose: {result['lose_probability']*100:.1f}%")
            print(f"  Push: {result['push_probability']*100:.1f}%")
            print(f"  EV:   {result['ev']:+.4f} units")
            return

        print(f"  Player: {result['player_hand']} ({result['player_hand_value']})  "
              f"|  Dealer up: {result['dealer_up_card']}  "
              f"|  {result['cards_in_sim']} cards in sim")
        print()
        print(f"  {'Action':<8} {'Win%':>6}  {'Lose%':>6}  {'Push%':>6}  {'EV':>8}")
        print(f"  {'-'*45}")

        for action, r in sorted(result['actions'].items(), key=lambda x: x[1]['ev'], reverse=True):
            note = ""
            if action == result['optimal_action']:
                note = "<- optimal"
            elif action == 'double':
                note = "(bet x2)"
            elif action == 'split':
                note = "(avg/hand)"
            print(f"  {action:<8} {r['win_probability']*100:>5.1f}%  "
                  f"{r['lose_probability']*100:>5.1f}%  "
                  f"{r['push_probability']*100:>5.1f}%  "
                  f"{r['ev']:>+8.4f}  {note}")


if __name__ == "__main__":
    sim = BlackjackSimulator()
    N = 100000

    print("=" * 60)
    print("BLACKJACK EV SIMULATOR -- double deck, stand on soft 17")
    print("=" * 60)

    t0 = time.time()

    print("\n[0] Start of hand, full double deck:")
    sim.print_analysis(sim.analyze_start(num_simulations=1000000))

    print("\n[1] Hard 16 vs 10:")
    sim.print_analysis(sim.analyze([10, 6], dealer_up_card=10, num_simulations=N))

    print("\n[2] Hard 16 vs 10, 10-rich deck:")
    sim.print_analysis(sim.analyze([10, 6], dealer_up_card=10,
        remaining_deck=[10, 6, 10] + [10, 10, 10, 10, 11, 9, 8] * 4, num_simulations=1000000))

    print("\n[3] Soft 18 (A+7) vs 9:")
    sim.print_analysis(sim.analyze([11, 7], dealer_up_card=9, num_simulations=N))

    print("\n[4] Soft 17 (A+6) vs 6:")
    sim.print_analysis(sim.analyze([11, 6], dealer_up_card=6, num_simulations=N))

    print("\n[5] Pair of 8s vs 6:")
    sim.print_analysis(sim.analyze([8, 8], dealer_up_card=6, num_simulations=N))

    print("\n[6] Hard 11 vs 5:")
    sim.print_analysis(sim.analyze([7, 4], dealer_up_card=5, num_simulations=N))

    print("\n[7] Hard 20 vs 6:")
    sim.print_analysis(sim.analyze([10, 10], dealer_up_card=6, num_simulations=N))

    print("\n" + "=" * 60)
    print("START-OF-HAND EV BY DECK COMPOSITION")
    print("=" * 60)

    print("\n[8] Neutral half shoe (26 cards):")
    sim.print_analysis(sim.analyze_start(
        remaining_deck=[2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 2,
        num_simulations=N))

    print("\n[9] 10-rich half shoe:")
    sim.print_analysis(sim.analyze_start(
        remaining_deck=[10,10,10,10,11,11,10,10,9,9,10,10,10,11,8,9,10,10,7,9,10,10,10,11,8,10],
        num_simulations=N))

    print("\n[10] Low-card half shoe:")
    sim.print_analysis(sim.analyze_start(
        remaining_deck=[2,3,4,5,6,2,3,4,5,6,2,3,4,5,6,2,3,4,5,6,7,7,7,8,8,8],
        num_simulations=N))

    print("\n" + "=" * 60)
    print("MID-HAND SCENARIOS")
    print("=" * 60)

    print("\n[11] Player 13 vs 2, 10-rich late shoe:")
    sim.print_analysis(sim.analyze([3, 2], dealer_up_card=2,
        remaining_deck=[3,2,2]+[10,10,10,10,10,11,11,10,10,9,10,10,10,11,10,10,10],
        num_simulations=N))

    print("\n[12] Player 11 vs 10, low-card shoe:")
    sim.print_analysis(sim.analyze([7, 4], dealer_up_card=10,
        remaining_deck=[7,4,10]+[2,3,4,5,6,2,3,4,5,6,2,3,4,5,6,7,7,7,8,8,9],
        num_simulations=N))

    print("\n[13] Soft 17 vs 8, nearly exhausted shoe:")
    sim.print_analysis(sim.analyze([11, 6], dealer_up_card=8,
        remaining_deck=[11,6,8,10,4,9,3,10,7,2],
        num_simulations=N))

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"14 scenarios x {N:,} sims in {elapsed:.2f}s")
    print(f"EV: +1.0 = win 1 unit | double: +-2.0 max | split: sum of 2 hands")
    print("=" * 60)