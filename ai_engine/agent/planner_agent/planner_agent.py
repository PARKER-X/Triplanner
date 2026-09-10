"""
Planner Agent - Creates optimized day-by-day itinerary
Based on Google's LLM-based trip planning research

KEY INSIGHT: Activities must be sequenced by location (TSP-like problem)
Travel time between activities is CRITICAL
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

from .schema import DayPlan, DayActivity, Meal, ItineraryStats, PlannerResult
from ..research_agent.schema import Activity


class PlannerAgent:
    """
    Planner Agent - Creates realistic, location-optimized itineraries
    
    Core algorithm:
    1. Get all activities + their distances
    2. For each day: 
       a. Start from hotel/accommodation
       b. Use nearest-neighbor to sequence activities
       c. Calculate actual travel time between each
       d. Fit within day (9 AM - 9 PM)
       e. Respect budgets
    """
    
    def __init__(self, llm):
        """Initialize planner"""
        self.llm = llm
        
        with open("ai_engine/agent/planner_agent/prompt.txt") as f:
            self.prompt = f.read()
        
        print("✅ Planner Agent initialized (with location optimization)")
    
    def run(self, planning_state) -> PlannerResult:
        """Main planner execution"""
        
        print("\n" + "="*80)
        print("📅 PLANNER AGENT: Creating location-optimized itinerary")
        print("="*80)
        
        # Extract data
        intent_dict = planning_state.intent
        constraints_dict = planning_state.constraints
        candidates = planning_state.candidates
        
        destination = constraints_dict.get("destination", "") or ""
        duration_days = constraints_dict.get("duration_days") or 3
        budget = constraints_dict.get("budget") or 10000

        preferences_dict = intent_dict.get("preferences", {})
        interests = preferences_dict.get("priorities") or []

        traveler_dict = intent_dict.get("traveler", {})
        party_size = traveler_dict.get("count") or 1
        
        # Get activities and distances
        activities_raw = candidates.get("activities", [])
        distances_raw = candidates.get("distances", [])
        neighborhoods = candidates.get("neighborhoods", {})
        
        print(f"   Destination: {destination}")
        print(f"   Duration: {duration_days} days | Budget: ₹{budget}")
        print(f"   Available: {len(activities_raw)} activities")
        print(f"   Interests: {interests}")
        
        if not activities_raw:
            print("⚠️ No OSM activities found — using LLM knowledge-based fallback")
            return self._create_llm_fallback_plan(
                planning_state, destination, duration_days, budget, party_size, interests
            )
        
        # Convert activities
        activities = self._convert_activities(activities_raw)
        
        # Build distance lookup
        distance_map = self._build_distance_map(distances_raw, activities)
        
        # Create daily plans with location optimization
        print(f"\n📋 Creating {duration_days}-day itinerary with location routing...")
        daily_plans = []
        
        # Distribute activities across days using round-robin
        # (ensures each day gets a diverse mix, not just leftovers on Day 3)
        daily_activity_pools = [[] for _ in range(duration_days)]
        for i, activity in enumerate(activities):
            daily_activity_pools[i % duration_days].append(activity)
        
        for day_num in range(1, duration_days + 1):
            print(f"\n   Day {day_num}:")
            
            # Get this day's activity pool
            day_activities_raw = daily_activity_pools[day_num - 1]
            
            # Create optimized day plan
            day_plan = self._create_optimized_day_plan(
                day_num,
                day_activities_raw,
                distance_map,
                budget / (duration_days or 3),
                party_size,
                interests,
                destination
            )
            
            daily_plans.append(day_plan)
            
            print(f"      ✓ {len(day_plan.activities)} activities sequenced")
            print(f"      ✓ Total travel: {day_plan.total_walking_km:.1f} km")
            print(f"      ✓ Cost: ₹{day_plan.total_cost:.0f}")
        
        # Calculate statistics
        print(f"\n📊 Calculating trip statistics...")
        stats = self._calculate_stats(daily_plans, activities, interests)
        
        # Create result
        result = PlannerResult(
            trip_title=self._generate_trip_title(destination, interests),
            trip_summary=self._generate_trip_summary(destination, duration_days, interests),
            destination=destination,
            duration_days=duration_days,
            days=daily_plans,
            stats=stats,
            highlights=self._generate_highlights(daily_plans, interests),
            tips=self._generate_tips(destination),
            warnings=self._generate_warnings(daily_plans, budget)
        )
        
        # Store in planning state
        planning_state.plans = [day.model_dump() for day in daily_plans]
        planning_state.selected_plan = result.model_dump()
        
        print("\n" + "="*80)
        print(f"✅ PLANNING COMPLETE")
        print(f"   Days: {len(daily_plans)}")
        print(f"   Activities: {stats.total_activities}")
        print(f"   Total distance: {stats.total_walking_km:.1f} km")
        print(f"   Total cost: ₹{stats.total_cost:.0f}")
        print("="*80 + "\n")
        
        return result
    
    def _convert_activities(self, activities_raw: List[Dict]) -> List[Dict]:
        """Convert raw activities to standardized format"""
        converted = []
        
        for activity in activities_raw:
            converted.append({
                "id": activity.get("id", ""),
                "name": activity.get("name", ""),
                "category": activity.get("category", ""),
                "lat": activity.get("coordinates", {}).get("lat", 0),
                "lng": activity.get("coordinates", {}).get("lng", 0),
                "location": activity.get("area", ""),
                "address": activity.get("address", ""),
                "cost": activity.get("cost_per_person_inr", 0),
                "cost_type": activity.get("cost_type", "free"),
                "duration_minutes": activity.get("duration_minutes", 60),
                "rating": activity.get("rating", 0),
                "description": activity.get("description", ""),
                "matches_interests": activity.get("matches_interests", [])
            })
        
        return converted
    
    def _build_distance_map(self, distances_raw: List[Dict], activities: List[Dict]) -> Dict:
        """Build a lookup map for distances between activities"""
        
        distance_map = {}
        
        for distance_data in distances_raw:
            from_id = distance_data.get("from_activity", "")
            to_id = distance_data.get("to_activity", "")
            distance_km = distance_data.get("distance_km", 0)
            travel_time = distance_data.get("travel_time_minutes", 0)
            
            # Create bidirectional mapping
            distance_map[(from_id, to_id)] = {
                "distance_km": distance_km,
                "travel_time_minutes": travel_time
            }
            distance_map[(to_id, from_id)] = {
                "distance_km": distance_km,
                "travel_time_minutes": travel_time
            }
        
        return distance_map
    
    def _create_optimized_day_plan(
        self,
        day_num: int,
        activities: List[Dict],
        distance_map: Dict,
        daily_budget: float,
        party_size: int,
        interests: List[str],
        destination: str = ""
    ) -> DayPlan:
        """Create a day plan with location-optimized sequencing"""
        
        # CRITICAL: Sequence activities to minimize travel
        # Prefer highly rated activities
        activities_sorted = sorted(
            activities,
            key=lambda a: (a.get("rating", 0), -a.get("cost", 0)),
            reverse=True
        )
        
        # Use nearest-neighbor algorithm to sequence
        sequenced = self._nearest_neighbor_sequence(
            activities_sorted,
            distance_map
        )
        
        # Schedule activities with times and travel
        scheduled = self._schedule_with_travel(
            sequenced,
            distance_map,
            daily_budget,
            interests,
            destination,
            party_size
        )
        
        # Add meals
        meals = self._schedule_meals(scheduled, party_size)
        
        # Calculate stats
        total_cost = sum(a.cost_per_person for a in scheduled) * party_size
        total_cost += sum(m.cost_per_person for m in meals) * party_size
        
        total_walking = self._calculate_total_walking(scheduled, distance_map)
        steps = int(total_walking * 1300)  # ~1300 steps per km
        
        theme = self._generate_day_theme(scheduled, interests)
        
        return DayPlan(
            day_number=day_num,
            theme=theme,
            activities=scheduled,
            meals=meals,
            total_activities=len(scheduled),
            total_cost=total_cost,
            total_walking_km=total_walking,
            estimated_steps=steps,
            rest_hours=self._calculate_rest_hours(scheduled),
            notes=self._generate_day_notes(day_num, total_walking)
        )
    
    def _nearest_neighbor_sequence(
        self,
        activities: List[Dict],
        distance_map: Dict
    ) -> List[Dict]:
        """
        Sequence activities using nearest-neighbor algorithm
        Minimizes total travel distance
        """
        
        if not activities:
            return []
        
        # Start with highest-rated activity
        sequenced = [activities[0]]
        remaining = activities[1:]
        
        while remaining:
            current = sequenced[-1]
            current_id = current.get("id", "")
            
            # Find nearest unvisited activity
            nearest = None
            nearest_distance = float('inf')
            
            for activity in remaining:
                activity_id = activity.get("id", "")
                
                # Get distance
                distance_data = distance_map.get((current_id, activity_id))
                if distance_data:
                    distance = distance_data.get("distance_km", float('inf'))
                else:
                    # Estimate Haversine if not in map
                    distance = self._haversine(
                        current.get("lat", 0),
                        current.get("lng", 0),
                        activity.get("lat", 0),
                        activity.get("lng", 0)
                    )
                
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest = activity
            
            if nearest:
                sequenced.append(nearest)
                remaining.remove(nearest)
            else:
                break
        
        return sequenced
    
    def _schedule_with_travel(
        self,
        activities: List[Dict],
        distance_map: Dict,
        daily_budget: float,
        interests: List[str],
        destination: str = "",
        party_size: int = 1
    ) -> List[DayActivity]:
        """Schedule activities with realistic travel times"""
        
        scheduled = []
        current_time = 9 * 60  # 9 AM in minutes
        current_cost = 0
        
        # Compute per-person daily budget and reserve ₹560/person for meals
        per_person_daily = daily_budget / max(party_size, 1)
        remaining_budget = per_person_daily - 560  # per-person activity budget
        
        for idx, activity in enumerate(activities):
            # Check if we can fit this activity
            duration = activity.get("duration_minutes", 60)
            cost = activity.get("cost", 0)
            
            # Budget check: skip if this activity alone uses > 50% of remaining budget
            # OR if cumulative cost already exceeds the activity budget
            if current_cost >= remaining_budget:
                break  # Day is full budget-wise
            if current_cost + cost > remaining_budget:
                if cost > remaining_budget * 0.5:
                    continue  # Too expensive relative to what's left
            
            # Check time (must finish by 9 PM = 21:00)
            if current_time + duration > 21 * 60:
                break
            
            # Skip if we already have a similar activity today
            existing_categories = [s.category for s in scheduled]
            if activity.get("category") in existing_categories and activity.get("category") == "cafe":
                continue
            
            # Format time
            hours = current_time // 60
            minutes = current_time % 60
            time_start = f"{int(hours):02d}:{int(minutes):02d}"
            
            # End time
            end_time = current_time + duration
            end_hours = end_time // 60
            end_minutes = end_time % 60
            time_end = f"{int(end_hours):02d}:{int(end_minutes):02d}"
            
            # Add travel time to next activity (if exists)
            if idx < len(activities) - 1:
                next_activity = activities[idx + 1]
                current_id = activity.get("id", "")
                next_id = next_activity.get("id", "")
                
                travel_data = distance_map.get((current_id, next_id))
                if travel_data:
                    travel_time = travel_data.get("travel_time_minutes", 15)
                else:
                    travel_time = 15  # Default 15 min
            else:
                travel_time = 0
            
            # Create activity
            scheduled.append(DayActivity(
                sequence=len(scheduled) + 1,
                time_start=time_start,
                time_end=time_end,
                activity_id=activity.get("id", ""),
                activity_name=activity.get("name", ""),
                category=activity.get("category", ""),
                location=activity.get("location", destination),
                address=activity.get("address", ""),
                cost_per_person=cost,
                duration_minutes=duration,
                description=activity.get("description", ""),
                why_included=self._get_why_included(activity, interests)
            ))
            
            # Update time (activity + travel buffer)
            current_time = end_time + travel_time
            current_cost += cost
        
        return scheduled
    
    def _get_why_included(self, activity: Dict, interests: List[str]) -> str:
        """Explain why activity was chosen"""
        
        name = activity.get("name", "")
        category = activity.get("category", "")
        rating = activity.get("rating", 0)
        matches = activity.get("matches_interests", [])
        
        # Prioritize highly-rated places
        if rating >= 4.5:
            if "museum" in category.lower() or "gallery" in category.lower() or "monument" in category.lower():
                return f"⭐ Top-rated {category.lower()} - cultural experience"
            elif "restaurant" in category.lower():
                return f"⭐ Highly-rated local restaurant"
            else:
                return f"⭐ Highly-rated attraction"
        
        # Prioritize matches
        if matches:
            return f"Matches your interest in {matches[0]}"
        
        # Default
        return f"Popular {category.lower()} in the area"
    
    def _schedule_meals(self, activities: List[DayActivity], party_size: int) -> List[Meal]:
        """Schedule meals realistically"""
        
        meals = []
        
        # Breakfast before first activity
        meals.append(Meal(
            type="breakfast",
            time="08:00",
            restaurant_name="Hotel Breakfast/Local Cafe",
            location="Accommodation",
            cost_per_person=80,
            cuisine="Local"
        ))
        
        # Lunch around midday
        lunch_time = "12:30"
        meals.append(Meal(
            type="lunch",
            time=lunch_time,
            restaurant_name="Local Restaurant",
            location="Near Activities",
            cost_per_person=200,
            cuisine="Local"
        ))
        
        # Dinner evening
        meals.append(Meal(
            type="dinner",
            time="19:30",
            restaurant_name="Restaurant/Cafe",
            location="Evening Location",
            cost_per_person=280,
            cuisine="Local"
        ))
        
        return meals
    
    def _calculate_total_walking(self, activities: List[DayActivity], distance_map: Dict) -> float:
        """Calculate total walking distance for the day"""
        
        total = 0
        
        for idx in range(len(activities) - 1):
            current_id = activities[idx].activity_id
            next_id = activities[idx + 1].activity_id
            
            distance_data = distance_map.get((current_id, next_id))
            if distance_data:
                total += distance_data.get("distance_km", 0)
        
        return total
    
    def _calculate_rest_hours(self, activities: List[DayActivity]) -> float:
        """Calculate rest/free time"""
        
        if not activities:
            return 24
        
        # Total activity time
        total_activity_minutes = sum(a.duration_minutes for a in activities)
        
        # Add meal time (3 hours)
        total_activity_minutes += 180
        
        # Calculate rest
        total_minutes = 24 * 60
        rest_minutes = total_minutes - total_activity_minutes
        
        return max(0, rest_minutes / 60)
    
    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between coordinates"""
        
        R = 6371  # Earth radius km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _generate_day_theme(self, activities: List[DayActivity], interests: List[str]) -> str:
        """Generate theme based on activities"""
        
        if not activities:
            return "Rest Day"
        
        categories = [a.category for a in activities]
        
        # Count by category
        food_count = sum(1 for c in categories if "cafe" in c.lower() or "restaurant" in c.lower())
        culture_count = sum(1 for c in categories if "museum" in c.lower() or "monument" in c.lower() or "gallery" in c.lower())
        nature_count = sum(1 for c in categories if "park" in c.lower() or "garden" in c.lower())
        
        if food_count > culture_count and food_count > nature_count:
            return "🍽️ Culinary Exploration"
        elif culture_count > nature_count:
            return "🏛️ Cultural Journey"
        elif nature_count > 0:
            return "🌳 Nature & Relaxation"
        else:
            return "🎯 City Discovery"
    
    def _generate_day_notes(self, day_num: int, total_walking: float) -> str:
        """Generate day notes"""
        
        if day_num == 1:
            return "Arrival & orientation day"
        elif day_num == 2:
            return f"Full exploration day ({total_walking:.0f}km walking)"
        else:
            return f"Final day - enjoy favorites again"
    
    def _calculate_stats(
        self,
        daily_plans: List[DayPlan],
        all_activities: List[Dict],
        interests: List[str]
    ) -> ItineraryStats:
        """Calculate trip statistics"""
        
        total_activities = sum(len(day.activities) for day in daily_plans)
        total_cost = sum(day.total_cost for day in daily_plans)
        total_walking = sum(day.total_walking_km for day in daily_plans)
        total_steps = sum(day.estimated_steps for day in daily_plans)
        
        free_count = sum(1 for a in all_activities if a.get("cost", 0) == 0)
        paid_count = len(all_activities) - free_count
        
        # Interest distribution
        interest_dist = {}
        for interest in interests:
            matching = sum(1 for a in all_activities if interest.lower() in str(a.get("matches_interests", [])).lower())
            percentage = (matching / len(all_activities) * 100) if all_activities else 0
            interest_dist[interest] = round(percentage, 1)
        
        return ItineraryStats(
            total_activities=total_activities,
            total_cost=total_cost,
            total_walking_km=total_walking,
            average_daily_cost=total_cost / len(daily_plans) if daily_plans else 0,
            estimated_total_steps=total_steps,
            average_daily_walking_km=total_walking / len(daily_plans) if daily_plans else 0,
            free_activities=free_count,
            paid_activities=paid_count,
            interest_distribution=interest_dist,
            neighborhood_distribution={}
        )
    
    def _generate_trip_title(self, destination: str, interests: List[str]) -> str:
        """Generate trip title"""
        
        if interests:
            # Use first 2 interests
            interest_str = " & ".join(interests[:2])
            # Truncate if too long
            interest_str = interest_str[:50] if len(interest_str) > 50 else interest_str
            return f"{destination}: {interest_str}"
        else:
            return f"{destination} Exploration Trip"
    
    def _generate_trip_summary(self, destination: str, duration: int, interests: List[str]) -> str:
        """Generate trip summary"""
        
        if interests:
            # Take first 2 interests
            interest_list = interests[:2]
            interest_str = ", ".join([str(i)[:30] for i in interest_list])  # Truncate each interest
            return f"Explore {destination}'s best {interest_str} attractions over {duration} days"
        else:
            return f"A {duration}-day exploration of {destination}"
    
    def _generate_highlights(self, daily_plans: List[DayPlan], interests: List[str]) -> List[str]:
        """Generate trip highlights"""
        
        highlights = []
        
        all_activities = []
        for day in daily_plans:
            all_activities.extend(day.activities)
        
        if all_activities:
            total_walking = sum(day.total_walking_km for day in daily_plans)
            highlights.append(f"Visit {len(all_activities)} carefully selected attractions")
            highlights.append(f"Optimized routing - {total_walking:.0f}km total travel")
        
        if interests:
            if "food" in str(interests).lower():
                highlights.append("Discover local culinary gems")
            if "culture" in str(interests).lower():
                highlights.append("Explore historical & cultural landmarks")
            if "relaxation" in str(interests).lower():
                highlights.append("Peaceful moments in nature")
        
        return highlights if highlights else ["Curated travel experience"]
    
    def _generate_tips(self, destination: str) -> List[str]:
        """Generate practical tips"""
        
        return [
            "Wear comfortable walking shoes (20+ km daily)",
            "Start activities early to beat crowds",
            "Keep water bottle handy",
            "Download offline maps of your route",
            "Check opening hours before visiting",
            "Book popular restaurants in advance",
            "Use public transport where possible"
        ]
    
    def _generate_warnings(self, daily_plans: List[DayPlan], budget: float) -> List[str]:
        """Generate warnings if needed"""
        
        warnings = []
        
        total_cost = sum(day.total_cost for day in daily_plans)
        
        if total_cost > budget * 0.9:
            shortfall = total_cost - budget
            warnings.append(f"⚠️ Budget exceeded by ₹{shortfall:.0f}")
        
        for day in daily_plans:
            if day.total_walking_km > 25:
                warnings.append(f"⚠️ Day {day.day_number}: {day.total_walking_km:.0f}km walking - very intense")
            
            if day.rest_hours < 4:
                warnings.append(f"⚠️ Day {day.day_number}: Only {day.rest_hours:.1f}h rest time")
        
        return warnings
    
    def _create_llm_fallback_plan(
        self,
        planning_state,
        destination: str,
        duration_days: int,
        budget: float,
        party_size: int,
        interests: List[str],
    ) -> "PlannerResult":
        """
        Generate a full itinerary using LLM world knowledge when OSM returns 0 activities.
        Produces real day cards the UI can render.
        """
        interests_str = ", ".join(interests) if interests else "sightseeing, local cuisine"
        daily_budget = round(budget / max(duration_days, 1) / max(party_size, 1))

        system_prompt = (
            "You are an expert travel itinerary planner with deep knowledge of Indian tourism. "
            "Return ONLY valid JSON — no markdown, no extra text."
        )

        user_prompt = f"""Create a detailed {duration_days}-day trip itinerary for {destination}.

Trip details:
- Party: {party_size} people
- Total budget: ₹{budget}
- Daily budget per person: ₹{daily_budget}
- Interests: {interests_str}

Return this exact JSON structure (no markdown fences):
{{
  "trip_title": "string",
  "trip_summary": "string (2-3 sentences)",
  "days": [
    {{
      "day_number": 1,
      "theme": "string (e.g. Forts & Palaces of Jaipur)",
      "activities": [
        {{
          "sequence": 1,
          "time_start": "09:00",
          "time_end": "11:30",
          "activity_name": "string",
          "category": "string (fort/museum/restaurant/temple/market/etc)",
          "location": "string (area/neighbourhood)",
          "address": "string",
          "cost_per_person": 0,
          "duration_minutes": 90,
          "description": "string (1-2 sentences)",
          "why_included": "string (why this suits the traveler)"
        }}
      ],
      "meals": [
        {{
          "type": "breakfast",
          "time": "08:00",
          "restaurant_name": "string",
          "location": "string",
          "cost_per_person": 150,
          "cuisine": "string"
        }}
      ],
      "total_cost": 0,
      "total_walking_km": 4.5,
      "notes": "string"
    }}
  ],
  "warnings": []
}}

Rules:
- Include 3-5 activities per day (real, well-known places).
- Include breakfast, lunch, dinner for each day.
- Respect the budget: activities + meals total_cost per day ≤ ₹{daily_budget * party_size}.
- Spread activities across the destination's key areas.
- Make it genuinely useful and accurate — do NOT invent fake places.
- All numeric fields must be numbers (not strings).
"""

        try:
            print("🤖 Calling LLM for knowledge-based itinerary...")
            raw = self.llm.generate(system_prompt, user_prompt)
            data = json.loads(raw)

            days_data = data.get("days", [])
            days: List[DayPlan] = []

            for d in days_data:
                acts = []
                for a in d.get("activities", []):
                    acts.append(DayActivity(
                        sequence=a.get("sequence", 1),
                        time_start=a.get("time_start", "09:00"),
                        time_end=a.get("time_end", "10:00"),
                        activity_id=f"llm_{a.get('sequence', 1)}_{d.get('day_number', 1)}",
                        activity_name=a.get("activity_name", "Activity"),
                        category=a.get("category", "attraction"),
                        location=a.get("location", destination),
                        address=a.get("address", ""),
                        cost_per_person=float(a.get("cost_per_person", 0)),
                        duration_minutes=int(a.get("duration_minutes", 60)),
                        description=a.get("description", ""),
                        why_included=a.get("why_included", ""),
                    ))

                meals = []
                for m in d.get("meals", []):
                    meals.append(Meal(
                        type=m.get("type", "meal"),
                        time=m.get("time", "12:00"),
                        restaurant_name=m.get("restaurant_name", "Local Restaurant"),
                        location=m.get("location", destination),
                        cost_per_person=float(m.get("cost_per_person", 200)),
                        cuisine=m.get("cuisine", "Indian"),
                    ))

                total_cost = float(d.get("total_cost") or sum(a.cost_per_person for a in acts) + sum(m.cost_per_person for m in meals))

                days.append(DayPlan(
                    day_number=d.get("day_number", len(days) + 1),
                    theme=d.get("theme", "Exploration"),
                    activities=acts,
                    meals=meals,
                    total_activities=len(acts),
                    total_cost=total_cost * party_size,
                    total_walking_km=float(d.get("total_walking_km", 4.0)),
                    estimated_steps=int(float(d.get("total_walking_km", 4.0)) * 1400),
                    rest_hours=8.0,
                    notes=d.get("notes", ""),
                ))

            total_cost_all = sum(day.total_cost for day in days)
            stats = ItineraryStats(
                total_activities=sum(len(day.activities) for day in days),
                total_cost=total_cost_all,
                total_walking_km=sum(day.total_walking_km for day in days),
                average_daily_cost=total_cost_all / max(len(days), 1),
                estimated_total_steps=sum(day.estimated_steps for day in days),
                average_daily_walking_km=sum(day.total_walking_km for day in days) / max(len(days), 1),
                free_activities=sum(1 for day in days for act in day.activities if act.cost_per_person == 0),
                paid_activities=sum(1 for day in days for act in day.activities if act.cost_per_person > 0),
                interest_distribution={},
                neighborhood_distribution={},
            )

            result = PlannerResult(
                trip_title=data.get("trip_title", f"{duration_days}-Day {destination} Trip"),
                trip_summary=data.get("trip_summary", ""),
                destination=destination,
                duration_days=duration_days,
                days=days,
                stats=stats,
                highlights=[],
                tips=self._generate_tips(destination),
                warnings=data.get("warnings", ["Note: This itinerary was generated from AI world knowledge since live POI data was unavailable."]),
            )

            # Store in planning state so optimizer/critic can use it
            planning_state.plans = [day.model_dump() for day in days]
            planning_state.selected_plan = result.model_dump()

            print(f"✅ LLM fallback: created {len(days)}-day itinerary with {stats.total_activities} activities")
            return result

        except Exception as e:
            print(f"❌ LLM fallback failed: {e}")
            return self._create_empty_result(destination, duration_days)

    def _create_empty_result(self, destination: str, duration: int) -> "PlannerResult":
        """Create empty result"""
        
        return PlannerResult(
            trip_title=f"{duration}-Day {destination}",
            trip_summary="Could not create itinerary",
            destination=destination,
            duration_days=duration,
            days=[],
            stats=ItineraryStats(
                total_activities=0,
                total_cost=0,
                total_walking_km=0,
                average_daily_cost=0,
                estimated_total_steps=0,
                average_daily_walking_km=0,
                free_activities=0,
                paid_activities=0,
                interest_distribution={},
                neighborhood_distribution={}
            ),
            highlights=[],
            tips=[],
            warnings=["No activities found"]
        )