import json

from .schema import Intent



class IntentAgent:


    def __init__(self, llm):

        self.llm = llm


        with open(
            "ai_engine/agent/intent_agent/prompt.txt"
        ) as file:

            self.prompt = file.read()



    def run(self, user_input: str) -> Intent:
        response = self.llm.generate(
            system_prompt=self.prompt,
            user_prompt=user_input,
        )

        if not response:
            raise RuntimeError("LLM returned an empty response.")

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            print("\n===== RAW LLM RESPONSE =====")
            print(response)
            print("============================\n")
            raise ValueError(f"Invalid JSON returned by LLM: {e}")

        return Intent.model_validate(data)