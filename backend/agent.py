# backend/agent.py
import os
from google import genai
from google.genai import types

class CodeAgent:
    def __init__(self):
        self.client = genai.Client()
        self.model_name = "gemini-flash-latest"
        
        # Check if we are in development mode to save API quota
        self.use_mock = os.getenv("USE_MOCK_AGENT", "false").lower() == "true"

    def generate_python_code(self, user_prompt: str) -> str:
        """
        Generates Python code via Gemini, or returns mock code if testing.
        """
        if self.use_mock:
            print("⚠️ USING MOCK AGENT: Bypassing Google API to save quota.")
            # Left-aligned, no indentation required, foolproof mock code
            return """import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('sales.csv')
plt.figure(figsize=(8, 5))
plt.bar(df.iloc[:, 0].astype(str), df.iloc[:, 1], color='green')
plt.title('Mock Revenue Chart')
plt.savefig('plot.png')
print("Mock analysis complete!")"""

        # If not mocking, call the real Google API
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
                temperature=0.1,
            )
        )
        
        return response.text.strip()