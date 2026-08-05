from pydantic import BaseModel
from typing import List, Dict, Optional

class Accommodation(BaseModel):
    id: str
    name: str
    type: str
    coordinates: Dict[str, float]
    cost_per_night: float
    area: str
    address: str
    amenities: List[str]
    rating: float
    description: str
    source: str
    suitability_score: float

class AccommodationResult(BaseModel):
    destination: str
    selected: Accommodation
    alternatives: List[Accommodation]
    budget_allocated: float
    budget_per_night: float
    total_nights: int
