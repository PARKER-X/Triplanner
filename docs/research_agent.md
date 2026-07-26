# Research Agent: Finding Real-World Options

## Purpose

The Research Agent transforms structured intent into **concrete, feasible options**.

It answers: "What can we actually DO with these constraints?"

## Core Philosophy

1. **Reality First**: Only return places/activities that exist and are accessible
2. **Constraint-Driven**: Filter aggressively by budget, time, location
3. **User-Centric Ranking**: Rank by user preferences, not just popularity
4. **Feasibility Scoring**: Every option includes a "can we really do this?" score

## Input (from Intent Agent)

```json
{
  "goal_type": "travel",
  "traveler": {
    "type": "group",
    "count": 4
  },
  "preferences": {
    "travel_style": "balanced",
    "priorities": ["food", "culture", "budget"],
    "avoid": ["crowded", "expensive"]
  },
  "constraints": {
    "source": "Delhi",
    "destination": "Mumbai",
    "budget": 10000,
    "duration_days": 3,
    "start_date": null
  },
  "missing_information": []
}

## Output

{
  "destination": "Mumbai",
  "search_date": "2024-01-20",
  "total_budget": 10000,
  "per_person_budget": 2500,
  "duration_days": 3,
  "party_size": 4,
  
  "places": [
    {
      "id": "place_001",
      "name": "Gateway of India",
      "category": "landmark",
      "location": {"lat": 18.9220, "lng": 72.8347},
      "cost_per_person": 0,
      "duration_hours": 2,
      "rating": 4.7,
      "reviews": 8234,
      "best_time": "early_morning",
      "opening_hours": "all_day",
      "matches_priorities": ["culture"],
      "feasibility_score": 0.98,
      "why_selected": "Free landmark, cultural significance, matches priorities"
    }
  ],
  
  "activities": [
    {
      "id": "activity_001",
      "name": "Street Food Tour",
      "category": "food_experience",
      "cost_per_person": 200,
      "duration_hours": 3,
      "best_time": "evening",
      "group_friendly": true,
      "feasibility_score": 0.95,
      "why_selected": "Matches food priority, within budget, group-friendly"
    }
  ],
  
  "accommodations": [
    {
      "id": "hotel_001",
      "name": "Backpacker's Inn",
      "area": "Colaba",
      "cost_per_night": 800,
      "cost_per_group_3_nights": 9600,
      "occupancy": "2-4 people dorm",
      "amenities": ["wifi", "breakfast", "kitchen"],
      "rating": 4.3,
      "feasibility_score": 0.92,
      "why_selected": "Budget-friendly, central location, group accommodations"
    }
  ],
  
  "transport": {
    "delhi_to_mumbai": {
      "options": [
        {
          "type": "flight",
          "cost_per_person": 3000,
          "duration_hours": 2,
          "total_cost_group": 12000,
          "feasibility": "over_budget"
        },
        {
          "type": "train",
          "cost_per_person": 800,
          "duration_hours": 16,
          "total_cost_group": 3200,
          "feasibility": "within_budget"
        },
        {
          "type": "bus",
          "cost_per_person": 500,
          "duration_hours": 20,
          "total_cost_group": 2000,
          "feasibility": "within_budget"
        }
      ],
      "recommended": "train"
    },
    "local_transport": {
      "type": "auto_rickshaw",
      "average_cost_per_ride": 50,
      "estimated_daily_rides": 3,
      "estimated_3day_cost": 450
    }
  },
  
  "research_summary": {
    "feasible": true,
    "budget_status": "comfortable",
    "breakdown": {
      "transport_delhi_mumbai": 3200,
      "accommodation_3_nights": 2400,
      "local_transport": 450,
      "food": 2000,
      "activities": 1200,
      "contingency": 750,
      "total": 10000
    },
    "priority_coverage": {
      "food": 0.95,
      "culture": 0.85,
      "budget": 0.98
    },
    "warnings": [],
    "recommendations": [
      "Take train to balance cost and comfort",
      "Stay in Colaba area for central location",
      "Do street food tours for best food experience",
      "Visit Gateway of India early morning to avoid crowds"
    ]
  }
}


How It Works
Phase 1: Data Retrieval
Source: Google Places API + Custom Database + User Knowledge

text

Query: "Places in Mumbai under ₹500 per person"
     ↓
Hits: Google Places, Local guides, Reviews APIs
     ↓
Returns: 50+ results
Phase 2: Constraint Filtering
Apply Hard Filters:

Budget constraints
Time constraints
Location radius
Opening hours
Group size suitability
text

50 results → Apply filters → 15 feasible options
Phase 3: Preference Ranking
Score each option:

Alignment with priorities (food, culture, adventure, etc.)
User ratings & reviews
Feasibility for group
Uniqueness (avoid mainstream)
Phase 4: Feasibility Scoring
Calculate: Can we REALLY do this?

text

Feasibility = 
  0.4 × Budget_Match +
  0.3 × Time_Feasibility +
  0.2 × Preference_Match +
  0.1 × Logistics_Ease
Phase 5: Budget Breakdown
Show realistic spending:

text

Transport: ₹3200 (32%)
Hotel: ₹2400 (24%)
Food: ₹2000 (20%)
Activities: ₹1200 (12%)
Local Transport: ₹450 (4.5%)
Contingency: ₹750 (7.5%)
Total: ₹10000
Key Differences from Just "Search"
Aspect	Basic Search	Research Agent
Returns	"Popular places"	"Feasible places matching constraints"
Scoring	Rating-based	Constraint + Preference based
Budget	Ignored	Central to filtering
Group Size	Ignored	Affects suitability
Explanation	None	"Why selected" for each item
Warnings	None	Flags impossible combinations

Research Agent gives Planner Agent:

Ranked places (top 10-15)
Feasible activities (top 8-10)
Budget breakdown (realistic spending)
Warnings (what might go wrong)
Recommendations (best options for user priorities)
This way, Planner doesn't have to search - just combine these pre-vetted options.

Success Metrics
Research Agent succeeds when:

✅ All returned options are actually feasible
✅ Budget breakdown is realistic (±10%)
✅ Top options match user priorities
✅ Explains WHY each option was selected
✅ Flags impossible combinations early