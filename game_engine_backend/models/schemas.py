from pydantic import BaseModel
from typing import List, Optional

class Card(BaseModel):
    rank: str
    suit: str

class Hand(BaseModel):
    cards: List[Card]
    value: int
    is_soft: bool

class GameState(BaseModel):
    player_hand: Hand
    dealer_hand: Hand
    deck: Optional[List[int]] = None

class SimulationRequest(BaseModel):
    request_id: str
    game_state: GameState
    num_simulations: int = 10000

class ActionResult(BaseModel):
    win_probability: float
    lose_probability: float
    push_probability: float
    ev: float

class SimulationResult(BaseModel):
    request_id: str
    player_hand: list[int]
    player_hand_value: int
    dealer_up_card: int
    optimal_action: str  # hit, stand, double, split
    optimal_ev: float
    actions: dict[str, ActionResult]