"""
Wikipedia API - Get descriptions and information about places
Free! No API key needed.
"""

import requests
from typing import Optional, Dict
import time


class WikipediaAPI:
    """Get information from Wikipedia"""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TripPlanner/1.0 (Educational)'
        })
    
    def get_info(self, title: str) -> Optional[Dict]:
        """
        Get Wikipedia info about a place/person/topic
        
        Returns:
            {
                "title": "...",
                "summary": "...",
                "url": "..."
            }
        """
        try:
            params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
                "format": "json",
                "exintro": True,
                "exlimit": 1
            }
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page in pages.items():
                if page_id != "-1":  # Valid page
                    extract = page.get("extract", "")
                    
                    # Clean up
                    extract = extract[:300] + "..." if len(extract) > 300 else extract
                    
                    return {
                        "title": page.get("title", title),
                        "summary": extract,
                        "url": f"https://en.wikipedia.org/wiki/{page.get('title', '').replace(' ', '_')}"
                    }
            
            return None
        
        except Exception as e:
            return None