from openai import OpenAI

from ai_engine.core.llm.base import LLMProvider
from ai_engine.core.config import settings


class GroqProvider(LLMProvider):

    def __init__(self):

        self.client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )


    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:


        response = self.client.chat.completions.create(

            model=settings.LLM_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],

            temperature=0,

            response_format={
                "type": "json_object"
            }
        )


        return response.choices[0].message.content