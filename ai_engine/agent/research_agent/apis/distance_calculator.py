"""
Calculate distances between coordinates
Uses Haversine formula - no API needed, fully local!
"""

import math
from typing import Tuple, List, Dict, Union
from dataclasses import dataclass


@dataclass
class Coordinates:
    lat: float
    lng: float


class DistanceCalculator:
    """Calculate distances between coordinates"""
    
    EARTH_RADIUS_KM = 6371
    
    @staticmethod
    def haversine(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        
        Returns:
            Distance in kilometers
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = DistanceCalculator.EARTH_RADIUS_KM * c
        return distance
    
    @staticmethod
    def estimate_travel_time(
        distance_km: float,
        mode: str = "walking"
    ) -> int:
        """
        Estimate travel time based on distance and mode
        
        Args:
            distance_km: Distance in kilometers
            mode: "walking", "cycling", "transit", "auto"
        
        Returns:
            Travel time in minutes
        """
        # Average speeds (km/hr)
        speeds = {
            "walking": 4,
            "cycling": 15,
            "transit": 20,  # Average with stops
            "auto": 30
        }
        
        speed = speeds.get(mode, 20)
        hours = distance_km / speed
        minutes = int(hours * 60)
        
        # Add buffer for stops, traffic, etc.
        if mode == "transit":
            minutes += 5  # Add 5 min for waiting
        elif mode == "auto":
            minutes += int(distance_km)  # Add traffic buffer
        
        return max(5, minutes)  # Minimum 5 minutes
    
    @staticmethod
    def calculate_all_distances(
        activities: List[Union[Dict, object]]
    ) -> List[Dict]:
        """
        Calculate distances between all pairs of activities
        
        FIXED: Handle both Activity objects and dictionaries
        
        Returns:
            List of distance info
        """
        distances = []
        
        for i, activity_a in enumerate(activities):
            # Extract coordinates - handle both dict and Activity objects
            coords_a = DistanceCalculator._get_coordinates(activity_a)
            id_a = DistanceCalculator._get_id(activity_a)
            
            if not coords_a or not id_a:
                continue
            
            for activity_b in activities[i+1:]:
                coords_b = DistanceCalculator._get_coordinates(activity_b)
                id_b = DistanceCalculator._get_id(activity_b)
                
                if not coords_b or not id_b:
                    continue
                
                distance_km = DistanceCalculator.haversine(
                    coords_a["lat"],
                    coords_a["lng"],
                    coords_b["lat"],
                    coords_b["lng"]
                )
                
                # Estimate for walking (default)
                travel_time = DistanceCalculator.estimate_travel_time(distance_km, "walking")
                
                distances.append({
                    "from_activity": id_a,
                    "to_activity": id_b,
                    "distance_km": round(distance_km, 2),
                    "travel_time_minutes": travel_time,
                    "travel_mode": "walking"
                })
        
        return distances
    
    @staticmethod
    def _get_coordinates(activity: Union[Dict, object]) -> Dict:
        """
        Extract coordinates from either dict or Activity object
        
        Returns:
            {"lat": float, "lng": float} or None
        """
        try:
            if isinstance(activity, dict):
                coords = activity.get("coordinates", {})
                return {
                    "lat": coords.get("lat"),
                    "lng": coords.get("lng")
                }
            else:
                # Activity object
                coords = activity.coordinates
                return {
                    "lat": coords.get("lat") if isinstance(coords, dict) else coords.lat,
                    "lng": coords.get("lng") if isinstance(coords, dict) else coords.lng
                }
        except:
            return None
    
    @staticmethod
    def _get_id(activity: Union[Dict, object]) -> str:
        """
        Extract ID from either dict or Activity object
        """
        try:
            if isinstance(activity, dict):
                return activity.get("id", "")
            else:
                # Activity object
                return activity.id
        except:
            return ""