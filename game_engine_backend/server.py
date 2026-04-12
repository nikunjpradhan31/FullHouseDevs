import os
import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn

from core.kafka import (
    start_kafka_consumer, stop_kafka_consumer,
)
from core.game_state_manager import game_state_manager
from core.hi_lo import hi_lo_tracker
from models.schemas import GameState, BetRequest

load_dotenv()



PORT = int(os.getenv("GAME_ENG_BACKEND_PORT", 9093))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await start_kafka_consumer()
    yield
    # Shutdown
    #task.cancel()
    await stop_kafka_consumer()

app = FastAPI(title="Game Engine Backend", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game_engine_backend"}

@app.get("/game-state")
async def get_game_state():
    """Get current game state and phase"""
    return {
        "phase": game_state_manager.get_current_phase().value,
        "game_state": game_state_manager.game_state.model_dump() if game_state_manager.game_state else None,
        "dealer_upcard": game_state_manager.get_dealer_upcard().model_dump() if game_state_manager.get_dealer_upcard() else None
    }

@app.get("/hi-lo")
async def get_hi_lo():
    """Returns Hi-Lo system state"""
    return hi_lo_tracker.get_state()

@app.post("/bet")
async def record_bet(request: BetRequest):
    """Record a player's bet amount for card counter detection"""
    hi_lo_tracker.record_bet(request.amount)
    return {
        "status": "recorded",
        "true_count": round(hi_lo_tracker.true_count, 2),
        "bets_recorded": len(hi_lo_tracker.bet_history)
    }

@app.post("/shuffle")
async def trigger_shuffle():
    """Manually trigger shuffle (resets game state and Hi-Lo count)"""
    game_state_manager.on_shuffle()
    hi_lo_tracker.reset()
    return {"status": "shuffled", "phase": game_state_manager.get_current_phase().value}

@app.post("/initial-deal")
async def trigger_initial_deal():
    """Transition to initial deal phase"""
    success = game_state_manager.transition_to(game_state_manager.GamePhase.INITIAL_DEAL)
    return {"success": success, "phase": game_state_manager.get_current_phase().value}

@app.post("/player-turn")
async def trigger_player_turn():
    """Transition to player turn phase"""
    success = game_state_manager.transition_to(game_state_manager.GamePhase.PLAYER_TURN)
    return {"success": success, "phase": game_state_manager.get_current_phase().value}

@app.post("/dealer-turn")
async def trigger_dealer_turn():
    """Transition to dealer turn phase"""
    success = game_state_manager.transition_to(game_state_manager.GamePhase.DEALER_TURN)
    return {"success": success, "phase": game_state_manager.get_current_phase().value}

@app.post("/round-complete")
async def trigger_round_complete():
    """Transition to round complete phase"""
    success = game_state_manager.transition_to(game_state_manager.GamePhase.ROUND_COMPLETE)
    return {"success": success, "phase": game_state_manager.get_current_phase().value}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
