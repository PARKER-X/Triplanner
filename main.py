"""
AI Trip Planner — Main Entry Point

Usage:
    python main.py
    python main.py --verbose
    python main.py --query "4 friends, 3 days Mumbai, ₹15000"
"""

import sys
import argparse

from ai_engine.core.orchestrator import Orchestrator
from ai_engine.core.llm.groq import GroqProvider


DEFAULT_QUERY = """
4 friends from Delhi want a 3-day trip to Mumbai.
Budget: ₹15,000 total.
We want authentic food experiences, famous cultural sites, and some relaxation.
We prefer iconic attractions over generic free parks.
"""


def display_itinerary(state):
    """Pretty-print the final itinerary from PlanningState."""

    plan = state.optimization_result or state.selected_plan
    if not plan:
        print("❌ No itinerary was generated.")
        return

    # Title
    title = plan.get("trip_title", "Trip Itinerary")
    summary = plan.get("trip_summary", "")

    print("\n" + "═" * 80)
    print(f"  🌍 {title.upper()}")
    print("═" * 80)
    if summary:
        print(f"  {summary}")

    # Days
    days = plan.get("days", [])
    for day in days:
        day_num = day.get("day_number", "?")
        theme = day.get("theme", "")
        total_cost = day.get("total_cost", 0)
        walking = day.get("total_walking_km", 0)

        print(f"\n{'─' * 80}")
        print(f"  DAY {day_num}: {theme}")
        print(f"{'─' * 80}")

        activities = day.get("activities", [])
        for act in activities:
            name = act.get("activity_name", act.get("name", "Unknown"))
            time_start = act.get("time_start", "??:??")
            category = act.get("category", "")
            cost = act.get("cost_per_person", 0)
            duration = act.get("duration_minutes", 60)
            why = act.get("why_included", "")

            cost_str = f"₹{cost}" if cost > 0 else "FREE"

            print(f"\n  {time_start}  {name}")
            print(f"           📂 {category}  |  💰 {cost_str}  |  ⏱️ {duration}min")
            if why:
                print(f"           💡 {why}")

        # Meals
        meals = day.get("meals", [])
        if meals:
            print(f"\n  🍽️ Meals:")
            for meal in meals:
                meal_type = meal.get("type", "meal")
                meal_time = meal.get("time", "")
                restaurant = meal.get("restaurant_name", "")
                meal_cost = meal.get("cost_per_person", 0)
                print(f"     {meal_time}  {meal_type.title()} — {restaurant} (₹{meal_cost}/person)")

        print(f"\n  💰 Day Cost: ₹{total_cost:.0f}  |  🚶 Walking: {walking:.1f}km")

    # Stats
    stats = plan.get("stats", {})
    if stats:
        print(f"\n{'═' * 80}")
        print("  📊 TRIP SUMMARY")
        print(f"{'═' * 80}")
        print(f"  Total Activities: {stats.get('total_activities', 0)}")
        print(f"  Total Cost: ₹{stats.get('total_cost', 0):.0f}")
        print(f"  Total Walking: {stats.get('total_walking_km', 0):.1f}km")
        print(f"  Free Activities: {stats.get('free_activities', 0)}")
        print(f"  Paid Activities: {stats.get('paid_activities', 0)}")

    # Warnings
    warnings = plan.get("warnings", [])
    if warnings:
        print(f"\n  ⚠️ Warnings:")
        for w in warnings:
            print(f"     {w}")

    # Accommodation
    if state.accommodation:
        print(f"\n  🏨 Accommodation: {state.accommodation.get('name', 'N/A')}")
        print(f"     Cost: ₹{state.accommodation.get('cost_per_night', 0)}/night")
        print(f"     Area: {state.accommodation.get('area', 'N/A')}")

    # Critic verdict
    if state.evaluation_results:
        print(f"\n  🔍 Validation: {state.evaluation_results.get('summary', 'N/A')}")

    # Timing
    if state.timing:
        print(f"\n  ⏱️ Pipeline Timing:")
        for stage, duration in state.timing.items():
            print(f"     {stage}: {duration:.1f}s")

    print(f"\n{'═' * 80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI Trip Planner — Multi-Agent Pipeline"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=DEFAULT_QUERY,
        help="Trip planning query"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Print detailed pipeline logs"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Only print final itinerary"
    )

    args = parser.parse_args()

    verbose = not args.quiet

    # Initialize
    print("🚀 Starting AI Trip Planner...\n")
    llm = GroqProvider()
    orchestrator = Orchestrator(llm=llm, verbose=verbose)

    # Run pipeline
    state = orchestrator.run(args.query.strip())

    # Display result
    if state.current_stage == "done":
        display_itinerary(state)
    else:
        print(f"\n❌ Pipeline ended at stage: {state.current_stage}")
        if state.errors:
            print("Errors:")
            for err in state.errors:
                print(f"  [{err['stage']}] {err['error']}")


if __name__ == "__main__":
    main()
