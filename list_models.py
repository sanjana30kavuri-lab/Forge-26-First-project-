import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for m in client.models.list():
    name = m.name.replace("models/", "")
    if ("flash" in name or "lite" in name) and not any(
        w in name for w in ["live", "audio", "tts", "image", "native", "translate", "robotics"]
    ):
        print(name)