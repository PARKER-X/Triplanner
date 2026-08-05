from ai_engine.agent.critic_agent.critic_agent import CriticAgent
from ai_engine.schemas.planning_state import PlanningState

def test_critic_passes_valid_plan():
    """Test CriticAgent passes a valid plan"""
    
    valid_plan = {
        "days": [
            {
                "day_number": 1,
                "total_cost": 2000,
                "total_walking_km": 8.0,
                "activities": [
                    {
                        "activity_name": "Gateway of India",
                        "category": "monument",
                        "time_start": "09:00",
                        "time_end": "10:00",
                        "cost_per_person": 0,
                        "duration_minutes": 60
                    },
                    {
                        "activity_name": "Lunch at Leopold",
                        "category": "restaurant",
                        "time_start": "12:00",
                        "time_end": "13:30",
                        "cost_per_person": 500,
                        "duration_minutes": 90
                    },
                    {
                        "activity_name": "Museum",
                        "category": "museum",
                        "time_start": "14:00",
                        "time_end": "16:00",
                        "cost_per_person": 300,
                        "duration_minutes": 120
                    }
                ]
            },
            {
                "day_number": 2,
                "total_cost": 1500,
                "total_walking_km": 6.0,
                "activities": [
                    {
                        "activity_name": "Marine Drive",
                        "category": "viewpoint",
                        "time_start": "09:30",
                        "time_end": "10:30",
                        "cost_per_person": 0,
                        "duration_minutes": 60
                    },
                    {
                        "activity_name": "Cafe Visit",
                        "category": "cafe",
                        "time_start": "11:00",
                        "time_end": "12:00",
                        "cost_per_person": 200,
                        "duration_minutes": 60
                    }
                ]
            }
        ]
    }
    
    state = PlanningState(
        user_goal="Test",
        constraints={"budget": 15000, "destination": "Mumbai", "duration_days": 2},
        optimization_result=valid_plan
    )
    
    critic = CriticAgent()
    verdict = critic.run(state)
    
    print(f"\nVerdict: {verdict.summary}")
    print(f"Passed: {verdict.passed}")
    print(f"Score: {verdict.overall_score:.2f}")
    print(f"Violations: {verdict.total_violations}")
    for v in verdict.violations:
        print(f"  [{v.severity}] {v.rule}: {v.details}")
    
    assert verdict.passed, f"Valid plan should pass critic, got: {verdict.summary}"
    assert verdict.overall_score > 0.5, "Score should be reasonable"
    
    print("\n✅ Critic (valid plan) test passed!")


def test_critic_catches_budget_overflow():
    """Test CriticAgent catches over-budget plans"""
    
    expensive_plan = {
        "days": [
            {
                "day_number": 1,
                "total_cost": 20000,  # Way over budget
                "total_walking_km": 5.0,
                "activities": [
                    {
                        "activity_name": "Expensive Tour",
                        "category": "tour",
                        "time_start": "10:00",
                        "time_end": "15:00",
                        "cost_per_person": 5000,
                        "duration_minutes": 300
                    },
                    {
                        "activity_name": "Fancy Dinner",
                        "category": "restaurant",
                        "time_start": "19:00",
                        "time_end": "21:00",
                        "cost_per_person": 3000,
                        "duration_minutes": 120
                    }
                ]
            }
        ]
    }
    
    state = PlanningState(
        user_goal="Test",
        constraints={"budget": 5000, "destination": "Mumbai", "duration_days": 1},
        optimization_result=expensive_plan
    )
    
    critic = CriticAgent()
    verdict = critic.run(state)
    
    print(f"\nVerdict: {verdict.summary}")
    budget_violations = [v for v in verdict.violations if v.rule == 'budget_check']
    print(f"Budget violations: {len(budget_violations)}")
    
    assert not verdict.passed, "Over-budget plan should fail"
    assert len(budget_violations) > 0, "Should catch budget overflow"
    
    print("\n✅ Critic (budget overflow) test passed!")


def test_critic_catches_empty_day():
    """Test CriticAgent catches empty days"""
    
    empty_plan = {
        "days": [
            {
                "day_number": 1,
                "total_cost": 0,
                "total_walking_km": 0,
                "activities": []  # Empty!
            }
        ]
    }
    
    state = PlanningState(
        user_goal="Test",
        constraints={"budget": 15000, "destination": "Mumbai", "duration_days": 1},
        optimization_result=empty_plan
    )
    
    critic = CriticAgent()
    verdict = critic.run(state)
    
    print(f"\nVerdict: {verdict.summary}")
    empty_violations = [v for v in verdict.violations if v.rule == 'empty_day_check']
    
    assert not verdict.passed, "Empty day should fail critic"
    assert len(empty_violations) > 0, "Should catch empty day"
    
    print("\n✅ Critic (empty day) test passed!")


if __name__ == "__main__":
    test_critic_passes_valid_plan()
    test_critic_catches_budget_overflow()
    test_critic_catches_empty_day()
