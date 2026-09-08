"""
Overpass API - Query OpenStreetMap data
Free, no API key needed!
This is the BEST for finding specific POIs (points of interest)
"""

import requests
from typing import List, Dict, Optional
import time


class OverpassAPI:
    """
    Overpass API for detailed POI search
    
    Queries OpenStreetMap using powerful query language
    Can find restaurants, hotels, museums, etc. with opening hours, ratings, etc.
    """
    
    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TripPlanner/1.0 (Educational)'
        })
        self.request_delay = 1  # Reduced: 1s between requests is enough
    
    def search_activities(
        self,
        lat: float,
        lng: float,
        tags: List[str],
        radius_meters: int = 5000
    ) -> List[Dict]:
        """
        Search for activities/POIs using OSM tags
        
        Args:
            lat, lng: Center coordinates
            tags: OSM tags like ["amenity=restaurant", "tourism=museum"]
            radius_meters: Search radius
        
        Returns:
            List of activities with details
        """
        print(f"🏪 Searching Overpass API for activities...")
        
        activities = []
        
        for tag in tags:
            try:
                # Build Overpass QL query
                parts = tag.split("=")
                key = parts[0]
                value = parts[1] if len(parts) > 1 else ""
                
                if value:
                    query = f"""
                    [out:json];
                    (
                        node["{key}"="{value}"](around:{radius_meters},{lat},{lng});
                        way["{key}"="{value}"](around:{radius_meters},{lat},{lng});
                        relation["{key}"="{value}"](around:{radius_meters},{lat},{lng});
                    );
                    out body geom;
                    """
                else:
                    query = f"""
                    [out:json];
                    (
                        node["{key}"](around:{radius_meters},{lat},{lng});
                        way["{key}"](around:{radius_meters},{lat},{lng});
                    );
                    out body geom;
                    """
                
                time.sleep(self.request_delay)  # Rate limiting
                
                print(f"   Querying: {tag}")
                response = self.session.post(
                    self.base_url,
                    data=query,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse results
                for element in data.get("elements", []):
                    activity = self._parse_element(element, tag)
                    if activity:
                        activities.append(activity)
            
            except requests.exceptions.Timeout:
                print(f"   ⏱️ Timeout for {tag}, retrying...")
                continue
            except Exception as e:
                print(f"   ⚠️ Error querying {tag}: {e}")
                continue
        
        print(f"   ✅ Found {len(activities)} activities")
        return activities

    def batch_search_activities(
        self,
        lat: float,
        lng: float,
        tags: List[str],
        radius_meters: int = 5000
    ) -> List[Dict]:
        """
        Fetch multiple OSM tags in a SINGLE Overpass request (much faster).
        """
        print(f"🏪 Batch querying Overpass API ({len(tags)} tags in 1 request)...")

        # Build union of all tag filters
        union_parts = []
        for tag in tags:
            parts = tag.split("=")
            if len(parts) == 2:
                key, value = parts
                union_parts.append(f'  node["{key}"="{value}"](around:{radius_meters},{lat},{lng});')
                union_parts.append(f'  way["{key}"="{value}"](around:{radius_meters},{lat},{lng});')

        query = "[out:json];\n(\n" + "\n".join(union_parts) + "\n);\nout body geom;"

        try:
            time.sleep(self.request_delay)
            response = self.session.post(self.base_url, data=query, timeout=45)
            response.raise_for_status()
            data = response.json()

            activities = []
            for element in data.get("elements", []):
                # Determine which tag this element matched
                elem_tags = element.get("tags", {})
                matched_tag = "tourism=hotel"
                for tag in tags:
                    k, _, v = tag.partition("=")
                    if elem_tags.get(k) == v:
                        matched_tag = tag
                        break
                activity = self._parse_element(element, matched_tag)
                if activity:
                    activities.append(activity)

            print(f"   ✅ Found {len(activities)} activities")
            return activities

        except Exception as e:
            print(f"   ⚠️ Batch query failed: {e}, falling back to sequential")
            return self.search_activities(lat, lng, tags, radius_meters)

    def _parse_element(self, element: Dict, tag: str) -> Optional[Dict]:
        """Parse Overpass element into activity format"""
        try:
            # Get coordinates
            lat = element.get("lat")
            lon = element.get("lon")
            
            # For ways/relations, get center
            if not lat or not lon:

                if "center" in element:
                    lat = element["center"].get("lat")
                    lon = element["center"].get("lon")
                elif "geometry" in element:
                    geom = element["geometry"][0]
                    lat = geom.get("lat")
                    lon = geom.get("lon")
            
            if not lat or not lon:
                return None
            
            tags = element.get("tags", {})
            name = tags.get("name", f"Place {element.get('id')}")
            
            # Parse category
            category = self._parse_category(tags)
            
            # Parse opening hours
            opening_hours = self._parse_opening_hours(tags.get("opening_hours", ""))
            
            # Estimate cost
            cost_per_person = self._estimate_cost(tags, category)
            
            # Get description
            description = tags.get("description", "")
            if not description:
                description = f"{category.title()} in {tags.get('addr:city', 'the area')}"
            
            return {
                "id": f"osm_{element.get('id')}",
                "name": name,
                "category": category,
                "address": tags.get("addr:street", "") + ", " + tags.get("addr:city", ""),
                "coordinates": {
                    "lat": lat,
                    "lng": lon
                },
                "area": tags.get("addr:suburb", tags.get("addr:district", "")),
                "duration_minutes": self._estimate_duration(category),
                "opening_hours": opening_hours,
                "cost_per_person_inr": cost_per_person,
                "cost_type": self._get_cost_type(cost_per_person),
                "rating": 4.0,  # OSM doesn't have ratings, Wikipedia does
                "review_count": 0,
                "description": description,
                "source": "openstreetmap",
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "tags": tags
            }
        
        except Exception as e:
            return None
    
    def _parse_category(self, tags: Dict) -> str:
        """Determine category from OSM tags"""
        
        category_map = {
            # Amenities
            "amenity=restaurant": "restaurant",
            "amenity=cafe": "cafe",
            "amenity=bar": "bar",
            "amenity=fast_food": "fast_food",
            "amenity=hotel": "hotel",
            "amenity=hostel": "hostel",
            "amenity=guest_house": "guest_house",
            "amenity=museum": "museum",
            "amenity=library": "library",
            "amenity=spa": "spa",
            "amenity=swimming_pool": "swimming_pool",
            
            # Tourism
            "tourism=museum": "museum",
            "tourism=art_gallery": "art_gallery",
            "tourism=hotel": "hotel",
            "tourism=guest_house": "guest_house",
            "tourism=information": "tourist_info",
            "tourism=viewpoint": "viewpoint",
            "tourism=attraction": "attraction",
            "tourism=tour_operator": "tour_operator",
            
            # Leisure
            "leisure=park": "park",
            "leisure=garden": "garden",
            "leisure=swimming_pool": "swimming_pool",
            "leisure=sports_centre": "sports_centre",
            
            # Shops
            "shop=mall": "shopping",
            "shop=supermarket": "supermarket",
            "shop=market": "market",
            
            # Historic
            "historic=monument": "monument",
            "historic=memorial": "monument",
            "historic=archaeological_site": "archaeological_site"
        }
        
        # Check exact matches
        for tag_key, tag_value in tags.items():
            full_tag = f"{tag_key}={tag_value}"
            if full_tag in category_map:
                return category_map[full_tag]
        
        # Default
        if "amenity" in tags:
            return tags["amenity"]
        if "tourism" in tags:
            return tags["tourism"]
        if "leisure" in tags:
            return tags["leisure"]
        
        return "attraction"
    
    def _parse_opening_hours(self, opening_hours_str: str) -> List[Dict]:
        """
        Parse OSM opening hours format
        Format: "Mo-Fr 09:00-18:00; Sa 10:00-14:00"
        """
        if not opening_hours_str:
            return []
        
        # Simplified parsing (real implementation would be more complex)
        result = []
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_abbr = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        
        # Simple case: same hours all days
        if ";" not in opening_hours_str and "-" in opening_hours_str:
            parts = opening_hours_str.split("-")
            if len(parts) == 2:
                open_time = parts[0].strip()
                close_time = parts[1].strip()
                for day in days:
                    result.append({
                        "day": day,
                        "open_time": open_time,
                        "close_time": close_time,
                        "is_open": True
                    })
        
        return result if result else []
    
    def _estimate_cost(self, tags: Dict, category: str) -> float:
        """Estimate cost in INR based on OSM data"""
        
        # Use price_level if available (0-4)
        price_level = tags.get("price_level")
        if price_level:
            level_map = {
                "1": 300,     # Budget
                "2": 600,     # Moderate
                "3": 1200,    # Expensive
                "4": 2500     # Very expensive
            }
            return level_map.get(str(price_level), 500)
        
        # Estimate based on category
        category_costs = {
            "restaurant": 400,
            "cafe": 150,
            "bar": 250,
            "fast_food": 100,
            "hotel": 1500,
            "hostel": 600,
            "guest_house": 1000,
            "museum": 300,
            "park": 0,
            "art_gallery": 250,
            "shopping": 0,
            "monument": 0,
            "viewpoint": 0
        }
        
        return category_costs.get(category, 0)
    
    def _get_cost_type(self, cost: float) -> str:
        """Categorize cost"""
        if cost == 0:
            return "free"
        elif cost < 200:
            return "budget"
        elif cost < 800:
            return "moderate"
        else:
            return "expensive"
    
    def _estimate_duration(self, category: str) -> int:
        """Estimate time to spend (in minutes)"""
        duration_map = {
            "museum": 120,
            "art_gallery": 90,
            "park": 90,
            "restaurant": 90,
            "cafe": 60,
            "bar": 60,
            "shopping": 120,
            "monument": 45,
            "viewpoint": 30,
            "hotel": 0,  # Accommodation, not an activity
            "hostel": 0,
            "guest_house": 0
        }
        return duration_map.get(category, 60)