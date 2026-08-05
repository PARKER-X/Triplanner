from ai_engine.agent.accommodation_agent.accommodation_agent import AccommodationAgent
from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.core.llm.groq import GroqProvider
from ai_engine.schemas.planning_state import PlanningState

def test_accommodation_agent():
    """Test AccommodationAgent finds hotels for a Mumbai trip"""
    llm = GroqProvider()
    
    # Step 1: Parse intent
    intent_agent = IntentAgent(llm)
    intent_result = intent_agent.run("""
        4 friends want to visit Mumbai for 3 days.
        Budget: ₹15,000.
        Interests: food, culture.
        From Delhi.
    """)
    
    # Step 2: Create state
    state = PlanningState(
        user_goal="Mumbai trip",
        intent=intent_result.model_dump(),
        constraints=intent_result.constraints.model_dump()
    )
    
    # Step 3: Run accommodation agent
    acc_agent = AccommodationAgent(llm)
    result = acc_agent.run(state)
    
    # Print results
    print(f"Selected: {result.selected.name}")
    print(f"Cost: ₹{result.selected.cost_per_night}/night")
    print(f"Type: {result.selected.type}")
    print(f"Budget allocated: ₹{result.budget_allocated}")
    print(f"Alternatives: {len(result.alternatives)}")
    
    # Check state was updated
    assert state.accommodation, "State should have accommodation"
    assert state.accommodation.get('name'), "Accommodation should have name"
    assert state.accommodation.get('coordinates'), "Should have coordinates"
    
    # Check budget
    assert result.budget_allocated > 0, "Should allocate budget"
    assert result.budget_per_night > 0, "Should have per-night budget"
    assert result.selected.cost_per_night <= result.budget_per_night + 1, "Should be within budget"
    
    print("\n✅ Accommodation Agent test passed!")

if __name__ == "__main__":
    test_accommodation_agent()
