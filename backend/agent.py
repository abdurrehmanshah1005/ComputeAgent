# backend/agent.py
import os
from google import genai
from google.genai import types

class CodeAgent:
    def __init__(self):
        # The client automatically picks up GEMINI_API_KEY from the environment
        self.client = genai.Client()
        # We use flash because it is fast, highly capable at coding, and free-tier friendly
        self.model_name = "gemini-flash-latest" 

    def generate_python_code(self, user_prompt: str) -> str:
        """
        Calls the Gemini API once to generate Python code based on the prompt.
        """
        # We explicitly tell the AI to act like a machine, not a chatbot
        system_instruction = (
            "You are an expert Python data science assistant. "
            "Write Python code to solve the user's problem. "
            "OUTPUT ONLY VALID, EXECUTABLE PYTHON CODE. "
            "Do NOT wrap the code in markdown blocks (no ```python). "
            "Do NOT include any explanations or conversational text. "
            "Just the raw code."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1, # Low temperature makes the code more deterministic/reliable
            )
        )
        
        # Return the raw text, stripping any accidental whitespace
        return response.text.strip()