import google.generativeai as genai

from .base import LLMProvider


class GeminiProvider(LLMProvider):

    def __init__(self, api_key):

        genai.configure(
            api_key=api_key
        )

        self.model = genai.GenerativeModel(
            "gemini-2.0-flash"
        )


    def generate(
        self,
        system_prompt,
        user_prompt
    ):

        response = self.model.generate_content(
            f"""
            SYSTEM:
            {system_prompt}


            USER:
            {user_prompt}
            """
        )

        return response.text