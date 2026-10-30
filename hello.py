import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELS = ["gemini-3.8-flash"]
PROMPT = "Explain what an AI agent is in 2 simple sentences, for a first-year student."

def ask(prompt):
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as e:
                print(f"{model} failed (try {attempt + 1}): {str(e)[:80]}")
                time.sleep(3)
    return "All models are busy right now. Try again shortly."

print(ask(PROMPT))