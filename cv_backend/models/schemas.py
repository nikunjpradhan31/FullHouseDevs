from pydantic import BaseModel
from typing import List

class Coordinate(BaseModel):
    x: float
    y: float
    w: float
    h: float

class CardDetection(BaseModel):
    rank: str
    suit: str
    confidence: float
    box: Coordinate

class CardDetectionPayload(BaseModel):
    frame_id: str
    timestamp: float
    detections: List[CardDetection]
