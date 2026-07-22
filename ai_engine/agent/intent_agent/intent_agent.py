import json

from .schema import Intent



class IntentAgent:


    def __init__(self, llm):

        self.llm = llm


        with open(
            "ai_engine/agent/intent_agent/prompt.txt"
        ) as file:

            self.prompt = file.read()



    def run(
        self,
        user_input:str
    ):


        response = self.llm.generate(

            system_prompt=self.prompt,

            user_prompt=user_input

        )


        data = json.loads(response)


        return Intent(**data)