import json
import os
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv
from models.schemas import Card, SimulationRequest, SimulationResult
from core.game_state_manager import game_state_manager
from core.hi_lo import hi_lo_tracker
from monte_carlo.blackjackSim import BlackjackSimulator
import traceback

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_CARD_DETECTIONS = "card-detections"
KAFKA_TOPIC_SIMULATION_REQUESTS = "simulation-requests"
KAFKA_TOPIC_SIMULATION_RESULTS = "simulation-results"

consumer_task = None
producer = None

async def get_kafka_producer():
    global producer
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await producer.start()
    return producer

async def close_kafka_producer():
    global producer
    if producer is not None:
        await producer.stop()

def parse_card_from_detection(detection: dict) -> Card:
    """Parse card detection from CV pipeline format"""
    # New CV backend format: {"rank": "A", "suit": "Hearts", "zone": "dealer", ...}
    rank = detection.get("rank", "")
    suit = detection.get("suit", "")

    if not rank or not suit:
        raise ValueError(f"Invalid card format: missing rank or suit in {detection}")

    return Card(rank=rank, suit=suit)

async def run_simulation(game_state, request_id: str):
    """Run Monte Carlo simulation and send results"""
    try:
        simulator = BlackjackSimulator()

        # this was an issue with that face suits were passed as letters to a simulation that uses only numbers, causing a type error
        RANK_TO_VALUE = {
            "11": 11,
            "A": 11,
            "K": 10,
            "Q": 10,
            "J": 10,
            "10": 10,
            "9": 9,
            "8": 8,
            "7": 7,
            "6": 6,
            "5": 5,
            "4": 4,
            "3": 3,
            "2": 2,
        }
        print(game_state.player_hand.cards)

        player_cards = [
            int(RANK_TO_VALUE[str(card.rank)])
            for card in game_state.player_hand.cards
        ]

        dealer_up_card_obj = game_state_manager.get_dealer_upcard()

        if not player_cards:
            print("Cannot run simulation: no player cards")
            return

        if dealer_up_card_obj is None:
            print("Cannot run simulation: no dealer upcard")
            return

        dealer_up_card = int(RANK_TO_VALUE[str(dealer_up_card_obj.rank)])

        remaining_deck = None
        if game_state.deck:
            remaining_deck = [
                RANK_TO_VALUE[c.rank] if hasattr(c, "rank") else RANK_TO_VALUE[str(c)]
                for c in game_state.deck
            ]

        player_cards = list(map(int, player_cards))
        dealer_up_card = int(dealer_up_card)
        # Run analysis
        result = simulator.analyze(
            player_cards=player_cards,
            dealer_up_card=dealer_up_card,
            remaining_deck=remaining_deck,
            num_simulations=10000
        )

        # Create simulation result
        sim_result = SimulationResult(
            request_id=request_id,
            player_hand=result['player_hand'],
            player_hand_value=result['player_hand_value'],
            dealer_up_card=result['dealer_up_card'],
            optimal_action=result['optimal_action'],
            optimal_ev=result['optimal_ev'],
            actions=result['actions']
        )

        # Send result via Kafka
        producer = await get_kafka_producer()
        await producer.send_and_wait(
            KAFKA_TOPIC_SIMULATION_RESULTS,
            sim_result.model_dump()
        )

        print(
            f"Simulation completed: {sim_result.optimal_action} "
            f"(Win: {sim_result.actions[sim_result.optimal_action].win_probability:.1%})"
        )


    except Exception as e:
        print("🔥 Simulation error occurred")
        traceback.print_exc()

async def process_card_detection(data: dict):
    """Process a card detection message from CV backend"""
    try:
        # New CV backend sends individual card detections, not arrays
        # Format: {"rank": "A", "suit": "Hearts", "zone": "dealer", "timestamp": 123.45, "raw_label": "Ah"}

        # Parse card
        card = parse_card_from_detection(data)

        # Use zone from CV backend to determine location
        zone = data.get("zone", "")
        if zone.startswith("player"):
            location = "player"
        elif zone == "dealer":
            location = "dealer"
        else:
            print(f"Unknown zone: {zone}, defaulting to player")
            location = "player"

        # Update game state
        hand_changed = game_state_manager.update_card(card, location)

        # Update Hi-Lo running count
        hi_lo_tracker.update(card)

        # Trigger simulation if player hand changed and we're in player turn
        current_phase = game_state_manager.get_current_phase()
        if hand_changed and current_phase.value == "player_turn":
            timestamp = data.get("timestamp", 0)
            request_id = f"req_{timestamp}_{len(game_state_manager.game_state.player_hand.cards)}"
            print("SIMULATION TRIGGER CHECK:",
                hand_changed,
                current_phase.value)
            await run_simulation(game_state_manager.game_state, request_id)

        # Check dealer status if card was dealt to dealer during dealer turn
        if location == "dealer" and current_phase.value == "dealer_turn":
            if game_state_manager.is_dealer_done():
                print("Dealer turn complete after card detection")
                game_state_manager.on_round_complete()

        timestamp = data.get("timestamp", 0)
        print(f"Processed card: {card.rank} of {card.suit} at {location} (zone: {zone}) at {timestamp}")

    except Exception as e:
        print(f"Error processing card detection: {e}")
        print(f"Message data: {data}")

async def consume_messages():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC_CARD_DETECTIONS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="game-engine-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        request_timeout_ms=5000,
        retry_backoff_ms=500

    )
    await consumer.start()
    try:
        async for msg in consumer:
            topic = msg.topic
            data = msg.value
            if topic == KAFKA_TOPIC_CARD_DETECTIONS:
                print(f"Received card detection: {data}")
                await process_card_detection(data)

    finally:
        await consumer.stop()

async def start_kafka_consumer():
    global consumer_task
    consumer_task = asyncio.create_task(consume_messages())

async def stop_kafka_consumer():
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
    await close_kafka_producer()
