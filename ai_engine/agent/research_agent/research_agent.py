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
        """
        # Extract from planning_state
        intent_dict = planning_state.intent  # This is a dict
        constraints_dict = planning_state.constraints  # This is a dict

        # Extract fields from intent_dict
        destination = constraints_dict.get("destination", "") or ""
        duration_days = constraints_dict.get("duration_days") or 3
        budget = constraints_dict.get("budget") or 10000

        # Get preferences from intent_dict
        preferences_dict = intent_dict.get("preferences", {})
        interests = preferences_dict.get("priorities") or []

        # Get traveler info from intent_dict
        traveler_dict = intent_dict.get("traveler", {})
        party_size = traveler_dict.get("count") or 1

        print("\n" + "=" * 80)
        print(f"🔍 RESEARCH AGENT: Searching for activities in {destination}")
        print("=" * 80)
        print(f"   Duration: {duration_days} days | Budget: ₹{budget} | Interests: {', '.join(interests)}")
        print(f"   Party size: {party_size}")

        # ── Step 1: Geocode — support multi-city destinations ─────────────────
        cities = self._extract_cities(destination)
        print(f"   Cities detected: {cities}")

        all_coords = []
        for city in cities:
            coords = self.nominatim.get_location_coords(city)
            if coords:
                all_coords.append((city, coords[0], coords[1]))

        if not all_coords:
            print("❌ Could not geocode any destination")
            return self._create_empty_result(destination)

        # ── Step 2: Build OSM tags ─────────────────────────────────────────────
        osm_tags = self._map_interests_to_osm_tags(interests)
        print(f"\n🏪 OSM tags to query: {osm_tags}")

        # ── Step 3: Search Overpass for every city ────────────────────────────
        raw_activities: List[Dict] = []
        for city_name, lat, lng in all_coords:
            print(f"\n   📍 Searching in {city_name} ({lat:.4f}, {lng:.4f})...")
            city_results = self.overpass.batch_search_activities(
                lat, lng, osm_tags, radius_meters=8000
            )
            if not city_results:
                print(f"   ⚠️ No results for {city_name}, trying broad fallback...")
                city_results = self.overpass.batch_search_activities(
                    lat, lng,
                    [
                        "tourism=attraction", "tourism=museum", "amenity=restaurant",
                        "historic=fort", "historic=castle", "historic=palace",
                        "historic=monument", "leisure=park",
                    ],
                    radius_meters=10000,
                )
            raw_activities.extend(city_results)
            print(f"   ✅ {len(city_results)} activities found in {city_name}")

        print(f"\n📊 Total raw activities from OpenStreetMap: {len(raw_activities)}")

        # ── Step 4: Pre-filter — keep named places, cap at 40 per Wikipedia ───
        named = [a for a in raw_activities if not a.get("name", "").startswith("Place ")]
        top_raw = named[:40] if named else raw_activities[:40]
        print(f"   Pre-selected {len(top_raw)} named candidates for Wikipedia enrichment")

        # ── Step 5: Enrich with Wikipedia ─────────────────────────────────────
        print("\n📚 Enriching top candidates with Wikipedia data...")
        enriched_activities = self._enrich_activities(top_raw)
        print(f"   Enriched {len(enriched_activities)} activities")

        # ── Step 6: Filter by constraints ─────────────────────────────────────
        print("\n⚖️ Filtering by constraints...")
        filtered_activities = self._filter_by_constraints(
            enriched_activities, budget, duration_days, interests, party_size
        )
        print(f"✅ {len(filtered_activities)} activities after filtering")

        if not filtered_activities:
            print("⚠️ Filter produced 0 results — returning all enriched activities")
            filtered_activities = enriched_activities[:25]

        # ── Step 7: Calculate distances ────────────────────────────────────────
        print("\n📍 Calculating distances between activities...")
        distances = self.distance_calc.calculate_all_distances(filtered_activities)
        print(f"   Calculated {len(distances)} distance pairs")

        # ── Step 8: Build result ───────────────────────────────────────────────
        grounding_data = GroundingData(
            activities=filtered_activities,
            distances=distances,
            neighborhoods=self._extract_neighborhoods(filtered_activities),
        )

        result = ResearchResult(
            destination=destination,
            search_date=datetime.now().isoformat()[:10],
            activities=filtered_activities,
            grounding=grounding_data,
            total_activities_found=len(raw_activities),
            feasible_activities=len(filtered_activities),
            budget_coverage=self._calculate_budget_coverage(filtered_activities),
            interest_coverage=self._calculate_interest_coverage(filtered_activities, interests),
        )

        planning_state.candidates = {
            "activities": [a.model_dump() for a in filtered_activities],
            "distances": distances,
            "neighborhoods": result.grounding.neighborhoods,
        }

        print("\n" + "=" * 80)
        print("✅ RESEARCH COMPLETE")
        print(f"   Cities searched: {[c[0] for c in all_coords]}")
        print(f"   Activities found: {len(filtered_activities)}")
        print(f"   Interest coverage: {result.interest_coverage}")
        print(f"   Budget coverage: {result.budget_coverage}")
        print("=" * 80 + "\n")

        return result

    def _extract_cities(self, destination: str) -> List[str]:
        """
        Parse a multi-city destination string into individual city names.

        Examples:
            "Jaipur and Jodhpur"          → ["Jaipur", "Jodhpur"]
            "Rajasthan covering Jaipur and Jodhpur" → ["Jaipur", "Jodhpur"]
            "Mumbai"                       → ["Mumbai"]
            "Delhi, Agra, Jaipur"          → ["Delhi", "Agra", "Jaipur"]
        """
        import re

        # Keywords that indicate a region/state rather than a city
        region_words = {
            "rajasthan", "kerala", "goa", "kashmir", "himachal", "uttarakhand",
            "maharashtra", "karnataka", "tamilnadu", "tamil", "andhra", "telangana",
            "gujarat", "punjab", "haryana", "uttar", "pradesh", "india",
            "north", "south", "east", "west", "covering", "including", "region",
            "circuit", "tour", "trip", "via", "through",
        }

        # Normalise separators: " and ", ",", "/", " & "
        normalised = re.sub(r"\s+and\s+|\s*[,/&]\s*", "|", destination, flags=re.IGNORECASE)
        parts = [p.strip() for p in normalised.split("|") if p.strip()]

        # Drop region-level words, keep proper city-like tokens
        cities = []
        for part in parts:
            tokens = part.split()
            # Remove stop/region words and keep capitalised words (likely city names)
            city_tokens = [t for t in tokens if t.lower() not in region_words and len(t) > 2]
            if city_tokens:
                city = " ".join(city_tokens)
                cities.append(city)

        # Deduplicate while preserving order
        seen: set = set()
        unique = []
        for c in cities:
            key = c.lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)

        # Fallback: use the full destination string if nothing sensible was found
        return unique if unique else [destination]
    
    def _map_interests_to_osm_tags(self, interests: List[str]) -> List[str]:
        """Map user interests to OpenStreetMap tags using substring matching.

        Includes India-specific tags (forts, palaces, temples) that are critical
        for destinations like Rajasthan, Kerala backwaters, etc.
        """

        mapping = {
            "food": [
                "amenity=restaurant",
                "amenity=cafe",
                "amenity=bar",
                "amenity=fast_food",
                "shop=supermarket",
            ],
            "culture": [
                "tourism=museum",
                "tourism=art_gallery",
                "historic=monument",
                "historic=fort",
                "historic=castle",
                "historic=palace",
                "historic=building",
                "historic=temple",
                "amenity=place_of_worship",
                "amenity=library",
            ],
            "cultural": [
                "tourism=museum",
                "tourism=art_gallery",
                "historic=monument",
                "historic=fort",
                "historic=castle",
                "historic=palace",
                "historic=building",
                "historic=temple",
                "tourism=attraction",
                "amenity=place_of_worship",
            ],
            "nature": [
                "leisure=park",
                "leisure=garden",
                "natural=water",
                "natural=lake",
                "leisure=nature_reserve",
                "leisure=swimming_pool",
            ],
            "adventure": [
                "tourism=tour_operator",
                "leisure=sports_centre",
                "sport=climbing",
            ],
            "relaxation": [
                "amenity=spa",
                "leisure=swimming_pool",
                "leisure=beach",
                "tourism=hotel",
            ],
            "shopping": [
                "shop=mall",
                "shop=market",
                "shop=supermarket",
                "shop=clothes",
            ],
            "iconic": [
                "tourism=attraction",
                "tourism=museum",
                "historic=monument",
                "historic=fort",
                "historic=castle",
                "historic=palace",
                "tourism=viewpoint",
            ],
            "attraction": [
                "tourism=attraction",
                "tourism=museum",
                "historic=monument",
                "historic=fort",
                "historic=castle",
                "historic=palace",
            ],
            # Family / kids — common in group travel
            "family": [
                "tourism=attraction",
                "leisure=park",
                "leisure=playground",
                "tourism=zoo",
                "tourism=museum",
                "amenity=restaurant",
            ],
            "kid": [
                "tourism=attraction",
                "leisure=park",
                "leisure=playground",
                "tourism=zoo",
                "tourism=museum",
            ],
            "historic": [
                "historic=fort",
                "historic=castle",
                "historic=palace",
                "historic=monument",
                "historic=building",
                "historic=temple",
                "tourism=museum",
            ],
            "heritage": [
                "historic=fort",
                "historic=castle",
                "historic=palace",
                "historic=monument",
                "historic=building",
                "tourism=attraction",
            ],
            "temple": [
                "amenity=place_of_worship",
                "historic=temple",
            ],
            "spiritual": [
                "amenity=place_of_worship",
                "historic=temple",
                "tourism=attraction",
            ],
        }

        tags: List[str] = []
        for interest in interests:
            interest_lower = interest.lower().strip()
            # Substring match — 'authentic food experiences' matches 'food'
            for key, key_tags in mapping.items():
                if key in interest_lower:
                    tags.extend(key_tags)

        unique_tags = list(dict.fromkeys(tags))  # Deduplicate preserving order

        # Always include a solid baseline for Indian destinations
        baseline = [
            "tourism=attraction",
            "amenity=restaurant",
            "historic=fort",
            "historic=monument",
            "historic=palace",
            "leisure=park",
        ]
        for tag in baseline:
            if tag not in unique_tags:
                unique_tags.append(tag)

        return unique_tags
    
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
        party_size: int,
    ) -> List[Activity]:
        """Filter activities — keep quality places, avoid only removing too-expensive ones.

        Previous version silently dropped all free activities that didn't match
        declared interests, which eliminated forts, monuments and parks entirely
        for trips where the LLM extracted vague interests like 'family-friendly'.
        """

        filtered = []

        # Daily per-person budget — guard against None/zero
        safe_days = duration_days or 3
        safe_party = party_size or 1
        daily_budget_per_person = budget / safe_days / safe_party

        # Allow activities that cost up to 150% of the daily per-person budget
        max_cost_per_activity = daily_budget_per_person * 1.5

        print(f"   Daily per person: ₹{daily_budget_per_person:.0f}")
        print(f"   Max cost per activity: ₹{max_cost_per_activity:.0f}")
        print(f"   Interests: {interests}")

        # Accommodation categories — never include as activities
        accommodation_categories = {"hotel", "hostel", "guest_house", "apartment", "motel"}

        for activity in activities:
            # 1. Always skip accommodation entries
            if activity.category in accommodation_categories:
                continue

            # 2. Cost guard — skip truly expensive outliers
            if activity.cost_per_person_inr > max_cost_per_activity:
                continue

            # 3. Tag interest matches (informational — no longer used as pass/fail gate)
            matches = self._get_matching_interests(activity, interests)
            activity.matches_interests = matches

            # 4. Keep everything that passes the cost check
            #    (free cultural sites — forts, parks, monuments — are always valid)
            filtered.append(activity)

        # Sort by composite score: interest relevance > rating > mild cost preference
        def score_activity(a: Activity) -> float:
            interest_score = len(a.matches_interests) * 100
            rating_score = a.rating * 20
            # Slight preference for attractions with an admission cost (signals quality)
            cost_signal = min(a.cost_per_person_inr, 500) * 0.05
            return interest_score + rating_score + cost_signal

        filtered.sort(key=score_activity, reverse=True)
        return filtered
    
    def _get_matching_interests(self, activity: Activity, interests: List[str]) -> List[str]:
        """Match interests using substring matching — handles phrases like 'authentic food experiences'."""

        category_interest_map: Dict[str, List[str]] = {
            # FOOD
            "restaurant": ["food"],
            "cafe": ["food"],
            "bar": ["food", "relaxation"],
            "fast_food": ["food"],
            "bakery": ["food"],
            "market": ["food", "shopping"],
            # CULTURE / HERITAGE
            "museum": ["culture", "cultural", "iconic", "historic", "heritage"],
            "art_gallery": ["culture", "cultural"],
            "monument": ["culture", "cultural", "iconic", "historic", "heritage"],
            "fort": ["culture", "cultural", "iconic", "historic", "heritage"],
            "castle": ["culture", "cultural", "iconic", "historic", "heritage"],
            "palace": ["culture", "cultural", "iconic", "historic", "heritage"],
            "archaeological_site": ["culture", "historic", "heritage"],
            "historical_building": ["culture", "cultural", "historic", "heritage"],
            "library": ["culture"],
            "temple": ["culture", "cultural", "spiritual", "temple"],
            "place_of_worship": ["culture", "spiritual", "temple"],
            "church": ["culture", "cultural"],
            "attraction": ["iconic", "attraction", "family", "kid"],
            # NATURE / RELAXATION
            "park": ["relaxation", "nature", "family", "kid"],
            "garden": ["relaxation", "nature"],
            "swimming_pool": ["relaxation", "family", "kid"],
            "spa": ["relaxation"],
            "beach": ["relaxation", "nature"],
            "viewpoint": ["relaxation", "nature", "iconic"],
            "nature_reserve": ["nature"],
            # SHOPPING
            "shopping": ["shopping"],
            "supermarket": ["shopping"],
            # FAMILY
            "zoo": ["family", "kid", "nature"],
            "playground": ["family", "kid"],
        }

        matches = []
        category_lower = activity.category.lower()
        if category_lower in category_interest_map:
            potential_keys = category_interest_map[category_lower]
            for interest in interests:
                interest_lower = interest.lower()
                for key in potential_keys:
                    if key in interest_lower:
                        matches.append(interest)
                        break

        return list(set(matches))
    
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