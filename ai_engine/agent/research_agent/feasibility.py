from typing import Dict, List


class FeasibilityScorer:
    """Score feasibility of options"""
    
    def __init__(self):
        self.weights = {
            "budget_match": 0.4,
            "time_feasibility": 0.3,
            "group_suitability": 0.2,
            "logistics": 0.1
        }
    
    def score_place(self, place: Dict, constraints: Dict, preferences: Dict) -> float:
        """
        Score a place option
        Returns 0-1 score
        """
        budget_match = self._score_budget(
            place.get("cost_per_person", 0),
            constraints.get("budget", 10000),
            constraints.get("duration_days", 3)
        )
        time_feasibility = self._score_time(
            place.get("duration_hours", 1),
            constraints.get("duration_days", 3)
        )
        group_suitability = self._score_group(place, constraints.get("party_size", 4))
        logistics = self._score_logistics(place, constraints.get("source"))
        
        score = (
            budget_match * self.weights["budget_match"] +
            time_feasibility * self.weights["time_feasibility"] +
            group_suitability * self.weights["group_suitability"] +
            logistics * self.weights["logistics"]
        )
        
        return min(1.0, max(0.0, score))
    
    def score_activity(self, activity: Dict, constraints: Dict, preferences: Dict) -> float:
        """Score an activity option"""
        budget_match = self._score_budget(
            activity.get("cost_per_person", 0),
            constraints.get("budget", 10000),
            constraints.get("duration_days", 3)
        )
        time_feasibility = self._score_time(
            activity.get("duration_hours", 2),
            constraints.get("duration_days", 3)
        )
        group_suitability = self._score_group(activity, constraints.get("party_size", 4))
        preference_match = self._score_preference_match(activity, preferences)
        
        score = (
            budget_match * self.weights["budget_match"] +
            time_feasibility * self.weights["time_feasibility"] +
            group_suitability * self.weights["group_suitability"] +
            preference_match * self.weights["logistics"]
        )
        
        return min(1.0, max(0.0, score))
    
    def score_accommodation(self, accommodation: Dict, constraints: Dict) -> float:
        """Score accommodation option"""
        budget_match = self._score_budget_accommodation(accommodation, constraints)
        capacity_match = self._score_capacity(accommodation, constraints.get("party_size", 4))
        location_convenience = accommodation.get("location_convenience", 0.7)
        
        score = (
            budget_match * 0.5 +
            capacity_match * 0.3 +
            location_convenience * 0.2
        )
        
        return min(1.0, max(0.0, score))
    
    def _score_budget(self, cost_per_person: float, total_budget: float, duration: int) -> float:
        """
        Score budget feasibility
        Cost should be <10% of total budget per activity
        """
        if cost_per_person == 0:
            return 1.0
        
        max_per_activity = total_budget * 0.1
        if cost_per_person > max_per_activity:
            return 0.0
        
        return 1.0 - (cost_per_person / max_per_activity) * 0.3
    
    def _score_time(self, duration_hours: float, total_days: int) -> float:
        """
        Score time feasibility
        Activity should not exceed 1/3 of day
        """
        hours_per_day = 12  # Assuming 12 hours active time per day
        max_activity_hours = hours_per_day / 3
        
        if duration_hours > max_activity_hours:
            return 0.3
        
        return 1.0 - (duration_hours / max_activity_hours) * 0.2
    
    def _score_group(self, option: Dict, group_size: int) -> float:
        """Score group suitability"""
        if option.get("group_friendly") == False:
            return 0.5
        if option.get("group_friendly") == True:
            return 1.0
        return 0.7
    
    def _score_logistics(self, place: Dict, source: str = None) -> float:
        """
        Score logistics feasibility
        E.g., is it accessible, do we need transport, etc.
        """
        # Default to good logistics
        return 0.8
    
    def _score_preference_match(self, option: Dict, preferences: Dict) -> float:
        """Score how well option matches user preferences"""
        user_priorities = preferences.get("priorities", [])
        option_matches = option.get("matches_priorities", [])
        
        if not user_priorities:
            return 0.7
        
        matching = len([p for p in user_priorities if p in option_matches])
        coverage = matching / len(user_priorities) if user_priorities else 0
        return min(1.0, coverage)
    
    def _score_budget_accommodation(self, accommodation: Dict, constraints: Dict) -> float:
        """Score accommodation budget"""
        nights = constraints.get("duration_days", 3)
        party_size = constraints.get("party_size", 4)
        total_budget = constraints.get("budget", 10000)
        
        max_budget_accommodation = total_budget * 0.25 / nights
        cost_per_night = accommodation.get("cost_per_night", 0)
        
        if cost_per_night > max_budget_accommodation:
            return 0.4
        
        return 1.0 - (cost_per_night / max_budget_accommodation) * 0.3
    
    def _score_capacity(self, accommodation: Dict, group_size: int) -> float:
        """Score accommodation capacity fit"""
        capacity = accommodation.get("capacity", 2)
        
        if capacity == group_size:
            return 1.0
        if capacity >= group_size:
            return 0.9
        if capacity >= group_size - 1:
            return 0.7
        return 0.3
    
    def get_why_selected_message(self, option: Dict, scores: Dict) -> str:
        """Generate "why selected" message"""
        name = option.get("name", "Option")
        score = scores.get("feasibility_score", 0)
        
        if score > 0.85:
            return f"{name} - Excellent fit for budget and preferences"
        elif score > 0.70:
            return f"{name} - Good choice within constraints"
        else:
            return f"{name} - Viable option with some tradeoffs"


class BudgetCalculator:
    """Calculate and optimize budget"""
    
    @staticmethod
    def calculate_breakdown(
        transport_cost: float,
        accommodation_cost: float,
        activities_cost: float,
        food_budget: float,
        local_transport: float,
        total_budget: float,
        party_size: int
    ) -> Dict:
        """Calculate realistic budget breakdown"""
        
        total_spent = (
            transport_cost +
            accommodation_cost +
            activities_cost +
            food_budget +
            local_transport
        )
        
        contingency = max(0, total_budget - total_spent)
        
        return {
            "transport_delhi_mumbai": transport_cost,
            "accommodation": accommodation_cost,
            "activities": activities_cost,
            "food": food_budget,
            "local_transport": local_transport,
            "contingency": contingency,
            "total": total_budget,
            "per_person": total_budget / party_size if party_size > 0 else 0,
            "buffer_remaining": contingency
        }
    
    @staticmethod
    def is_feasible_budget(breakdown: Dict, total_budget: float) -> tuple:
        """Check if budget is feasible"""
        total_spent = breakdown.get("total", 0) - breakdown.get("buffer_remaining", 0)
        
        if total_spent > total_budget:
            shortfall = total_spent - total_budget
            return False, f"Budget short by ₹{shortfall:.0f}"
        
        if breakdown.get("buffer_remaining", 0) < total_budget * 0.05:
            return True, f"Tight budget, only ₹{breakdown.get('buffer_remaining', 0):.0f} buffer"
        
        return True, f"Comfortable budget with ₹{breakdown.get('buffer_remaining', 0):.0f} buffer"