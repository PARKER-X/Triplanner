from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class DayActivity(BaseModel):
    """An activity scheduled on a specific day"""
    sequence: int
    time_start: str  # "09:00"
    time_end: str  # "12:00"
    activity_id: str  # Reference to research activity
    activity_name: str
    category: str
    location: str
    address: str
    cost_per_person: float
    duration_minutes: int
    description: str
    why_included: str  # Explanation for user


class Meal(BaseModel):
    """A meal scheduled for a day"""
    type: str  # breakfast, lunch, dinner
    time: str  # "12:30"
    restaurant_name: str
    location: str
    cost_per_person: float
    cuisine: str


class DayPlan(BaseModel):
    """Complete plan for one day"""
    day_number: int
    date: Optional[str] = None
    theme: str  # e.g., "Cultural Exploration"
    
    activities: List[DayActivity]
    meals: List[Meal]
    
    # Stats
    total_activities: int
    total_cost: float
    total_walking_km: float
    estimated_steps: int
    rest_hours: float
    
    notes: str


class ItineraryStats(BaseModel):
    """Statistics for entire trip"""
    total_activities: int
    total_cost: float
    total_walking_km: float
    average_daily_cost: float
    estimated_total_steps: int
    average_daily_walking_km: float
    free_activities: int
    paid_activities: int
    
    interest_distribution: Dict[str, float]  # % of activities per interest
    neighborhood_distribution: Dict[str, int]  # Activities per neighborhood


class PlannerResult(BaseModel):
    """Complete itinerary plan"""
    trip_title: str
    trip_summary: str
    destination: str
    duration_days: int
    
    days: List[DayPlan]
    stats: ItineraryStats
    
    highlights: List[str]
    tips: List[str]
    warnings: List[str]