from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.agent.research_agent.research_agent import ResearchAgent
from ai_engine.agent.planner_agent.planner_agent import PlannerAgent
from ai_engine.core.llm.groq import GroqProvider
from ai_engine.schemas.planning_state import PlanningState

def test_full_pipeline():
    """Test Intent → Research → Planner with REAL output"""
    
    llm = GroqProvider()
    
    print("\n" + "="*100)
    print("REALISTIC TRIP PLANNING: What Users Actually Want")
    print("="*100)
    
    # Step 1: Intent
    print("\n[1/3] Understanding Your Travel Goals...")
    intent_agent = IntentAgent(llm)
    intent_result = intent_agent.run("""
        4 friends from Delhi want a 3-day trip to Mumbai.
        Budget: ₹15,000 (₹3,750 per person).
        We want: authentic food experiences, famous cultural sites, and some relaxation.
        We want to visit real attractions, not just free parks.
    """)
    
    print(f"✅ Understood Your Needs:")
    print(f"   📍 Destination: {intent_result.constraints.destination}")
    print(f"   💰 Budget: ₹{intent_result.constraints.budget}")
    print(f"   ⏱️  Duration: {intent_result.constraints.duration_days} days")
    print(f"   👥 Travelers: {intent_result.traveler.count}")
    print(f"   🎯 Interests: {', '.join(intent_result.preferences.priorities)}")
    
    # Step 2: Research
    print("\n[2/3] Researching Best Places for You...")
    planning_state = PlanningState(
        user_goal="Mumbai trip",
        intent=intent_result.model_dump(),
        constraints=intent_result.constraints.model_dump(),
        candidates=[],
        plans=[],
        selected_plan={},
        evulation_results={}
    )
    
    research_agent = ResearchAgent(llm=llm)
    research_result = research_agent.run(planning_state)
    
    print(f"\n✅ Found {research_result.feasible_activities} suitable activities:")
    print(f"   🍽️  Food experiences: {research_result.interest_coverage.get('food', 0):.0f}%")
    print(f"   🏛️  Cultural sites: {research_result.interest_coverage.get('culture', 0):.0f}%")
    print(f"   🌳 Relaxation spots: {research_result.interest_coverage.get('relaxation', 0):.0f}%")
    print(f"   💵 Budget distribution:")
    for cost_type, count in research_result.budget_coverage.items():
        if count > 0:
            print(f"      - {cost_type.capitalize()}: {count} places")
    
    # Step 3: Planner
    print("\n[3/3] Creating Your Perfect Itinerary...")
    planner_agent = PlannerAgent(llm=llm)
    planner_result = planner_agent.run(planning_state)
    
    # Display results
    print(f"\n{'='*100}")
    print(planner_result.trip_title.upper())
    print(f"{'='*100}\n")
    
    print(f"{planner_result.trip_summary}\n")
    
    # Show each day with explanations
    for day in planner_result.days:
        print(f"\n{'─'*100}")
        print(f"DAY {day.day_number}: {day.theme}")
        print(f"{'─'*100}\n")
        
        print(f"SCHEDULE:")
        for activity in day.activities:
            icon = "🍽️" if "food" in activity.category else "🏛️" if "culture" in activity.category else "🌳"
            cost_str = f"₹{activity.cost_per_person}" if activity.cost_per_person > 0 else "FREE"
            
            print(f"\n{activity.time_start} – {activity.activity_name}")
            print(f"  {icon} {activity.category.upper()}")
            print(f"  📍 {activity.location}")
            print(f"  💰 {cost_str} per person")
            print(f"  ⏱️  {activity.duration_minutes} mins")
            print(f"  ✨ {activity.why_included}")
        
        print(f"\nMEALS:")
        for meal in day.meals:
            print(f"  {meal.time} – {meal.type.upper()}: {meal.restaurant_name} (₹{meal.cost_per_person})")
        
        print(f"\nDAY SUMMARY:")
        print(f"  💰 Total Cost: ₹{day.total_cost:.0f}")
        print(f"  🚶 Walking Distance: {day.total_walking_km:.1f} km")
        print(f"  😴 Rest Time: {day.rest_hours:.1f} hours")
    
    # Final summary
    print(f"\n{'='*100}")
    print("YOUR 3-DAY ADVENTURE - SUMMARY")
    print(f"{'='*100}\n")
    
    print(f"📊 What You'll Experience:")
    print(f"   {planner_result.stats.total_activities} carefully chosen attractions")
    print(f"   {planner_result.stats.free_activities} free experiences + {planner_result.stats.paid_activities} paid attractions")
    print(f"   {planner_result.stats.total_walking_km:.0f} km of walking (realistic daily exploration)")
    print(f"   ₹{planner_result.stats.total_cost:.0f} total cost (₹{planner_result.stats.average_daily_cost:.0f}/day)\n")
    
    print(f"🌟 Trip Highlights:")
    for highlight in planner_result.highlights:
        print(f"   ✓ {highlight}")
    
    print(f"\n💡 Pro Tips:")
    for tip in planner_result.tips[:4]:
        print(f"   • {tip}")
    
    if planner_result.warnings:
        print(f"\n⚠️  Important Notes:")
        for warning in planner_result.warnings:
            print(f"   {warning}")
    else:
        print(f"\n✅ Everything fits perfectly within your budget!")
    
    print(f"\n{'='*100}")
    print("Ready to book? Your itinerary is ready for reservations!")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    test_full_pipeline()