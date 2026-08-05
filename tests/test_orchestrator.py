from ai_engine.core.orchestrator import Orchestrator
from ai_engine.core.llm.groq import GroqProvider


def test_full_pipeline():
    """Test complete orchestrator pipeline end-to-end"""
    
    print("\n" + "=" * 100)
    print("FULL PIPELINE TEST: 7-Stage Orchestrator")
    print("=" * 100)
    
    llm = GroqProvider()
    orchestrator = Orchestrator(llm=llm, verbose=True)
    
    state = orchestrator.run("""
        4 friends from Delhi want a 3-day trip to Mumbai.
        Budget: ₹15,000 total.
        We want authentic food experiences, famous cultural sites.
        We prefer iconic attractions over generic free parks.
    """)
    
    # Check pipeline completed
    print(f"\n📊 Pipeline Result:")
    print(f"  Stage: {state.current_stage}")
    print(f"  Completed stages: {state.completed_stages}")
    print(f"  Errors: {len(state.errors)}")
    print(f"  Timing: {state.timing}")
    
    # Assertions
    assert state.current_stage == "done" or state.current_stage == "critic", \
        f"Pipeline should complete, got: {state.current_stage}"
    assert "intent" in state.completed_stages, "Should complete intent stage"
    assert state.get_destination(), "Should have destination"
    assert state.get_budget() > 0, "Should have budget"
    
    # Check accommodation
    if state.accommodation:
        print(f"\n  🏨 Accommodation: {state.accommodation.get('name', 'N/A')}")
    
    # Check plan exists
    if state.selected_plan:
        days = state.selected_plan.get('days', [])
        print(f"  📅 Plan days: {len(days)}")
        for day in days:
            print(f"    Day {day.get('day_number')}: {len(day.get('activities', []))} activities")
    
    # Check critic verdict
    if state.evaluation_results:
        print(f"  🔍 Critic: {state.evaluation_results.get('summary', 'N/A')}")
    
    print("\n✅ Full pipeline test completed!")


if __name__ == "__main__":
    test_full_pipeline()
