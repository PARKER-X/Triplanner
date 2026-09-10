"""
Overpass API - Query OpenStreetMap data
Free, no API key needed!
This is the BEST for finding specific POIs (points of interest)
"""

import logging
import time
from typing import List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 5    # seconds to establish TCP connection
_READ_TIMEOUT = 30      # seconds to wait for the response body


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "TripPlanner/1.0 (Educational)"})
    retry = Retry(
        total=2,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class OverpassAPI:
    """
    Overpass API for detailed POI search

    Queries OpenStreetMap using powerful query language
    Can find restaurants, hotels, museums, etc. with opening hours, ratings, etc.
    """

    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.session = _make_session()
        self.request_delay = 1  # 1s between requests to respect the free API
    
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

                time.sleep(self.request_delay)

                print(f"   Querying: {tag}")
                response = self.session.post(
                    self.base_url,
                    data=query,
                    timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                )
                response.raise_for_status()

                data = response.json()
                for element in data.get("elements", []):
                    activity = self._parse_element(element, tag)
                    if activity:
                        activities.append(activity)

            except requests.exceptions.Timeout:
                logger.warning("Overpass timeout for tag '%s' — skipping", tag)
                continue
            except Exception as e:
                logger.warning("Overpass error for tag '%s': %s", tag, e)
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
            response = self.session.post(
                self.base_url,
                data=query,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT + 15),  # extra room for large queries
            )
            response.raise_for_status()
            data = response.json()

            activities = []
            for element in data.get("elements", []):
                elem_tags = element.get("tags", {})
                matched_tag = "tourism=attraction"
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

        except requests.exceptions.Timeout:
            logger.warning("Overpass batch query timed out — falling back to sequential")
            return self.search_activities(lat, lng, tags, radius_meters)
        except Exception as e:
            logger.warning("Overpass batch query failed (%s) — falling back to sequential", e)
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
            "amenity=place_of_worship": "place_of_worship",
            
            # Tourism
            "tourism=museum": "museum",
            "tourism=art_gallery": "art_gallery",
            "tourism=hotel": "hotel",
            "tourism=guest_house": "guest_house",
            "tourism=information": "tourist_info",
            "tourism=viewpoint": "viewpoint",
            "tourism=attraction": "attraction",
            "tourism=tour_operator": "tour_operator",
            "tourism=zoo": "zoo",
            
            # Leisure
            "leisure=park": "park",
            "leisure=garden": "garden",
            "leisure=swimming_pool": "swimming_pool",
            "leisure=sports_centre": "sports_centre",
            "leisure=playground": "playground",
            "leisure=nature_reserve": "nature_reserve",
            
            # Shops
            "shop=mall": "shopping",
            "shop=supermarket": "supermarket",
            "shop=market": "market",
            "shop=clothes": "shopping",
            
            # Historic — including India-specific fort/palace/castle/temple
            "historic=monument": "monument",
            "historic=memorial": "monument",
            "historic=archaeological_site": "archaeological_site",
            "historic=fort": "fort",
            "historic=castle": "castle",
            "historic=palace": "palace",
            "historic=building": "historical_building",
            "historic=temple": "temple",
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
            "monument": 50,
            "viewpoint": 0,
            # India-specific
            "fort": 500,
            "castle": 500,
            "palace": 600,
            "temple": 0,
            "place_of_worship": 0,
            "historical_building": 100,
            "archaeological_site": 300,
            "zoo": 300,
            "nature_reserve": 0,
            "playground": 0,
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
            # India-specific
            "fort": 150,
            "castle": 150,
            "palace": 120,
            "temple": 60,
            "place_of_worship": 45,
            "historical_building": 60,
            "archaeological_site": 90,
            "zoo": 120,
            "nature_reserve": 90,
            "playground": 60,
            # Accommodation (not activities)
            "hotel": 0,
            "hostel": 0,
            "guest_house": 0,
        }
        return duration_map.get(category, 60)