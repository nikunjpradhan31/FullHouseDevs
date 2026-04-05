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

class SimulationResult(BaseModel):
    request_id: str
    win_probability: float
    loss_probability: float
    push_probability: float
    recommended_action: str # hit, stand, double, split
