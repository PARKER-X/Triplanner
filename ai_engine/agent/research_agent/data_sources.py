"""
Data sources for research agent
- OpenStreetMap (Nominatim) - FREE
- Overpass API - FREE
- Wikipedia API - FREE
- No API keys required!
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import json


class OpenStreetMapAPI:
    """
    Free OpenStreetMap API using Nominatim (search) and Overpass (POI data)
    No API key required!
    
    Nominatim: For searching locations and addresses
    Overpass: For finding specific points of interest (restaurants, hotels, etc.)
    """
    
    def __init__(self):
        """Initialize with OSM endpoints"""
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.wikipedia_url = "https://en.wikipedia.org/w/api.php"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TripPlanner/1.0 (Educational Project)'
        })
    
    def search_places(
        self,
        location: str,
        interests: List[str],
        budget: float,
        party_size: int = 4
    ) -> List[Dict]:
        """
        Search for places/landmarks/attractions using Overpass API
        
        Args:
            location: City name (e.g., "Mumbai")
            interests: User priorities (e.g., ["food", "culture"])
            budget: Total budget in INR
            party_size: Number of people
        
        Returns:
            List of places with details
        """
        print(f"🔍 Searching OpenStreetMap for {location}...")
        
        # First, get coordinates of the city
        city_coords = self._get_location_coords(location)
        if not city_coords:
            print(f"❌ Could not find {location}")
            return []
        
        lat, lng = city_coords
        print(f"   Found {location} at ({lat}, {lng})")
        
        places = []
        
        # Map interests to OSM tags
        osm_queries = self._map_interests_to_osm_tags(interests, "places")
        
        for query in osm_queries:
            results = self._query_overpass(lat, lng, query, radius=5000)  # 5km radius
            places.extend(results)
        
        # Remove duplicates
        seen = set()
        unique_places = []
        for place in places:
            place_id = place.get("id")
            if place_id not in seen:
                seen.add(place_id)
                unique_places.append(place)
        
        # Filter and enrich
        enriched_places = []
        for place in unique_places[:30]:
            enriched = self._enrich_place_data(place, location)
            if enriched:
                enriched_places.append(enriched)
        
        print(f"   Found {len(enriched_places)} places")
        return enriched_places
    
    def search_activities(
        self,
        location: str,
        interests: List[str],
        budget: float,
        party_size: int = 4
    ) -> List[Dict]:
        """
        Search for activities/experiences (restaurants, tours, etc.)
        """
        print(f"🔍 Searching for activities in {location}...")
        
        city_coords = self._get_location_coords(location)
        if not city_coords:
            return []
        
        lat, lng = city_coords
        
        activities = []
        osm_queries = self._map_interests_to_osm_tags(interests, "activities")
        
        for query in osm_queries:
            results = self._query_overpass(lat, lng, query, radius=3000)
            activities.extend(results)
        
        # Remove duplicates
        seen = set()
        unique_activities = []
        for activity in activities:
            if activity.get("id") not in seen:
                seen.add(activity.get("id"))
                unique_activities.append(activity)
        
        # Enrich with Wikipedia info
        enriched_activities = []
        for activity in unique_activities[:25]:
            enriched = self._enrich_activity_data(activity, location)
            if enriched:
                enriched_activities.append(enriched)
        
        print(f"   Found {len(enriched_activities)} activities")
        return enriched_activities
    
    def search_accommodations(
        self,
        location: str,
        budget: float,
        nights: int = 3,
        party_size: int = 4
    ) -> List[Dict]:
        """
        Search for hotels/accommodations
        """
        print(f"🔍 Searching for accommodations in {location}...")
        
        city_coords = self._get_location_coords(location)
        if not city_coords:
            return []
        
        lat, lng = city_coords
        
        # Query for hotels, guest houses, hostels, airbnb
        queries = [
            '["tourism"="hotel"]',
            '["tourism"="guest_house"]',
            '["tourism"="hostel"]',
            '["tourism"="apartment"]'
        ]
        
        accommodations = []
        for query in queries:
            results = self._query_overpass(lat, lng, query, radius=5000)
            accommodations.extend(results)
        
        # Remove duplicates
        seen = set()
        unique = []
        for acc in accommodations:
            if acc.get("id") not in seen:
                seen.add(acc.get("id"))
                unique.append(acc)
        
        # Enrich with data
        enriched = []
        max_per_night = (budget * 0.25) / nights / party_size
        
        for accommodation in unique[:20]:
            enriched_acc = self._enrich_accommodation_data(accommodation, max_per_night)
            if enriched_acc:
                enriched.append(enriched_acc)
        
        print(f"   Found {len(enriched)} accommodations")
        return enriched
    
    def search_transport(
        self,
        source: str,
        destination: str,
        travelers: int = 4
    ) -> List[Dict]:
        """
        Search for transport options
        Uses manually researched data since OSM doesn't have real-time transport
        """
        print(f"🚗 Researching transport from {source} to {destination}...")
        
        transport_options = self._get_transport_data(source, destination, travelers)
        print(f"   Found {len(transport_options)} transport options")
        return transport_options
    
    def _get_location_coords(self, location: str) -> Optional[tuple]:
        """
        Get latitude and longitude of a location using Nominatim
        Returns: (lat, lng) or None
        """
        try:
            url = f"{self.nominatim_url}/search"
            params = {
                "q": location,
                "format": "json",
                "limit": 1
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                result = data[0]
                return (float(result["lat"]), float(result["lon"]))
            
            return None
        
        except Exception as e:
            print(f"⚠️ Error getting location: {e}")
            return None
    
    def _query_overpass(self, lat: float, lng: float, query: str, radius: int = 5000) -> List[Dict]:
        """
        Query Overpass API for POIs (Points of Interest)
        
        Args:
            lat, lng: Center coordinates
            query: OSM tag query (e.g., '["tourism"="museum"]')
            radius: Search radius in meters
        """
        try:
            # Build Overpass QL query
            overpass_query = f"""
            [out:json];
            (
                node{query}(around:{radius},{lat},{lng});
                way{query}(around:{radius},{lat},{lng});
            );
            out center;
            """
            
            response = self.session.post(
                self.overpass_url,
                data=overpass_query,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to our format
            places = []
            for element in data.get("elements", []):
                place = self._parse_overpass_element(element)
                if place:
                    places.append(place)
            
            return places
        
        except Exception as e:
            print(f"⚠️ Error querying Overpass: {e}")
            return []
    
    def _parse_overpass_element(self, element: dict) -> Optional[Dict]:
        """Parse Overpass element into our place format"""
        try:
            # Get coordinates
            lat = element.get("lat")
            lon = element.get("lon")
            
            # For ways, use center
            if not lat or not lon:
                center = element.get("center")
                if center:
                    lat = center.get("lat")
                    lon = center.get("lon")
            
            if not lat or not lon:
                return None
            
            tags = element.get("tags", {})
            name = tags.get("name", f"Place {element.get('id')}")
            
            return {
                "id": f"osm_{element.get('id')}",
                "name": name,
                "category": self._infer_category_from_tags(tags),
                "location": {
                    "lat": lat,
                    "lng": lon,
                    "area": ""
                },
                "cost_per_person": 0,  # Default free
                "duration_hours": self._estimate_duration(tags),
                "rating": 4.0,  # OSM doesn't have ratings, default to 4
                "reviews_count": 0,
                "best_time": "morning",
                "opening_hours": tags.get("opening_hours", ""),
                "address": tags.get("addr:full", ""),
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "source": "openstreetmap"
            }
        
        except Exception as e:
            return None
    
    def _enrich_place_data(self, place: dict, location: str) -> Optional[Dict]:
        """Enrich place data with Wikipedia info"""
        try:
            # Try to get Wikipedia info
            wiki_data = self._get_wikipedia_info(place.get("name", ""))
            
            if wiki_data:
                place["description"] = wiki_data.get("description", "")
                place["rating"] = 4.5 if wiki_data else 4.0
                place["reviews_count"] = 100  # Estimate
            
            return place
        
        except:
            return place
    
    def _enrich_activity_data(self, activity: dict, location: str) -> Optional[Dict]:
        """Enrich activity data"""
        try:
            # Estimate cost based on type
            activity_type = activity.get("category", "").lower()
            
            cost_estimates = {
                "restaurant": 300,
                "cafe": 150,
                "bar": 200,
                "pub": 250,
                "fast_food": 100,
                "food": 250,
                "tourism": 400,
                "tour": 500
            }
            
            for key, cost in cost_estimates.items():
                if key in activity_type:
                    activity["cost_per_person"] = cost
                    break
            
            activity["group_friendly"] = True
            activity["duration_hours"] = 2
            
            # Get Wikipedia info
            wiki_data = self._get_wikipedia_info(activity.get("name", ""))
            if wiki_data:
                activity["description"] = wiki_data.get("description", "")
            
            return activity
        
        except:
            return activity
    
    def _enrich_accommodation_data(self, accommodation: dict, max_price: float) -> Optional[Dict]:
        """Enrich accommodation data"""
        try:
            # Estimate cost based on type
            acc_type = accommodation.get("category", "").lower()
            
            cost_estimates = {
                "hostel": 600,
                "guest_house": 1000,
                "hotel": 1500,
                "apartment": 1200
            }
            
            estimated_cost = 1000  # Default
            for key, cost in cost_estimates.items():
                if key in acc_type:
                    estimated_cost = cost
                    break
            
            # Check budget fit
            if estimated_cost > max_price:
                return None
            
            accommodation["cost_per_night"] = estimated_cost
            accommodation["occupancy"] = "double"
            accommodation["capacity"] = 2
            accommodation["amenities"] = ["wifi", "bathroom"]
            accommodation["group_suitability"] = True
            
            return accommodation
        
        except:
            return None
    
    def _get_wikipedia_info(self, title: str) -> Optional[Dict]:
        """Get info from Wikipedia"""
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
                "format": "json",
                "exintro": True
            }
            
            response = self.session.get(self.wikipedia_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page in pages.items():
                if page_id != "-1":  # Valid page
                    return {
                        "title": page.get("title"),
                        "description": page.get("extract", "")[:200]
                    }
            
            return None
        
        except:
            return None
    
    def _map_interests_to_osm_tags(self, interests: List[str], query_type: str) -> List[str]:
        """Map interests to OpenStreetMap tags"""
        
        mapping = {
            "places": {
                "food": [
                    '["amenity"="restaurant"]',
                    '["amenity"="cafe"]',
                    '["shop"="bakery"]'
                ],
                "culture": [
                    '["tourism"="museum"]',
                    '["amenity"="place_of_worship"]',
                    '["historic"="monument"]'
                ],
                "nature": [
                    '["leisure"="park"]',
                    '["natural"="forest"]',
                    '["natural"="water"]'
                ],
                "adventure": [
                    '["tourism"="adventure"]',
                    '["leisure"="sports_centre"]'
                ],
                "shopping": [
                    '["shop"="mall"]',
                    '["shop"="market"]'
                ],
                "relaxation": [
                    '["amenity"="spa"]',
                    '["leisure"="swimming_pool"]'
                ]
            },
            "activities": {
                "food": [
                    '["amenity"="restaurant"]',
                    '["amenity"="cafe"]',
                    '["amenity"="fast_food"]'
                ],
                "culture": [
                    '["tourism"="museum"]',
                    '["tourism"="gallery"]'
                ],
                "adventure": [
                    '["tourism"="adventure"]'
                ],
                "relaxation": [
                    '["amenity"="spa"]'
                ]
            }
        }
        
        queries = []
        for interest in interests:
            interest_lower = interest.lower()
            if interest_lower in mapping.get(query_type, {}):
                queries.extend(mapping[query_type][interest_lower])
        
        return queries if queries else ['["tourism"="attraction"]']
    
    def _infer_category_from_tags(self, tags: dict) -> str:
        """Infer category from OSM tags"""
        category_map = {
            "museum": "museum",
            "place_of_worship": "temple",
            "monument": "monument",
            "park": "park",
            "restaurant": "restaurant",
            "cafe": "cafe",
            "hotel": "hotel",
            "guest_house": "guest_house",
            "hostel": "hostel"
        }
        
        for key, value in tags.items():
            for cat_key, cat_value in category_map.items():
                if cat_key in value.lower():
                    return cat_value
        
        return tags.get("tourism", "attraction")
    
    def _estimate_duration(self, tags: dict) -> float:
        """Estimate visit duration based on type"""
        duration_map = {
            "museum": 2.0,
            "temple": 1.5,
            "park": 1.5,
            "restaurant": 1.5,
            "cafe": 1.0
        }
        
        for key, value in tags.items():
            for dur_key, dur_value in duration_map.items():
                if dur_key in value.lower():
                    return dur_value
        
        return 1.0
    
    def _get_transport_data(self, source: str, destination: str, travelers: int) -> List[Dict]:
        """Get transport data (manually researched)"""
        
        routes = {
            ("delhi", "mumbai"): [
                {
                    "type": "flight",
                    "cost_per_person": 3000,
                    "duration_hours": 2,
                    "comfort": "economy",
                    "pros": ["Fast", "Comfortable"],
                    "cons": ["Expensive"]
                },
                {
                    "type": "train",
                    "cost_per_person": 800,
                    "duration_hours": 16,
                    "comfort": "comfortable",
                    "pros": ["Affordable", "Scenic", "Good food"],
                    "cons": ["Time-consuming"]
                },
                {
                    "type": "bus",
                    "cost_per_person": 500,
                    "duration_hours": 20,
                    "comfort": "economy",
                    "pros": ["Cheapest", "Direct"],
                    "cons": ["Long journey"]
                }
            ],
            ("delhi", "jaipur"): [
                {
                    "type": "train",
                    "cost_per_person": 200,
                    "duration_hours": 4,
                    "comfort": "comfortable",
                    "pros": ["Quick", "Affordable"],
                    "cons": ["Limited trains"]
                },
                {
                    "type": "bus",
                    "cost_per_person": 150,
                    "duration_hours": 5.5,
                    "comfort": "economy",
                    "pros": ["Very cheap", "Frequent"],
                    "cons": ["Long drive"]
                }
            ],
            ("mumbai", "goa"): [
                {
                    "type": "flight",
                    "cost_per_person": 2500,
                    "duration_hours": 1,
                    "comfort": "economy",
                    "pros": ["Very fast"],
                    "cons": ["Expensive"]
                },
                {
                    "type": "train",
                    "cost_per_person": 600,
                    "duration_hours": 10,
                    "comfort": "comfortable",
                    "pros": ["Affordable", "Scenic"],
                    "cons": ["Long journey"]
                }
            ]
        }
        
        source_norm = source.lower().strip()
        dest_norm = destination.lower().strip()
        route_key = (source_norm, dest_norm)
        
        transport_data = routes.get(route_key, [])
        
        if not transport_data:
            print(f"⚠️ No specific data for {source} -> {destination}, using generic")
            transport_data = [
                {
                    "type": "flight",
                    "cost_per_person": 3500,
                    "duration_hours": 2,
                    "comfort": "economy",
                    "pros": ["Fast"],
                    "cons": ["Expensive"]
                },
                {
                    "type": "train",
                    "cost_per_person": 1000,
                    "duration_hours": 24,
                    "comfort": "comfortable",
                    "pros": ["Affordable"],
                    "cons": ["Time-consuming"]
                }
            ]
        
        # Convert to our format
        result = []
        for t in transport_data:
            result.append({
                "type": t["type"],
                "cost_per_person": t["cost_per_person"],
                "cost_total_group": t["cost_per_person"] * travelers,
                "duration_hours": t["duration_hours"],
                "comfort_level": t["comfort"],
                "feasibility": self._get_feasibility(t["cost_per_person"] * travelers, 10000),
                "pros": t["pros"],
                "cons": t["cons"],
                "booking_url": self._get_booking_url(t["type"]),
                "source": "manually_researched"
            })
        
        return result
    
    def _get_feasibility(self, cost: float, budget: float) -> str:
        """Check feasibility"""
        if cost > budget * 0.4:
            return "over_budget"
        elif cost > budget * 0.3:
            return "tight"
        else:
            return "within_budget"
    
    def _get_booking_url(self, transport_type: str) -> Optional[str]:
        """Get booking URL"""
        urls = {
            "flight": "https://www.skyscanner.com",
            "train": "https://www.irctc.co.in",
            "bus": "https://www.redbus.in"
        }
        return urls.get(transport_type)


# Use this as the default
DataSource = OpenStreetMapAPI