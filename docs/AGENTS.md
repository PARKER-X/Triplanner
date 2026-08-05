# Agents

This document describes all 7 agents in the AI Trip Planner pipeline.

---

## 1. Intent Agent

**Purpose**: Convert natural language into structured intent.

**Input**: Raw user message (string)

**Output**: `IntentResult` — structured JSON with:
- `goal_type`: travel, event, etc.
- `traveler`: type (solo/couple/family/group), count
- `preferences`: travel_style, priorities, avoid list
- `constraints`: source, destination, budget, duration_days, start_date
- `missing_information`: what the user didn't specify

**LLM**: ✅ Yes (understands vague human language)

---

## 2. Accommodation Agent

**Purpose**: Find where the traveler will stay.

**Input**: PlanningState with `constraints` (destination, budget, duration)

**Output**: `AccommodationResult` — selected hotel/hostel with:
- Name, type, coordinates, cost_per_night
- Alternatives ranked by suitability
- Budget allocation (25% of total budget)

**LLM**: ✅ Optional (for ranking descriptions)

**Why first?** Where you stay determines the geographic center for all other activities. This is the #1 priority in trip planning.

---

## 3. Research Agent (Retrieval)

**Purpose**: Find real-world activities via APIs.

**Input**: PlanningState with `intent`, `constraints`, `accommodation` (center point)

**Output**: `ResearchResult` — raw activities with:
- Name, category, coordinates, cost, duration
- Distance matrix (haversine between all pairs)
- Neighborhood groupings
- Budget coverage stats

**APIs Used**:
- Overpass API (OpenStreetMap POI search)
- Nominatim (geocoding)
- Wikipedia (descriptions, fame signal)
- Haversine (local distance calculator)

**LLM**: ✅ Yes (for query construction)

---

## 4. Ranking Agent

**Purpose**: Curate and prioritize activities.

**Input**: PlanningState with `candidates.activities` (raw list)

**Output**: Curated activities list (modifies `candidates.activities` in-place)

**Priority System**:
| Priority | Category | Quota | Examples |
|----------|----------|-------|---------|
| 🥇 P1 | Famous landmarks | 60% | Gateway of India, Taj Mahal |
| 🥈 P2 | Iconic food/cafes | 20% | Leopold Cafe, street food |
| 🥉 P3 | Cultural experiences | 15% | Museums, temples |
| P4 | Nature/relaxation | 5% | Parks, gardens |

**Key Signal**: Wikipedia presence = actually famous (+150 score)

**LLM**: ❌ No (purely algorithmic scoring)

---

## 5. Planner Agent

**Purpose**: Create day-by-day itinerary with time scheduling.

**Input**: PlanningState with `candidates` (curated activities), `constraints`

**Output**: `PlannerResult` — complete itinerary:
- Day plans with sequenced activities
- Time slots (09:00 - 21:00 window)
- Meals (breakfast, lunch, dinner)
- Cost breakdown per day
- Walking distance estimates

**Algorithm**: Nearest-neighbor TSP for routing + time-slot packing

**LLM**: ✅ Yes (for prompt-based planning)

---

## 6. Optimizer Agent

**Purpose**: Optimize the planner's output using Google-style two-stage solver.

**Input**: PlanningState with `selected_plan` (initial itinerary)

**Output**: `OptimizationResult` — optimized itinerary:
- Re-sequenced activities (minimize travel)
- Recalculated times
- Inter-day swaps (balance days)
- Feasibility scores per day

**Algorithm**:
- **Stage 1 (Intra-Day)**: Nearest-neighbor re-sequencing per day using haversine
- **Stage 2 (Inter-Day)**: Local search — swap activities between days to maximize total score

**LLM**: ❌ No (purely algorithmic — DP + heuristic)

---

## 7. Critic Agent

**Purpose**: Validate the plan's feasibility.

**Input**: PlanningState with `optimization_result` or `selected_plan`

**Output**: `CriticVerdict` — pass/fail with:
- List of violations (critical/warning/info)
- Overall score (0-1)
- Suggested fixes

**7 Validation Rules**:
1. 💰 Budget check — total cost ≤ user budget
2. ⏰ Time window — activities within 09:00-21:00
3. 🚶 Travel sanity — no >25km walking per day
4. 🔄 Duplicate check — no repeated activities
5. 🛌 Rest check — ≥8 hours between days
6. 🍽️ Meal gap — no >5 hours without food
7. 📅 Empty day — every day has ≥2 activities

**LLM**: ❌ No (deterministic rule checks)