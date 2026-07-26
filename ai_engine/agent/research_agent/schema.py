from pydantic import BaseModel, Field
from typing import List, Optional, Dict,Union

from enum import Enum


class Coordinates(BaseModel):
    """Geographic coordinates"""
    lat: float
    lng: float


class TimeSlot(BaseModel):
    """Operating hours"""
    day: str  # Monday, Tuesday, etc.
    open_time: str  # "09:00"
    close_time: str  # "18:00"
    is_open: bool = True


class Activity(BaseModel):
    """A single activity/place to visit"""
    id: str
    name: str
    category: str  # restaurant, museum, park, etc.
    
    # Location data
    address: str
    coordinates: Coordinates
    area: str  # Neighborhood name
    
    # Time data
    duration_minutes: int  # How long to spend
    opening_hours: List[TimeSlot] = []
    
    # Cost data
    cost_per_person_inr: Optional[float] = None
    cost_type: str = "free"  # free, budget, moderate, expensive
    
    # Quality data
    rating: float  # 0-5
    review_count: int
    
    # Matching
    matches_interests: List[str]  # Which user interests it matches
    
    # Travel data
    description: str
    source: str  # "openstreetmap", "wikipedia", etc.


class DistanceInfo(BaseModel):
    """Distance between two activities"""
    from_activity: str
    to_activity: str
    distance_km: float
    travel_time_minutes: int  # Estimated by walking/transit
    travel_mode: str  # walking, transit, auto


class GroundingData(BaseModel):
    """Real-world constraints and data"""
    activities: List[Activity]
    distances: List[Union[Dict, 'DistanceInfo']] = []  # Accept both dicts and DistanceInfo objects
    weather: Optional[str] = None
    peak_hours: Dict[str, str] = {}
    neighborhoods: Dict[str, Dict] = {}

class ResearchResult(BaseModel):
    """Complete research result"""
    destination: str
    search_date: str
    
    # Retrieved activities
    activities: List[Activity]
    
    # Grounding data
    grounding: GroundingData
    
    # Summary
    total_activities_found: int
    feasible_activities: int
    budget_coverage: Dict[str, int]  # cost_type: count
    interest_coverage: Dict[str, float]  # interest: coverage %