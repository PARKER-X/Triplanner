class orchestrator:
    def __init__(self):
        pass
    
    def run(self,state):

        state = intent_agent.run(state)

        state = retrieval_agent.run(state)

        state = planner_agent.run(state)

        state = optimizer_agent.run(state)

        state = critic_agent.run(state)

        return state