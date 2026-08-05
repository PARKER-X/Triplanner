from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.agent.research_agent.research_agent import ResearchAgent
from ai_engine.agent.ranking_agent.ranking_agent import RankingAgent
from ai_engine.agent.planner_agent.planner_agent import PlannerAgent
from ai_engine.core.llm.groq import GroqProvider
from ai_engine.schemas.planning_state import PlanningState


def test_full_pipeline():
    """Intent → Research → Ranking → Planner (Realistic Version)"""

    llm = GroqProvider()

    print("\n" + "=" * 100)
    print("REALISTIC TRIP PLANNING: Optimized Famous Experience")
    print("=" * 100)

    # ---------------------------
    # STEP 1 — INTENT
    # ---------------------------
    print("\n[1/4] Understanding Travel Goals...")

    intent_agent = IntentAgent(llm)

    intent_result = intent_agent.run("""
        4 friends from Delhi want a 3-day trip to Mumbai.
        Budget: ₹15,000 total.
        We want authentic food experiences, famous cultural sites, and some relaxation.
        We prefer iconic attractions over generic free parks.
    """)

    print(f"✅ Destination: {intent_result.constraints.destination}")
    print(f"✅ Budget: ₹{intent_result.constraints.budget}")
    print(f"✅ Duration: {intent_result.constraints.duration_days} days")
    print(f"✅ Travelers: {intent_result.traveler.count}")
    print(f"✅ Interests: {intent_result.preferences.priorities}")

    # ---------------------------
    # STEP 2 — RESEARCH
    # ---------------------------
    print("\n[2/4] Retrieving Real Activities...")

    planning_state = PlanningState(
        user_goal="Mumbai trip",
        intent=intent_result.model_dump(),
        constraints=intent_result.constraints.model_dump(),
        candidates={},
        plans=[],
        selected_plan={},
        evulation_results={}
    )

    research_agent = ResearchAgent(llm=llm)
    research_result = research_agent.run(planning_state)

    print(f"\n✅ Raw Activities Found: {research_result.total_activities_found}")
    print(f"✅ Feasible Activities: {research_result.feasible_activities}")
    print(f"✅ Interest Coverage: {research_result.interest_coverage}")
    print(f"✅ Budget Coverage: {research_result.budget_coverage}")

    # ---------------------------
    # STEP 3 — RANKING (NEW)
    # ---------------------------
    print("\n[3/4] Curating Famous Experiences (80/15/5 weighting)...")

    ranking_agent = RankingAgent()
    planning_state = ranking_agent.run(planning_state)

    curated_count = len(planning_state.candidates.get("activities", []))
    print(f"✅ Curated Activities for Planning: {curated_count}")

    # ---------------------------
    # STEP 4 — PLANNER
    # ---------------------------
    print("\n[4/4] Creating Optimized Itinerary...")

    planner_agent = PlannerAgent(llm=llm)
    planner_result = planner_agent.run(planning_state)

    # ---------------------------
    # DISPLAY RESULTS
    # ---------------------------

    print(f"\n{'=' * 100}")
    print(planner_result.trip_title.upper())
    print(f"{'=' * 100}\n")

    print(planner_result.trip_summary)

    for day in planner_result.days:
        print(f"\n{'─' * 100}")
        print(f"DAY {day.day_number}: {day.theme}")
        print(f"{'─' * 100}")

        for activity in day.activities:
            cost = f"₹{activity.cost_per_person}" if activity.cost_per_person > 0 else "FREE"

            print(f"\n{activity.time_start} – {activity.activity_name}")
            print(f"  Category: {activity.category}")
            print(f"  Coordinates: {activity.coordinates}")
            print(f"  Cost: {cost}")
            print(f"  Duration: {activity.duration_minutes} mins")
            print(f"  Why: {activity.why_included}")

        print(f"\n  💰 Day Cost: ₹{day.total_cost:.0f}")
        print(f"  🚶 Distance: {day.total_walking_km:.1f} km")

    print(f"\n{'=' * 100}")
    print("TRIP SUMMARY")
    print(f"{'=' * 100}")

    print(f"Total Activities: {planner_result.stats.total_activities}")
    print(f"Total Cost: ₹{planner_result.stats.total_cost:.0f}")
    print(f"Total Walking: {planner_result.stats.total_walking_km:.1f} km")

    if planner_result.warnings:
        print("\n⚠️ Warnings:")
        for w in planner_result.warnings:
            print(f"  {w}")
    else:
        print("\n✅ Within Budget")

    print("\n✅ FULL PIPELINE COMPLETED\n")


if __name__ == "__main__":
    test_full_pipeline()