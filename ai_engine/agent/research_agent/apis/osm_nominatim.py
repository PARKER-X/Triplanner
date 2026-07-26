"""
OpenStreetMap Nominatim - Free geocoding and place search
No API key required!
"""

import requests
from typing import List, Dict, Optional, Tuple
import time


class NominatimAPI:
    """Free OpenStreetMap Nominatim API for geocoding and place search"""
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TripPlanner/1.0 (Educational)'
        })
        self.request_delay = 1  # Be nice to free API - 1 second between requests
    
    def get_location_coords(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Get latitude and longitude of a location
        
        Args:
            location_name: City name (e.g., "Mumbai", "Delhi")
        
        Returns:
            (lat, lng) tuple or None
        """
        print(f"📍 Getting coordinates for {location_name}...")
        
        try:
            url = f"{self.base_url}/search"
            params = {
                "q": location_name,
                "format": "json",
                "limit": 1
            }
            
            time.sleep(self.request_delay)  # Rate limiting
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                result = data[0]
                lat = float(result["lat"])
                lng = float(result["lon"])
                print(f"   ✅ Found: {location_name} at ({lat:.4f}, {lng:.4f})")
                return (lat, lng)
            
            print(f"   ❌ Could not find {location_name}")
            return None
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def search_nearby(
        self,
        lat: float,
        lng: float,
        search_term: str,
        radius_km: int = 5
    ) -> List[Dict]:
        """
        Search for places near a location
        Uses Nominatim reverse geocoding with custom search
        
        Limited functionality - for detailed search, use Overpass API
        """
        print(f"🔍 Searching nearby '{search_term}' within {radius_km}km...")
        
        try:
            url = f"{self.base_url}/search"
            params = {
                "q": f"{search_term} near {lat},{lng}",
                "format": "json",
                "limit": 10,
                "viewbox": f"{lng-0.05},{lat+0.05},{lng+0.05},{lat-0.05}"
            }
            
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for result in data:
                results.append({
                    "name": result.get("name", ""),
                    "address": result.get("address", ""),
                    "lat": float(result.get("lat", 0)),
                    "lng": float(result.get("lon", 0)),
                    "type": result.get("type", ""),
                    "importance": float(result.get("importance", 0))
                })
            
            print(f"   Found {len(results)} places")
            return results
        
        except Exception as e:
            print(f"   Error: {e}")
            return []
    
    def get_address_details(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Get detailed address information for coordinates
        """
        try:
            url = f"{self.base_url}/reverse"
            params = {
                "lat": lat,
                "lon": lng,
                "format": "json"
            }
            
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return {
                "address": data.get("address", {}),
                "name": data.get("name", ""),
                "area": data.get("address", {}).get("suburb", "")
            }
        
        except Exception as e:
            return None