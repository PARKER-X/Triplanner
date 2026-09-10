"""
Orchestrator — The conductor of the agent pipeline.

Controls workflow, agent execution order, retries, and failures.
The orchestrator does NOT make plans or decide answers — agents do that.

Pipeline:
  Intent → Accommodation → Research → Ranking → Planner → Optimizer → Critic
  (with critic-optimizer retry loop, max 2 retries)
"""

import time
from typing import Optional

from ai_engine.schemas.planning_state import PlanningState
from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.agent.accommodation_agent.accommodation_agent import AccommodationAgent
from ai_engine.agent.research_agent.research_agent import ResearchAgent
from ai_engine.agent.ranking_agent.ranking_agent import RankingAgent
from ai_engine.agent.planner_agent.planner_agent import PlannerAgent
from ai_engine.agent.optimizer_agent.optimizer_agent import OptimizerAgent
from ai_engine.agent.critic_agent.critic_agent import CriticAgent


class Orchestrator:
    """
    Orchestrator — Runs the 7-stage trip planning pipeline.

    Each stage:
    1. Reads from PlanningState
    2. Executes agent
    3. Writes results to PlanningState
    4. Logs timing
    5. Handles errors gracefully
    """

    MAX_CRITIC_RETRIES = 2

    def __init__(self, llm, verbose: bool = True):
        """
        Initialize all agents.

        Args:
            llm: LLM provider instance (GroqProvider, GeminiProvider, etc.)
            verbose: Print detailed status messages
        """
        self.llm = llm
        self.verbose = verbose

        self._log("🚀 Initializing AI Trip Planner Pipeline...")

        # LLM-using agents
        self.intent_agent = IntentAgent(llm)
        self.accommodation_agent = AccommodationAgent(llm)
        self.research_agent = ResearchAgent(llm)

        # Algorithmic agents (no LLM)
        self.ranking_agent = RankingAgent()
        self.planner_agent = PlannerAgent(llm)
        self.optimizer_agent = OptimizerAgent()
        self.critic_agent = CriticAgent()

        self._log("✅ All 7 agents initialized\n")

    def run(self, user_query: str) -> PlanningState:
        """
        Execute the full planning pipeline.

        Args:
            user_query: Natural language trip request

        Returns:
            PlanningState with complete itinerary
        """
        pipeline_start = time.time()

        self._log("\n" + "=" * 80)
        self._log("🌍 AI TRIP PLANNER — Starting Pipeline")
        self._log("=" * 80)
        self._log(f"📝 Query: {user_query[:100]}...")

        # Create initial state
        state = PlanningState(user_goal=user_query)

        # ── Stage 1: Intent ────────────────────────────────
        state = self._run_stage(state, "intent", self._stage_intent)

        # Check if we have a valid destination
        if not state.get_destination():
            state.add_error("intent", "No destination found in user query")
            state.current_stage = "failed"
            self._log("❌ Pipeline failed: No destination found")
            return state

        # ── Stage 2: Accommodation ─────────────────────────
        if state.get_duration_days() > 1:
            state = self._run_stage(state, "accommodation", self._stage_accommodation)
        else:
            self._log("⏭️ Skipping accommodation (day trip)")

        # ── Stage 3: Research ──────────────────────────────
        state = self._run_stage(state, "research", self._stage_research)

        # Warn if research came back empty, but don't abort — let planner handle it gracefully
        if not state.candidates.get("activities"):
            state.add_error("research", "No activities found — pipeline will continue with limited data")
            self._log("⚠️ Research returned 0 activities; continuing pipeline with best-effort data")

        # ── Stage 4: Ranking ───────────────────────────────
        state = self._run_stage(state, "ranking", self._stage_ranking)

        # ── Stage 5: Planner ───────────────────────────────
        state = self._run_stage(state, "planner", self._stage_planner)

        # ── Stage 6 & 7: Optimizer + Critic (with retry loop)
        state = self._optimizer_critic_loop(state)

        # ── Done ───────────────────────────────────────────
        total_time = time.time() - pipeline_start
        state.timing["total"] = round(total_time, 2)
        state.current_stage = "done"

        self._log("\n" + "=" * 80)
        self._log("✅ PIPELINE COMPLETE")
        self._log(f"   Total time: {total_time:.1f}s")
        self._log(f"   Stages completed: {len(state.completed_stages)}")
        self._log(f"   Errors: {len(state.errors)}")
        if state.evaluation_results:
            self._log(f"   Critic verdict: {state.evaluation_results.get('summary', 'N/A')}")
        self._log("=" * 80 + "\n")

        return state

    # ─── Stage Implementations ──────────────────────────────

    def _stage_intent(self, state: PlanningState) -> PlanningState:
        """Stage 1: Parse user intent."""
        intent_result = self.intent_agent.run(state.user_goal)

        state.intent = intent_result.model_dump()
        state.constraints = intent_result.constraints.model_dump()

        self._log(f"   Destination: {state.get_destination()}")
        self._log(f"   Duration: {state.get_duration_days()} days")
        self._log(f"   Budget: ₹{state.get_budget()}")
        self._log(f"   Party: {state.get_party_size()} people")
        self._log(f"   Interests: {state.get_interests()}")

        return state

    def _stage_accommodation(self, state: PlanningState) -> PlanningState:
        """Stage 2: Find accommodation."""
        self.accommodation_agent.run(state)

        if state.accommodation:
            name = state.accommodation.get("name", "Unknown")
            cost = state.accommodation.get("cost_per_night", 0)
            self._log(f"   Selected: {name} (₹{cost}/night)")
        else:
            self._log("   ⚠️ No accommodation found, using fallback")

        return state

    def _stage_research(self, state: PlanningState) -> PlanningState:
        """Stage 3: Research real activities."""
        self.research_agent.run(state)

        count = len(state.candidates.get("activities", []))
        self._log(f"   Found {count} activities")

        return state

    def _stage_ranking(self, state: PlanningState) -> PlanningState:
        """Stage 4: Rank and curate activities."""
        self.ranking_agent.run(state)

        count = len(state.candidates.get("activities", []))
        self._log(f"   Curated to {count} activities")

        return state

    def _stage_planner(self, state: PlanningState) -> PlanningState:
        """Stage 5: Create day-by-day itinerary."""
        result = self.planner_agent.run(state)

        if result:
            self._log(f"   Created {len(result.days)}-day itinerary")
            self._log(f"   Total activities: {result.stats.total_activities}")
            self._log(f"   Total cost: ₹{result.stats.total_cost:.0f}")

        return state

    def _optimizer_critic_loop(self, state: PlanningState) -> PlanningState:
        """Stages 6 & 7: Optimize + Validate with retry loop."""

        for attempt in range(1, self.MAX_CRITIC_RETRIES + 2):  # +2 for initial + retries
            # Stage 6: Optimize
            state = self._run_stage(state, "optimizer", self._stage_optimizer)

            # Stage 7: Validate
            state = self._run_stage(state, "critic", self._stage_critic)

            # Check verdict
            verdict = state.evaluation_results
            if verdict.get("passed", True):
                self._log(f"   ✅ Critic PASSED (attempt {attempt})")
                break
            else:
                state.retry_count += 1
                if attempt <= self.MAX_CRITIC_RETRIES:
                    self._log(f"   🔄 Critic FAILED, retrying... (attempt {attempt}/{self.MAX_CRITIC_RETRIES + 1})")
                else:
                    self._log(f"   ⚠️ Critic FAILED after {attempt} attempts, proceeding with best effort")

        return state

    def _stage_optimizer(self, state: PlanningState) -> PlanningState:
        """Stage 6: Two-stage optimization."""
        result = self.optimizer_agent.run(state)

        self._log(f"   Swaps: {result.stats.total_swaps}")
        self._log(f"   Score improvement: {result.stats.score_improvement_pct:.1f}%")

        return state

    def _stage_critic(self, state: PlanningState) -> PlanningState:
        """Stage 7: Validate plan."""
        verdict = self.critic_agent.run(state)

        self._log(f"   {verdict.summary}")

        return state

    # ─── Utilities ──────────────────────────────────────────

    def _run_stage(self, state: PlanningState, stage_name: str, stage_fn) -> PlanningState:
        """
        Run a pipeline stage with timing and error handling.
        """
        self._log(f"\n{'─' * 60}")
        self._log(f"📌 Stage: {stage_name.upper()}")
        self._log(f"{'─' * 60}")

        start_time = time.time()

        try:
            state = stage_fn(state)
            duration = time.time() - start_time
            state.mark_stage_complete(stage_name, duration)
            self._log(f"   ⏱️  Completed in {duration:.1f}s")

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)[:200]}"
            state.add_error(stage_name, error_msg)
            state.timing[stage_name] = round(duration, 2)
            self._log(f"   ❌ Error in {stage_name}: {error_msg}")

        return state

    def _log(self, message: str):
        """Print log message if verbose mode is on."""
        if self.verbose:
            print(message)