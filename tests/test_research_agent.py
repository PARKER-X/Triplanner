from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.agent.research_agent.research_agent import ResearchAgent
from ai_engine.core.llm.groq import GroqProvider
from ai_engine.schemas.planning_state import PlanningState


def test_research_agent():
    """Test Research Agent with free APIs"""
    
    llm = GroqProvider()
    
    print("\n" + "="*80)
    print("TESTING RESEARCH AGENT WITH FREE APIs")
    print("="*80)
    
    # Step 1: Parse intent
    print("\n[1/2] Parsing Intent...")
    intent_agent = IntentAgent(llm)
    intent_result = intent_agent.run("""
        4 friends want to visit Mumbai for 3 days.
        Budget: ₹15,000 (₹3750 per person).
        Interests: food, culture, relaxation.
        From Delhi.
    """)
    
    print(f"✅ Parsed:")
    print(f"   Destination: {intent_result.constraints.destination}")
    print(f"   Budget: ₹{intent_result.constraints.budget}")
    print(f"   Duration: {intent_result.constraints.duration_days} days")
    print(f"   Interests: {intent_result.preferences.priorities}")
    
    # Step 2: Create planning state
    planning_state = PlanningState(
        user_goal="Mumbai trip for 4 friends",
        intent=intent_result.model_dump(),
        constraints=intent_result.constraints.model_dump(),
        candidates=[],
        plans=[],
        selected_plan={},
        evulation_results={}
    )
    
    # Step 3: Research
    print("\n[2/2] Researching Activities (Using Free APIs)...")
    
    try:
        research_agent = ResearchAgent(llm=llm)
        research_result = research_agent.run(planning_state)
        
        # Display results
        print(f"\n✅ Research Complete!")
        print(f"   Total activities found: {research_result.total_activities_found}")
        print(f"   Feasible activities: {research_result.feasible_activities}")
        
        print(f"\n📊 Budget Coverage:")
        for cost_type, count in research_result.budget_coverage.items():
            if count > 0:
                print(f"   {cost_type}: {count}")
        
        print(f"\n🎯 Interest Coverage:")
        for interest, coverage in research_result.interest_coverage.items():
            print(f"   {interest}: {coverage}%")
        
        print(f"\n🏛️ Sample Activities (first 5):")
        for i, activity in enumerate(research_result.activities[:5], 1):
            print(f"\n   {i}. {activity.name}")
            print(f"      Category: {activity.category}")
            print(f"      Cost: ₹{activity.cost_per_person_inr}/person ({activity.cost_type})")
            print(f"      Duration: {activity.duration_minutes} minutes")
            matches = ', '.join(activity.matches_interests) if activity.matches_interests else 'general'
            print(f"      Matches: {matches}")
            print(f"      Rating: {activity.rating}/5")
            print(f"      Area: {activity.area if activity.area else 'Mumbai'}")
            print(f"      Address: {activity.address[:60] if activity.address else 'N/A'}...")
        
        # FIXED: Handle dict access properly
        print(f"\n📍 Distance Matrix (first 5 pairs):")
        grounding_distances = research_result.grounding.distances
        
        for i, dist in enumerate(grounding_distances[:5], 1):
            # dist is a dict, not an object
            if isinstance(dist, dict):
                from_id = dist.get("from_activity", "")
                to_id = dist.get("to_activity", "")
                distance_km = dist.get("distance_km", 0)
                travel_time = dist.get("travel_time_minutes", 0)
            else:
                from_id = dist.from_activity
                to_id = dist.to_activity
                distance_km = dist.distance_km
                travel_time = dist.travel_time_minutes
            
            print(f"\n   {i}. {from_id} ↔ {to_id}")
            print(f"      Distance: {distance_km} km")
            print(f"      Travel time: {travel_time} minutes")
        
        print(f"\n🏘️ Neighborhoods (top 5):")
        neighborhoods = research_result.grounding.neighborhoods
        for area, data in list(neighborhoods.items())[:5]:
            print(f"\n   {area}")
            print(f"      Activities: {data['activities_count']}")
            categories = ', '.join(data['categories'][:3])
            print(f"      Categories: {categories}")
        
        # Summary statistics
        print(f"\n📈 Summary Statistics:")
        print(f"   Total distance pairs calculated: {len(research_result.grounding.distances)}")
        print(f"   Total neighborhoods: {len(neighborhoods)}")
        print(f"   Activities by cost type:")
        for cost_type, count in research_result.budget_coverage.items():
            if count > 0:
                percentage = (count / research_result.feasible_activities) * 100
                print(f"      {cost_type}: {count} ({percentage:.1f}%)")
        
        print("\n" + "="*80)
        print("✅ TEST PASSED - Research Agent Working with Real APIs!")
        print("="*80 + "\n")
        
        # Assertions
        assert research_result.total_activities_found > 0, "Should find activities"
        assert research_result.feasible_activities > 0, "Should have feasible activities"
        assert len(research_result.activities) > 0, "Should have activities in result"
        assert len(research_result.grounding.distances) > 0, "Should calculate distances"
        assert len(research_result.grounding.neighborhoods) > 0, "Should have neighborhoods"
        
        print("✅ All assertions passed!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_research_agent()