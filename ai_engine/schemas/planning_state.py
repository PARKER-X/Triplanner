"""
PlanningState — The shared blackboard that flows through all agents.

Every agent reads from and writes to this state object.
The orchestrator passes it from stage to stage.

Design: Inspired by Google's trip planning pipeline where each stage
enriches the state with more grounded, optimized data.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class PlanningState(BaseModel):
    """
    Central state object that flows through the entire planning pipeline.

    Stage flow:
        Intent → Accommodation → Research → Ranking → Planner → Optimizer → Critic

    Each agent reads what it needs and writes its results back.
    """

    # ── User Input ──────────────────────────────────────────
    user_goal: str = Field(
        default="",
        description="Raw user query string"
    )

    # ── Stage 1: Intent Agent Output ────────────────────────
    intent: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured intent extracted by IntentAgent"
    )
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Hard constraints: budget, duration, destination, etc."
    )

    # ── Stage 2: Accommodation Agent Output ─────────────────
    accommodation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Selected accommodation with coordinates (base camp for routing)"
    )
    accommodation_alternatives: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative accommodation options"
    )

    # ── Stage 3: Research Agent Output ──────────────────────
    candidates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Activities, distances, neighborhoods from ResearchAgent"
    )

    # ── Stage 4: Ranking Agent Output ───────────────────────
    # (Ranking modifies candidates in-place, curating the list)

    # ── Stage 5: Planner Agent Output ───────────────────────
    plans: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Day-by-day plans from PlannerAgent"
    )
    selected_plan: Dict[str, Any] = Field(
        default_factory=dict,
        description="The selected itinerary (PlannerResult as dict)"
    )

    # ── Stage 6: Optimizer Agent Output ─────────────────────
    optimization_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optimized itinerary from OptimizerAgent"
    )

    # ── Stage 7: Critic Agent Output ────────────────────────
    evaluation_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Critic verdict: pass/fail + violations + suggested fixes"
    )

    # ── Pipeline Metadata ───────────────────────────────────
    current_stage: str = Field(
        default="init",
        description="Current pipeline stage: init|intent|accommodation|research|ranking|planner|optimizer|critic|done|failed"
    )
    completed_stages: List[str] = Field(
        default_factory=list,
        description="List of successfully completed stages"
    )
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Errors encountered during pipeline execution"
    )
    timing: Dict[str, float] = Field(
        default_factory=dict,
        description="Time taken (seconds) by each stage"
    )
    retry_count: int = Field(
        default=0,
        description="Number of optimizer-critic retry loops executed"
    )

    def mark_stage_complete(self, stage: str, duration_seconds: float):
        """Mark a pipeline stage as complete with timing."""
        self.current_stage = stage
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)
        self.timing[stage] = round(duration_seconds, 2)

    def add_error(self, stage: str, error: str):
        """Record an error from a pipeline stage."""
        self.errors.append({
            "stage": stage,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def get_destination(self) -> str:
        """Helper: extract destination from constraints."""
        return self.constraints.get("destination", "")

    def get_duration_days(self) -> int:
        """Helper: extract trip duration."""
        return self.constraints.get("duration_days", 3)

    def get_budget(self) -> float:
        """Helper: extract total budget."""
        return self.constraints.get("budget", 10000)

    def get_party_size(self) -> int:
        """Helper: extract party size."""
        traveler = self.intent.get("traveler", {})
        return traveler.get("count", 1) or 1

    def get_interests(self) -> List[str]:
        """Helper: extract user interests/priorities."""
        preferences = self.intent.get("preferences", {})
        return preferences.get("priorities", [])

    def get_accommodation_coords(self) -> Optional[Dict[str, float]]:
        """Helper: get accommodation coordinates for routing."""
        return self.accommodation.get("coordinates", None)
