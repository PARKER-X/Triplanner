from typing import List, Optional
from pydantic import BaseModel

class OptimizedActivity(BaseModel):
    sequence: int
    time_start: str
    time_end: str
    activity_id: str
    activity_name: str
    category: str
    location: str
    address: str
    cost_per_person: float
    duration_minutes: int
    description: str
    why_included: str
    travel_time_to_next: int = 0

class OptimizedDayPlan(BaseModel):
    day_number: int
    theme: str
    activities: List[OptimizedActivity]
    total_cost: float
    total_walking_km: float
    feasibility_score: float

class OptimizationStats(BaseModel):
    total_swaps: int
    score_improvement_pct: float
    stages_completed: int
    intra_day_time_ms: float
    inter_day_time_ms: float

class OptimizationResult(BaseModel):
    days: List[OptimizedDayPlan]
    stats: OptimizationStats
    total_score: float
    is_feasible: bool
    warnings: List[str]
