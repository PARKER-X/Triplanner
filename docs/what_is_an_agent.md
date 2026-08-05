# What is an Agent?

## Definition

In this system, an **agent** is a specialized module that owns one specific responsibility in the trip planning pipeline. Each agent:

1. **Receives** a shared `PlanningState` object
2. **Reads** only the fields it needs
3. **Performs** its specialized task (LLM reasoning, API calls, or pure computation)
4. **Writes** its results back to the state
5. **Returns** a structured result object

```
PlanningState (in) → Agent.run() → PlanningState (enriched) + Result
```


## Agents vs. Functions

| Aspect | Plain Function | Agent |
|--------|---------------|-------|
| State | Receives args, returns value | Reads/writes shared PlanningState |
| Prompt | None | Has a dedicated prompt.txt (if LLM-using) |
| Schema | Ad-hoc dicts | Pydantic models with validation |
| Identity | Anonymous | Named, logged, trackable |
| Failure | Crashes caller | Caught by orchestrator, retried or skipped |
| Testing | Unit test with mocks | Integration test with real or mocked LLM |


## Agent Anatomy

Every agent in this project follows the same structure:

```
ai_engine/agent/{agent_name}/
├── __init__.py          # Package marker
├── {agent_name}.py      # The agent class
├── schema.py            # Pydantic input/output models
└── prompt.txt           # LLM system prompt (only for LLM-using agents)
```

### The Agent Class

```python
class SomeAgent:
    def __init__(self, llm=None):
        # Store LLM provider (if needed)
        # Load prompt from prompt.txt (if needed)
        # Initialize API clients (if needed)
    
    def run(self, planning_state) -> SomeResult:
        # 1. Read from planning_state
        # 2. Do the work
        # 3. Write results to planning_state
        # 4. Return structured result
```


## Types of Agents

### LLM-Using Agents
These agents call a language model to handle qualitative reasoning:

- **IntentAgent** — Understands what the user wants
- **AccommodationAgent** — Ranks hotels using LLM judgment

### API-Using Agents
These agents call external services for real-world data:

- **ResearchAgent** — Queries OpenStreetMap, Wikipedia for real places

### Pure Algorithmic Agents
These agents use deterministic algorithms — no LLM, no API:

- **RankingAgent** — Scores and curates using weighted rules
- **OptimizerAgent** — Two-stage DP + local search optimization
- **CriticAgent** — Deterministic validation with rule checks
- **PlannerAgent** — Nearest-neighbor routing + time scheduling


## Why Agents, Not One Big LLM Call?

The North Star principle:

> **"Language models are not planners. They are reasoning interfaces."**

A single LLM call for "plan my trip" produces:
- ❌ Hallucinated restaurants that don't exist
- ❌ Impossible schedules (visit 10 places in 4 hours)
- ❌ No budget awareness
- ❌ Random geographic routing (zigzag across the city)

The agent architecture produces:
- ✅ Real places from OpenStreetMap
- ✅ Feasible schedules checked by the Critic
- ✅ Budget-optimized plans
- ✅ Geographically clustered routing

This is the core insight from Google Research's trip planning paper:
**Qualitative LLM reasoning + Quantitative algorithmic optimization = Plans that actually work.**


## Agent Lifecycle

```
1. INITIALIZATION
   Agent.__init__() — Load prompts, connect APIs, set weights

2. EXECUTION  
   Agent.run(planning_state) — Read state → Do work → Write state

3. RESULT
   Return structured Pydantic model — Always validated, never raw dicts

4. ORCHESTRATION
   Orchestrator catches errors, logs timing, decides retries
```


## Design Principles

1. **Single Responsibility** — Each agent does one thing well
2. **Explicit Contracts** — Input/output defined by Pydantic schemas
3. **Fail Gracefully** — Return empty results, don't crash the pipeline
4. **Determinism Where Possible** — Use algorithms over LLM calls when the task is well-defined
5. **Observable** — Print emoji status logs for debugging
