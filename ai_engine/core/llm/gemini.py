import google.generativeai as genai

from ai_engine.core.llm.base import LLMProvider
from ai_engine.core.config import settings



class GeminiProvider(LLMProvider):


    def __init__(self):

        genai.configure(
            api_key=settings.GEMINI_API_KEY
        )


        self.model = genai.GenerativeModel(
            settings.LLM_MODEL
        )


    def generate(
        self,
        system_prompt: str,
        user_prompt: str
    ):


        response = self.model.generate_content(
            [
                {
                    "role": "user",
                    "parts": [
                        f"""
                        SYSTEM:

                        {system_prompt}


                        USER:

                        {user_prompt}
                        """
                    ]
                }
            ]
        )


        return response.text