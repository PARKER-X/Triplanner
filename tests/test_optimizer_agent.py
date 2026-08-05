from ai_engine.agent.optimizer_agent.optimizer_agent import OptimizerAgent
from ai_engine.schemas.planning_state import PlanningState

def test_optimizer_agent():
    """Test OptimizerAgent with synthetic plan data"""
    
    # Create a fake plan with activities that have coordinates
    fake_plan = {
        "trip_title": "Test Trip",
        "trip_summary": "Test summary",
        "destination": "Mumbai",
        "duration_days": 2,
        "days": [
            {
                "day_number": 1,
                "theme": "Cultural Day",
                "total_cost": 500,
                "total_walking_km": 5.0,
                "activities": [
                    {
                        "activity_id": "a1",
                        "activity_name": "Gateway of India",
                        "name": "Gateway of India",
                        "category": "monument",
                        "coordinates": {"lat": 18.922, "lng": 72.835},
                        "location": "Colaba",
                        "address": "Apollo Bunder",
                        "cost_per_person": 0,
                        "duration_minutes": 60,
                        "description": "Iconic arch monument",
                        "why_included": "Famous landmark",
                        "rating": 4.5
                    },
                    {
                        "activity_id": "a2",
                        "activity_name": "Chhatrapati Shivaji Museum",
                        "name": "Chhatrapati Shivaji Museum",
                        "category": "museum",
                        "coordinates": {"lat": 18.927, "lng": 72.832},
                        "location": "Fort",
                        "address": "Fort Area",
                        "cost_per_person": 300,
                        "duration_minutes": 120,
                        "description": "Major museum",
                        "why_included": "Cultural experience",
                        "rating": 4.3
                    },
                    {
                        "activity_id": "a3",
                        "activity_name": "Marine Drive",
                        "name": "Marine Drive",
                        "category": "viewpoint",
                        "coordinates": {"lat": 18.944, "lng": 72.824},
                        "location": "Churchgate",
                        "address": "Netaji Subhash Road",
                        "cost_per_person": 0,
                        "duration_minutes": 45,
                        "description": "Scenic promenade",
                        "why_included": "Iconic viewpoint",
                        "rating": 4.7
                    }
                ]
            },
            {
                "day_number": 2,
                "theme": "Food Day",
                "total_cost": 800,
                "total_walking_km": 3.0,
                "activities": [
                    {
                        "activity_id": "a4",
                        "activity_name": "Leopold Cafe",
                        "name": "Leopold Cafe",
                        "category": "cafe",
                        "coordinates": {"lat": 18.923, "lng": 72.832},
                        "location": "Colaba",
                        "address": "Colaba Causeway",
                        "cost_per_person": 400,
                        "duration_minutes": 90,
                        "description": "Iconic cafe",
                        "why_included": "Famous food spot",
                        "rating": 4.2
                    },
                    {
                        "activity_id": "a5",
                        "activity_name": "Elephanta Caves",
                        "name": "Elephanta Caves",
                        "category": "monument",
                        "coordinates": {"lat": 18.964, "lng": 72.932},
                        "location": "Elephanta Island",
                        "address": "Elephanta Island",
                        "cost_per_person": 500,
                        "duration_minutes": 180,
                        "description": "UNESCO site",
                        "why_included": "World heritage",
                        "rating": 4.6
                    }
                ]
            }
        ],
        "stats": {"total_activities": 5, "total_cost": 1300, "total_walking_km": 8.0},
        "highlights": [],
        "tips": [],
        "warnings": []
    }
    
    state = PlanningState(
        user_goal="Test trip",
        constraints={"budget": 15000, "duration_days": 2, "destination": "Mumbai"},
        selected_plan=fake_plan
    )
    
    optimizer = OptimizerAgent()
    result = optimizer.run(state)
    
    print(f"\nOptimization Result:")
    print(f"  Total score: {result.total_score:.3f}")
    print(f"  Total swaps: {result.stats.total_swaps}")
    print(f"  Score improvement: {result.stats.score_improvement_pct:.1f}%")
    print(f"  Intra-day time: {result.stats.intra_day_time_ms:.1f}ms")
    print(f"  Inter-day time: {result.stats.inter_day_time_ms:.1f}ms")
    print(f"  Is feasible: {result.is_feasible}")
    
    for day in result.days:
        print(f"\n  Day {day.day_number}: {day.theme}")
        for act in day.activities:
            print(f"    {act.time_start} — {act.activity_name}")
    
    # Assertions
    assert result.is_feasible, "Result should be feasible"
    assert len(result.days) == 2, "Should have 2 days"
    assert result.total_score > 0, "Should have positive score"
    assert state.optimization_result, "State should have optimization_result"
    
    # Check time windows
    for day in result.days:
        for act in day.activities:
            hour = int(act.time_start.split(':')[0])
            assert 7 <= hour <= 21, f"Activity should be within time window: {act.time_start}"
    
    print("\n✅ Optimizer Agent test passed!")

if __name__ == "__main__":
    test_optimizer_agent()
