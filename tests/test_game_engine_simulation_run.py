import asyncio
import sys
import os

# -----------------------------
# PATH SETUP
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "game_engine_backend")
sys.path.append(BACKEND_DIR)

from core.game_state_manager import game_state_manager, GamePhase
from core.kafka import process_card_detection, close_kafka_producer


# -----------------------------
# FAKE CV MESSAGES
# -----------------------------
def make_detection(rank, suit, zone="player"):
    return {
        "rank": rank,
        "suit": suit,
        "zone": zone,
        "timestamp": 123.0
    }


# -----------------------------
# TEST
# -----------------------------
async def test_process_card_detection():

    print("\n==============================")
    print(" PROCESS CARD DETECTION TEST ")
    print("==============================\n")

    try:
        # Reset state
        game_state_manager.game_state = None
        game_state_manager.current_phase = GamePhase.IDLE

        # Force valid state machine
        game_state_manager.transition_to(GamePhase.SHUFFLING)
        game_state_manager.transition_to(GamePhase.INITIAL_DEAL)
        game_state_manager.transition_to(GamePhase.PLAYER_TURN)

        print("[0] Sending dealer upcard...")
        await process_card_detection(make_detection("6", "Hearts", "dealer"))

        print("[1] Sending first card...")
        await process_card_detection(make_detection("2", "Spades", "player"))

        print("[2] Sending second card...")
        await process_card_detection(make_detection("9", "Clubs", "player"))

        print("\nFINAL STATE:")
        if game_state_manager.game_state:
            print(game_state_manager.game_state.player_hand.cards)
        else:
            print("No game state created")

        print("\nDONE\n")

    finally:
        # IMPORTANT: clean up Kafka producer to avoid warnings
        await close_kafka_producer()


if __name__ == "__main__":
    asyncio.run(test_process_card_detection())