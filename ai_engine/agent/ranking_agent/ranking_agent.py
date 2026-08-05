"""
Ranking Agent — Curate and prioritize activities for the trip.

Priority system (user's requirement):
  P1 (60%): Famous landmarks, monuments, iconic attractions
  P2 (20%): Iconic food spots, cafes, restaurants  
  P3 (15%): Cultural experiences — museums, temples, galleries
  P4 (5%):  Nature/relaxation — only if user explicitly asks

Key insight: Wikipedia presence = the place is actually famous.
A swimming pool with no Wikipedia page is NOT a tourist attraction.
"""

from typing import List, Dict, Optional
from ai_engine.agent.research_agent.schema import Activity


class RankingAgent:
    """
    Ranking Agent — Fame-weighted curation with quota strategy.

    Goal:
    - 60% famous landmarks (monuments, iconic attractions)
    - 20% famous food/cafes
    - 15% cultural (museums, temples, galleries)
    - 5% filler (nature/relaxation if user wants)
    - Remove low-value generic places
    - Return curated top activities for planning
    """

    # ── Category Classification ─────────────────────────────
    LANDMARK_CATEGORIES = {
        "monument", "attraction", "viewpoint",
        "archaeological_site", "memorial",
    }

    CULTURAL_CATEGORIES = {
        "museum", "art_gallery", "library",
        "temple", "church",
    }

    FOOD_CATEGORIES = {
        "restaurant", "cafe", "bar",
        "fast_food", "bakery", "market",
    }

    NATURE_CATEGORIES = {
        "park", "garden", "beach",
    }

    PENALIZED_CATEGORIES = {
        "swimming_pool", "sports_centre", "supermarket",
        "generic", "unknown", "tourist_info",
        "tour_operator", "hotel", "hostel",
        "guest_house", "apartment",
    }

    def __init__(self):
        print("✅ Ranking Agent initialized (fame-weighted, landmark-first)")

    def run(self, planning_state) -> None:
        """
        Rank and curate activities in planning_state.candidates.

        Mutates planning_state.candidates['activities'] in place.
        """

        candidates = planning_state.candidates.get("activities", [])

        if not candidates:
            print("⚠️  No candidates to rank")
            return planning_state

        print(f"\n🏆 RANKING AGENT: Curating {len(candidates)} activities...")

        # Convert dicts to Activity objects
        activities = []
        for c in candidates:
            try:
                activities.append(Activity(**c))
            except Exception:
                continue

        # Step 1: Score every activity
        scored = self._score_activities(activities)

        # Step 2: Apply quota strategy
        duration_days = planning_state.get_duration_days()
        target_count = self._calculate_target_count(duration_days)
        curated = self._apply_quota_strategy(scored, target_count)

        # Step 3: Write back
        planning_state.candidates["activities"] = [
            a.model_dump() for a in curated
        ]

        # Report
        cats = self._count_categories(curated)
        print(f"   ✅ Curated to {len(curated)} activities for {duration_days}-day trip")
        print(f"      🏛️ Landmarks: {cats['landmarks']}")
        print(f"      🍽️ Food/Cafe: {cats['food']}")
        print(f"      🎭 Cultural:  {cats['cultural']}")
        print(f"      🌳 Nature:    {cats['nature']}")
        print(f"      📍 Other:     {cats['other']}")

        return planning_state

    # ─── Scoring ────────────────────────────────────────────

    def _score_activities(self, activities: List[Activity]) -> List[Activity]:
        """Score each activity by fame + quality + category."""

        scored_pairs = []

        for a in activities:
            score = 0.0
            cat = a.category.lower().strip()

            # ── Fame Signal: Wikipedia presence ──
            if getattr(a, "has_wikipedia", False):
                score += 150

            # Wikipedia-enriched descriptions are longer and more meaningful
            if a.description and len(a.description) > 100:
                score += 50  # Likely has a real Wikipedia article

            # ── Category Boost ──
            if cat in self.LANDMARK_CATEGORIES:
                score += 120
            elif cat in self.CULTURAL_CATEGORIES:
                score += 100
            elif cat in self.FOOD_CATEGORIES:
                score += 80
            elif cat in self.NATURE_CATEGORIES:
                score += 40

            # ── Penalize Low-Value ──
            if cat in self.PENALIZED_CATEGORIES:
                score -= 200

            # ── Rating Boost ──
            if a.rating >= 4.5:
                score += 60
            elif a.rating >= 4.0:
                score += 30

            # ── Named Place Boost ──
            # Places with real names (not "Place 12345") are more likely real attractions
            name = a.name or ""
            if name and not name.startswith("Place "):
                score += 20
            else:
                score -= 50  # Unnamed = probably not worth visiting

            # ── Paid Place Signal ──
            # If it charges entry, it's likely a curated experience
            if a.cost_per_person_inr and a.cost_per_person_inr > 0:
                score += 15

            scored_pairs.append((score, a))

        # Sort by score descending
        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        return [a for _, a in scored_pairs]

    # ─── Quota Strategy ─────────────────────────────────────

    def _calculate_target_count(self, duration_days: int) -> int:
        """Calculate how many activities to curate based on trip length."""
        # ~5-6 activities per day is realistic
        # Plus some buffer for optimizer to swap
        return min(duration_days * 8, 40)

    def _apply_quota_strategy(
        self,
        activities: List[Activity],
        target: int
    ) -> List[Activity]:
        """
        Apply the 60/20/15/5 quota:
          60% landmarks + iconic attractions
          20% food spots + cafes
          15% cultural (museums, temples)
          5% nature/relaxation filler
        """

        landmarks = []
        food = []
        cultural = []
        nature = []
        other = []

        for a in activities:
            cat = a.category.lower().strip()

            if cat in self.LANDMARK_CATEGORIES:
                landmarks.append(a)
            elif cat in self.FOOD_CATEGORIES:
                food.append(a)
            elif cat in self.CULTURAL_CATEGORIES:
                cultural.append(a)
            elif cat in self.NATURE_CATEGORIES:
                nature.append(a)
            elif cat not in self.PENALIZED_CATEGORIES:
                other.append(a)
            # Penalized categories are dropped entirely

        # Calculate quotas
        num_landmarks = max(1, int(target * 0.60))
        num_food = max(1, int(target * 0.20))
        num_cultural = max(1, int(target * 0.15))
        num_nature = target - num_landmarks - num_food - num_cultural

        # Fill quotas
        curated = []
        curated.extend(landmarks[:num_landmarks])
        curated.extend(food[:num_food])
        curated.extend(cultural[:num_cultural])
        curated.extend(nature[:max(0, num_nature)])

        # If short of target, fill from leftovers (in priority order)
        if len(curated) < target:
            remaining_pool = []
            remaining_pool.extend(landmarks[num_landmarks:])
            remaining_pool.extend(food[num_food:])
            remaining_pool.extend(cultural[num_cultural:])
            remaining_pool.extend(nature[max(0, num_nature):])
            remaining_pool.extend(other)

            need = target - len(curated)
            curated.extend(remaining_pool[:need])

        # Deduplicate by id
        seen_ids = set()
        deduped = []
        for a in curated:
            if a.id not in seen_ids:
                seen_ids.add(a.id)
                deduped.append(a)

        return deduped[:target]

    # ─── Helpers ────────────────────────────────────────────

    def _count_categories(self, activities: List[Activity]) -> Dict[str, int]:
        """Count activities by category group."""
        counts = {"landmarks": 0, "food": 0, "cultural": 0, "nature": 0, "other": 0}

        for a in activities:
            cat = a.category.lower().strip()
            if cat in self.LANDMARK_CATEGORIES:
                counts["landmarks"] += 1
            elif cat in self.FOOD_CATEGORIES:
                counts["food"] += 1
            elif cat in self.CULTURAL_CATEGORIES:
                counts["cultural"] += 1
            elif cat in self.NATURE_CATEGORIES:
                counts["nature"] += 1
            else:
                counts["other"] += 1

        return counts