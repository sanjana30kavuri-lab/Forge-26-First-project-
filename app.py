import os
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from hello import MODELS

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=15000),
)

MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite",  "gemini-3.7-flash"]

def ask(prompt):
    last_error = ""
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return response.text
            except Exception as e:
                print(f"[{model}, attempt {attempt + 1}] ERROR: {e}")
                last_error = str(e)
                time.sleep(1)
    return f"The AI is busy right now. Last error: {last_error[:300]}"

st.title("My First AI App")
user_text = st.text_area("Ask me anything:")

if st.button("Submit"):
    if user_text.strip():
        with st.spinner("Thinking..."):
            full_prompt = "You are a civil engineering teaching assistant. Explain in simple words, in under 100 words, for a first-year student. Question: " + user_text
            st.write(ask(full_prompt))
    else:
        st.warning("Please type something first.")