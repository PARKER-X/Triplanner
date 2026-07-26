"""
Research Agent - Retrieve real activities and ground data
Uses FREE OpenStreetMap + Wikipedia APIs (No API key needed!)
"""

import json
from datetime import datetime
from typing import List, Dict, Optional,Union

from .schema import Activity, ResearchResult, GroundingData
from .apis.osm_nominatim import NominatimAPI
from .apis.overpass import OverpassAPI
from .apis.wikipedia import WikipediaAPI
from .apis.distance_calculator import DistanceCalculator


class ResearchAgent:
    """
    Research Agent - Retrieves real activities and grounds them in reality
    
    Flow:
    1. Get coordinates of destination
    2. Search for activities using Overpass API
    3. Enrich with Wikipedia data
    4. Calculate distances between all activities
    5. Return grounded data for planning
    """
    
    def __init__(self, llm):
        """Initialize with free APIs (no keys needed!)"""
        self.llm = llm
        self.nominatim = NominatimAPI()
        self.overpass = OverpassAPI()
        self.wikipedia = WikipediaAPI()
        self.distance_calc = DistanceCalculator()
        
        # Load prompt
        with open("ai_engine/agent/research_agent/prompt.txt") as f:
            self.prompt = f.read()
        
        print("✅ Research Agent initialized (using free APIs)")
    
    def run(self, planning_state) -> ResearchResult:
        """
        Main research execution
        
        Input: planning_state with intent + constraints
        Output: ResearchResult with real activities and grounding data
        
        FIX: Extract preferences from intent dict, not planning_state
        """
        # Extract from planning_state
        intent_dict = planning_state.intent  # This is a dict
        constraints_dict = planning_state.constraints  # This is a dict
        
        # Extract fields from intent_dict
        destination = constraints_dict.get("destination", "")
        duration_days = constraints_dict.get("duration_days", 3)
        budget = constraints_dict.get("budget", 10000)
        
        # Get preferences from intent_dict
        preferences_dict = intent_dict.get("preferences", {})
        interests = preferences_dict.get("priorities", [])
        
        # Get traveler info from intent_dict
        traveler_dict = intent_dict.get("traveler", {})
        party_size = traveler_dict.get("count", 4)
        
        print("\n" + "="*80)
        print(f"🔍 RESEARCH AGENT: Searching for activities in {destination}")
        print("="*80)
        print(f"   Duration: {duration_days} days | Budget: ₹{budget} | Interests: {', '.join(interests)}")
        print(f"   Party size: {party_size}")
        
        # Step 1: Get destination coordinates
        coords = self.nominatim.get_location_coords(destination)
        if not coords:
            print("❌ Could not find destination")
            return self._create_empty_result(destination)
        
        lat, lng = coords
        print(f"   Coordinates: ({lat:.4f}, {lng:.4f})")
        
        # Step 2: Search for activities
        osm_tags = self._map_interests_to_osm_tags(interests)
        print(f"\n🏪 Searching for activities with tags: {osm_tags[:3]}...")  # Show first 3
        
        raw_activities = self.overpass.search_activities(lat, lng, osm_tags, radius_meters=5000)
        
        if not raw_activities:
            print("⚠️ No activities found, trying broader search...")
            raw_activities = self.overpass.search_activities(
                lat, lng,
                ["amenity=restaurant", "tourism=museum", "leisure=park"],
                radius_meters=5000
            )
        
        print(f"📊 Found {len(raw_activities)} raw activities from OpenStreetMap")
        
        # Step 3: Enrich with Wikipedia
        print("\n📚 Enriching with Wikipedia data...")
        enriched_activities = self._enrich_activities(raw_activities)
        print(f"   Enriched {len(enriched_activities)} activities")
        
        # Step 4: Filter by constraints
        print("\n⚖️ Filtering by constraints...")
        filtered_activities = self._filter_by_constraints(
            enriched_activities,
            budget,
            duration_days,
            interests,
            party_size
        )
        
        print(f"✅ {len(filtered_activities)} activities match constraints")
        
        if not filtered_activities:
            print("⚠️ No activities match constraints, returning all activities")
            filtered_activities = enriched_activities[:20]  # Return top 20
        
        # Step 5: Calculate distances
        print("\n📍 Calculating distances between activities...")
        distances = self.distance_calc.calculate_all_distances(filtered_activities)
        print(f"   Calculated {len(distances)} distance pairs")
        
        # Step 6: Create result
        grounding_data = GroundingData(
            activities=filtered_activities,
            distances=distances,  # distances are already dicts
            neighborhoods=self._extract_neighborhoods(filtered_activities)
        )
        
        result = ResearchResult(
            destination=destination,
            search_date=datetime.now().isoformat()[:10],
            activities=filtered_activities,
            grounding=grounding_data,
            total_activities_found=len(raw_activities),
            feasible_activities=len(filtered_activities),
            budget_coverage=self._calculate_budget_coverage(filtered_activities),
            interest_coverage=self._calculate_interest_coverage(filtered_activities, interests)
        )
        
        planning_state.candidates = {
            "activities": [a.model_dump() for a in filtered_activities],
            "distances": distances,  # FIXED: Already dicts
            "neighborhoods": result.grounding.neighborhoods
        }
        print("\n" + "="*80)
        print(f"✅ RESEARCH COMPLETE")
        print(f"   Activities found: {len(filtered_activities)}")
        print(f"   Interest coverage: {result.interest_coverage}")
        print(f"   Budget coverage: {result.budget_coverage}")
        print("="*80 + "\n")
        
        return result
    
    def _map_interests_to_osm_tags(self, interests: List[str]) -> List[str]:
        """Map user interests to OpenStreetMap tags"""
        
        mapping = {
            "food": [
                "amenity=restaurant",
                "amenity=cafe",
                "amenity=bar",
                "amenity=fast_food",
                "shop=supermarket"
            ],
            "culture": [
                "tourism=museum",
                "tourism=art_gallery",
                "historic=monument",
                "amenity=library"
            ],
            "nature": [
                "leisure=park",
                "leisure=garden",
                "natural=water",
                "leisure=swimming_pool"
            ],
            "adventure": [
                "tourism=tour_operator",
                "leisure=sports_centre",
                "sport=climbing"
            ],
            "relaxation": [
                "amenity=spa",
                "leisure=swimming_pool",
                "leisure=beach",
                "tourism=hotel"
            ],
            "shopping": [
                "shop=mall",
                "shop=market",
                "shop=supermarket"
            ]
        }
        
        tags = []
        for interest in interests:
            interest_lower = interest.lower().strip()
            if interest_lower in mapping:
                tags.extend(mapping[interest_lower])
        
        # Remove duplicates
        unique_tags = list(set(tags))
        return unique_tags if unique_tags else ["tourism=attraction", "amenity=restaurant", "leisure=park"]
    
    def _enrich_activities(self, activities: List[Dict]) -> List[Activity]:
        """Enrich raw activities with Wikipedia data and convert to Activity objects"""
        
        enriched = []
        
        for raw in activities:
            try:
                # Get Wikipedia info
                wiki_info = self.wikipedia.get_info(raw["name"])
                
                description = raw["description"]
                if wiki_info and wiki_info.get("summary"):
                    description = wiki_info["summary"]
                
                # Create Activity object
                activity = Activity(
                    id=raw["id"],
                    name=raw["name"],
                    category=raw["category"],
                    address=raw.get("address", ""),
                    coordinates=raw["coordinates"],
                    area=raw.get("area", ""),
                    duration_minutes=raw.get("duration_minutes", 60),
                    opening_hours=raw.get("opening_hours", []),
                    cost_per_person_inr=raw.get("cost_per_person_inr", 0),
                    cost_type=raw.get("cost_type", "free"),
                    rating=raw.get("rating", 4.0),
                    review_count=raw.get("review_count", 0),
                    matches_interests=[],  # Will fill later
                    description=description,
                    source=raw.get("source", "openstreetmap")
                )
                
                enriched.append(activity)
            
            except Exception as e:
                print(f"   ⚠️ Error enriching {raw.get('name', 'unknown')}: {str(e)[:50]}")
                continue
        
        return enriched
    
    def _filter_by_constraints(
        self,
        activities: List[Activity],
        budget: float,
        duration_days: int,
        interests: List[str],
        party_size: int
    ) -> List[Activity]:
        """Filter activities by user constraints"""
        
        filtered = []
        
        # Daily budget per person
        daily_budget_per_person = budget / duration_days / party_size
        max_activity_cost = daily_budget_per_person * 0.5  # Max 50% of daily budget per activity
        
        print(f"   Daily budget per person: ₹{daily_budget_per_person:.0f}")
        print(f"   Max per activity: ₹{max_activity_cost:.0f}")
        
        for activity in activities:
            # Skip accommodations (not activities)
            if activity.category in ["hotel", "hostel", "guest_house", "apartment"]:
                continue
            
            # Budget check - if cost is specified, check it
            if activity.cost_per_person_inr and activity.cost_per_person_inr > max_activity_cost:
                if activity.cost_per_person_inr > 0:  # Skip only expensive ones
                    if activity.cost_per_person_inr > daily_budget_per_person:
                        continue
            
            # Match interests
            matches = self._get_matching_interests(activity, interests)
            activity.matches_interests = matches
            
            # Keep if it matches interests OR is a general attraction
            if matches or activity.category in ["attraction", "viewpoint", "park"]:
                filtered.append(activity)
        
        return filtered
    
    def _get_matching_interests(self, activity: Activity, interests: List[str]) -> List[str]:
        """Get which user interests match this activity"""
        
        category_interest_map = {
            "restaurant": ["food"],
            "cafe": ["food"],
            "bar": ["food", "relaxation"],
            "fast_food": ["food"],
            "museum": ["culture"],
            "art_gallery": ["culture"],
            "park": ["nature", "relaxation"],
            "garden": ["nature"],
            "swimming_pool": ["relaxation", "adventure"],
            "monument": ["culture"],
            "viewpoint": ["nature"],
            "tour_operator": ["adventure"],
            "market": ["shopping", "food"],
            "spa": ["relaxation"],
            "beach": ["relaxation", "nature"],
            "library": ["culture"]
        }
        
        matches = []
        
        # Check category matches
        if activity.category in category_interest_map:
            potential_matches = category_interest_map[activity.category]
            # Only add if user is interested in it
            for interest in interests:
                if interest.lower() in potential_matches:
                    matches.append(interest)
        
        # Check interest keywords in description
        if interests:
            for interest in interests:
                interest_lower = interest.lower()
                if interest_lower in activity.description.lower():
                    if interest not in matches:
                        matches.append(interest)
        
        return list(set(matches))  # Remove duplicates
    
    def _extract_neighborhoods(self, activities: List[Activity]) -> Dict[str, Dict]:
        """Extract and summarize neighborhoods"""
        
        neighborhoods = {}
        
        for activity in activities:
            area = activity.area
            if not area or area == "":
                continue
            
            if area not in neighborhoods:
                neighborhoods[area] = {
                    "name": area,
                    "activities_count": 0,
                    "categories": [],
                    "avg_cost": 0
                }
            
            neighborhoods[area]["activities_count"] += 1
            if activity.category not in neighborhoods[area]["categories"]:
                neighborhoods[area]["categories"].append(activity.category)
        
        # Calculate averages
        for area, data in neighborhoods.items():
            area_activities = [a for a in activities if a.area == area]
            costs = [a.cost_per_person_inr for a in area_activities if a.cost_per_person_inr and a.cost_per_person_inr > 0]
            if costs:
                data["avg_cost"] = sum(costs) / len(costs)
        
        return neighborhoods
    
    def _calculate_budget_coverage(self, activities: List[Activity]) -> Dict[str, int]:
        """Calculate how many activities in each price range"""
        
        coverage = {
            "free": 0,
            "budget": 0,
            "moderate": 0,
            "expensive": 0
        }
        
        for activity in activities:
            coverage[activity.cost_type] += 1
        
        return coverage
    
    def _calculate_interest_coverage(self, activities: List[Activity], interests: List[str]) -> Dict[str, float]:
        """Calculate coverage for each interest"""
        
        coverage = {}
        
        for interest in interests:
            matching = sum(1 for a in activities if interest.lower() in [i.lower() for i in a.matches_interests])
            total = len(activities)
            percentage = (matching / total * 100) if total > 0 else 0
            coverage[interest] = round(percentage, 1)
        
        return coverage
    
    def _create_empty_result(self, destination: str) -> ResearchResult:
        """Create empty result when no activities found"""
        return ResearchResult(
            destination=destination,
            search_date=datetime.now().isoformat()[:10],
            activities=[],
            grounding=GroundingData(activities=[], distances=[]),
            total_activities_found=0,
            feasible_activities=0,
            budget_coverage={},
            interest_coverage={}
        )