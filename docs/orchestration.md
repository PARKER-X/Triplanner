# Orchestration

## Responsibility

The orchestrator controls:

- Workflow (7-stage pipeline)
- Agent execution order
- State transitions
- Retries (critic-optimizer loop)
- Error handling
- Timing instrumentation

The orchestrator does NOT:

- Make plans
- Decide answers
- Replace agents
- Call APIs directly


## Architecture

```
                User Query
                    │
                    ▼
            ┌──────────────┐
            │ Orchestrator  │
            │ (conductor)   │
            └──────┬───────┘
                    │
            ┌──────┴───────┐
            │ PlanningState │  ← Shared blackboard
            └──────┬───────┘
                    │
    ┌───────┬───────┼───────┬───────┬───────┬───────┐
    ▼       ▼       ▼       ▼       ▼       ▼       ▼
  Intent  Accomm  Research Ranking Planner Optim  Critic
                                            ▲       │
                                            │       │
                                            └───────┘
                                          Retry Loop
                                         (max 2x)
```


## 7-Stage Pipeline

### Stage 1: Intent
- **Agent**: IntentAgent
- **Action**: Parse natural language → structured intent
- **Writes**: `state.intent`, `state.constraints`

### Stage 2: Accommodation
- **Agent**: AccommodationAgent
- **Action**: Find where to stay → geographic center
- **Writes**: `state.accommodation`, `state.accommodation_alternatives`
- **Skipped if**: Day trip (duration_days ≤ 1)

### Stage 3: Research
- **Agent**: ResearchAgent
- **Action**: Query APIs for real activities
- **Writes**: `state.candidates` (activities, distances, neighborhoods)

### Stage 4: Ranking
- **Agent**: RankingAgent
- **Action**: Curate 60% landmarks / 20% food / 15% culture / 5% nature
- **Writes**: `state.candidates.activities` (modified in-place)

### Stage 5: Planner
- **Agent**: PlannerAgent
- **Action**: Create day-by-day itinerary with time scheduling
- **Writes**: `state.plans`, `state.selected_plan`

### Stage 6: Optimizer
- **Agent**: OptimizerAgent
- **Action**: Two-stage optimization (intra-day DP + inter-day swap)
- **Writes**: `state.optimization_result`

### Stage 7: Critic
- **Agent**: CriticAgent
- **Action**: Validate feasibility (7 rules)
- **Writes**: `state.evaluation_results`

### Feedback Loop
If critic finds **critical** violations:
1. Orchestrator increments `state.retry_count`
2. Goes back to Stage 6 (Optimizer)
3. Maximum 2 retries, then proceeds with best effort


## Error Handling

Each stage is wrapped in `try/except`:
- On success → mark stage complete, log timing
- On error → log error, continue pipeline (graceful degradation)
- Fatal errors (no destination, no activities) → stop pipeline

```python
state = self._run_stage(state, "intent", self._stage_intent)
```


## Timing

The orchestrator tracks time for each stage:

```python
state.timing = {
    "intent": 1.2,
    "accommodation": 8.5,
    "research": 25.3,
    "ranking": 0.01,
    "planner": 0.05,
    "optimizer": 0.12,
    "critic": 0.002,
    "total": 35.18
}
```
