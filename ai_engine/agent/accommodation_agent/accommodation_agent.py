import json
import os
import uuid
from typing import List, Dict, Any
from .schema import Accommodation, AccommodationResult
from ai_engine.schemas.planning_state import PlanningState
from ai_engine.core.llm.base import LLMProvider
from ai_engine.agent.research_agent.apis.overpass import OverpassAPI
from ai_engine.agent.research_agent.apis.osm_nominatim import NominatimAPI
from ai_engine.agent.research_agent.apis.wikipedia import WikipediaAPI

class AccommodationAgent:
    def __init__(self, llm: LLMProvider = None):
        print("🏨 Initializing Accommodation Agent")
        self.llm = llm
        
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
        with open(prompt_path, 'r') as f:
            self.prompt = f.read()
            
        self.overpass = OverpassAPI()
        self.nominatim = NominatimAPI()
        self.wikipedia = WikipediaAPI()
        
    def run(self, planning_state: PlanningState) -> AccommodationResult:
        print("🔍 Extracting trip details for accommodation")
        destination = planning_state.get_destination()
        budget = planning_state.get_budget()
        duration_days = planning_state.get_duration_days()
        party_size = planning_state.get_party_size()
        
        print(f"💰 Allocating budget for {duration_days} nights, {party_size} people")
        total_nights = max(1, duration_days - 1)
        budget_allocated = budget * 0.25
        budget_per_night = budget_allocated / total_nights
        
        print(f"📍 Getting coordinates for destination: {destination}")
        coords = self.nominatim.get_location_coords(destination)
        if not coords:
            lat, lng = None, None
        else:
            lat, lng = coords
        
        if not lat or not lng:
            print("⚠️ Could not find destination coordinates, using fallback.")
            fallback = self._create_fallback(destination, budget_per_night)
            planning_state.accommodation = fallback.model_dump()
            planning_state.accommodation_alternatives = []
            return AccommodationResult(
                destination=destination,
                selected=fallback,
                alternatives=[],
                budget_allocated=budget_allocated,
                budget_per_night=budget_per_night,
                total_nights=total_nights
            )
            
        print("🔎 Searching for accommodations via Overpass")
        tags = ['tourism=hotel', 'tourism=guest_house', 'tourism=hostel', 'tourism=apartment']
        raw_results = self.overpass.search_activities(lat, lng, tags, radius_meters=5000)
        
        options: List[Accommodation] = []
        for result in raw_results:
            try:
                # Infer type from category field set by Overpass parser
                acc_type = result.get('category', 'hotel')
                if acc_type == 'hotel':
                    cost = 2000.0
                elif acc_type == 'guest_house':
                    cost = 1200.0
                elif acc_type == 'hostel':
                    cost = 600.0
                elif acc_type == 'apartment':
                    cost = 1500.0
                else:
                    cost = 2000.0
                    
                if cost > budget_per_night:
                    continue
                    
                rating = 4.0 # Default rating
                centrality = 0.7 # Default centrality
                budget_fit = 1.0 - (cost / budget_per_night) if budget_per_night > 0 else 0
                
                score = (0.4 * budget_fit) + (0.3 * (rating / 5)) + (0.3 * centrality)
                
                acc = Accommodation(
                    id=str(uuid.uuid4()),
                    name=result.get('name', f"Unknown {acc_type.title()}"),
                    type=acc_type,
                    coordinates=result.get('coordinates', {"lat": lat, "lng": lng}),
                    cost_per_night=cost,
                    area=result.get('area', 'Central'),
                    address=result.get('address', destination),
                    amenities=["Wi-Fi", "Air Conditioning"] if cost > 1000 else ["Wi-Fi"],
                    rating=rating,
                    description=f"A lovely {acc_type} located in {destination}.",
                    source="OSM",
                    suitability_score=score
                )
                options.append(acc)
            except Exception as e:
                print(f"⚠️ Error processing accommodation: {e}")
                continue
                
        if not options:
            print("⚠️ No suitable accommodations found, using fallback.")
            fallback = self._create_fallback(destination, budget_per_night, lat, lng)
            options.append(fallback)
            
        print(f"✨ Enhancing top {min(len(options), 5)} options with Wikipedia data")
        options = sorted(options, key=lambda x: x.suitability_score, reverse=True)
        top_options = options[:5]
        
        for opt in top_options:
            try:
                wiki_info = self.wikipedia.get_info(opt.name)
                if wiki_info and wiki_info.get('summary'):
                    opt.description = wiki_info['summary'][:200] + "..."
            except Exception:
                pass
                
        print("🏆 Selecting the best accommodation option")
        selected = top_options[0]
        alternatives = top_options[1:]
        
        planning_state.accommodation = selected.model_dump()
        planning_state.accommodation_alternatives = [alt.model_dump() for alt in alternatives]
        
        print(f"✅ Selected accommodation: {selected.name} at ₹{selected.cost_per_night}/night")
        
        return AccommodationResult(
            destination=destination,
            selected=selected,
            alternatives=alternatives,
            budget_allocated=budget_allocated,
            budget_per_night=budget_per_night,
            total_nights=total_nights
        )

    def _create_fallback(self, destination: str, budget: float, lat: float = 0.0, lng: float = 0.0) -> Accommodation:
        return Accommodation(
            id=str(uuid.uuid4()),
            name="Generic Hotel",
            type="hotel",
            coordinates={"lat": lat, "lng": lng},
            cost_per_night=min(2000.0, budget),
            area="City Center",
            address=destination,
            amenities=["Wi-Fi"],
            rating=3.0,
            description="A generic fallback hotel.",
            source="Fallback",
            suitability_score=0.5
        )
