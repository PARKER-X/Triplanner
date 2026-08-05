# Agent Connections — How They Work Together

## The Pipeline

The agents form a **7-stage sequential pipeline** with one feedback loop:

```
User Query: "4 friends, 3 days Mumbai, ₹15000, food and culture"
                    │
                    ▼
         ┌─────────────────────┐
         │  Stage 1: INTENT    │  Parse natural language → structured intent
         │  (IntentAgent)      │  Output: goal_type, traveler, preferences, constraints
         └─────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Stage 2: STAY      │  Find accommodation → geographic center
         │  (AccommodationAgent)│  Output: selected hotel + coordinates
         └─────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Stage 3: RESEARCH  │  Find real activities via OpenStreetMap + Wikipedia
         │  (ResearchAgent)    │  Output: 50+ raw activities with coordinates
         └─────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Stage 4: RANKING   │  Curate & prioritize (famous > food > culture > filler)
         │  (RankingAgent)     │  Output: top 20-30 curated activities
         └─────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Stage 5: PLANNER   │  Create initial day-by-day itinerary
         │  (PlannerAgent)     │  Output: sequenced activities with times, meals, costs
         └─────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
     ┌──▶│  Stage 6: OPTIMIZER │  Two-stage optimization (DP + local search)
     │   │  (OptimizerAgent)   │  Output: optimized itinerary with better routing
     │   └─────────┬───────────┘
     │              │
     │              ▼
     │   ┌─────────────────────┐
     │   │  Stage 7: CRITIC    │  Validate feasibility (budget, time, travel)
     │   │  (CriticAgent)      │  Output: pass/fail + violations
     │   └─────────┬───────────┘
     │              │
     │         ┌────┴────┐
     │         │ PASSED? │
     │         └────┬────┘
     │          ╱         ╲
     │      YES              NO (max 2 retries)
     │       │                │
     │       ▼                └──────────────┘
     │  ┌──────────┐
     │  │ DONE ✅  │
     │  │ Final    │
     │  │ Itinerary│
     │  └──────────┘
     │
     └── Retry with critic feedback
```


## Data Flow: What Each Agent Reads & Writes

### PlanningState as Shared Blackboard

Every agent reads from and writes to a single `PlanningState` object:

| Agent | Reads From | Writes To |
|-------|-----------|-----------|
| IntentAgent | `user_goal` (raw string) | `intent`, `constraints` |
| AccommodationAgent | `constraints` (destination, budget) | `accommodation`, `accommodation_alternatives` |
| ResearchAgent | `intent`, `constraints`, `accommodation` (center coords) | `candidates` (activities, distances, neighborhoods) |
| RankingAgent | `candidates.activities` | `candidates.activities` (curated, in-place) |
| PlannerAgent | `intent`, `constraints`, `candidates` | `plans`, `selected_plan` |
| OptimizerAgent | `selected_plan` | `optimization_result` |
| CriticAgent | `optimization_result` or `selected_plan`, `constraints` | `evaluation_results` |


## How Each Connection Works

### 1. Intent → Accommodation
The IntentAgent extracts `destination` and `budget`. The AccommodationAgent uses these to:
- Geocode the destination (get lat/lng)
- Allocate 25% of budget to accommodation
- Search for hotels near the destination center

### 2. Accommodation → Research  
The accommodation's coordinates become the **geographic center** for activity search. The ResearchAgent searches within 5km of the hotel, so activities are walkable/transit-reachable from where you're staying.

### 3. Research → Ranking
Raw activities (50+) go in, curated activities (20-30) come out. The RankingAgent applies:
- Fame scoring (Wikipedia presence = actually famous)
- Quota allocation (60% landmarks, 20% food, 15% culture, 5% nature)
- Penalty filtering (remove swimming pools, unnamed places)

### 4. Ranking → Planner
The PlannerAgent takes the curated list and:
- Distributes activities across days
- Sequences them using nearest-neighbor (minimize travel)
- Schedules with realistic times (9 AM – 9 PM)
- Adds meal slots
- Calculates costs per day

### 5. Planner → Optimizer
The initial plan is good but not optimal. The OptimizerAgent:
- **Stage 1 (Intra-Day DP)**: For each day, re-sequence activities to minimize travel time
- **Stage 2 (Inter-Day Swap)**: Swap activities between days when it improves total score

### 6. Optimizer → Critic
The optimized plan gets validated against 7 deterministic rules:
1. Budget: total cost ≤ user budget
2. Time window: activities within 9 AM – 9 PM
3. Travel sanity: no >25 km walking per day
4. No duplicates: same activity doesn't appear twice
5. Rest: at least 8 hours overnight
6. Meal gaps: no >5 hours without food
7. Not empty: every day has ≥ 2 activities

### 7. Critic → Optimizer (Feedback Loop)
If the critic finds **critical** violations, the orchestrator feeds the violations back to the optimizer for a repair attempt. Maximum 2 retries to prevent infinite loops.


## Error Propagation

```
Agent fails
    │
    ▼
Orchestrator catches exception
    │
    ├── Error is recoverable → Log warning, continue with partial data
    │   Example: Wikipedia API timeout → skip enrichment, use raw data
    │
    └── Error is fatal → Stop pipeline, return error to user
        Example: Destination not found → can't do anything
```

Each agent wraps its work in try/except and returns empty/default results on failure rather than crashing the entire pipeline.


## Timing & Observability

The orchestrator tracks how long each stage takes:

```python
planning_state.timing = {
    "intent": 1.2,          # seconds
    "accommodation": 8.5,   # API calls take time
    "research": 25.3,       # Multiple Overpass queries
    "ranking": 0.01,        # Pure computation, instant
    "planner": 0.05,        # Algorithm, very fast
    "optimizer": 0.12,      # DP + local search
    "critic": 0.002,        # Rule checks, instant
    "total": 35.18
}
```

Every agent prints emoji-prefixed status messages for real-time debugging:
```
✅ Intent Agent initialized
🔍 RESEARCH AGENT: Searching for activities in Mumbai
📍 Getting coordinates for Mumbai...
🏪 Searching Overpass API for activities...
🏆 RANKING AGENT: Curating 47 activities...
📅 PLANNER AGENT: Creating location-optimized itinerary
⚡ OPTIMIZER AGENT: Two-stage optimization...
🔍 CRITIC AGENT: Validating plan (7 rules)...
✅ PIPELINE COMPLETE
```
