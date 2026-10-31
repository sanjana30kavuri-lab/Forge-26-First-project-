import os, json, time, uuid
from datetime import datetime
import requests
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def secret(name):
    val = os.getenv(name)
    if val:
        return val
    try:
        return st.secrets[name]
    except Exception:
        return None

client = genai.Client(api_key=secret("GEMINI_API_KEY"),
                      http_options=types.HttpOptions(timeout=30000))
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]
WEBHOOK_URL = secret("N8N_WEBHOOK_URL")

SYSTEM = """You help citizens in India file civic complaints.
Return ONLY JSON with keys: category, department, severity (integer 1-5),
severity_reason, subject, letter, language.
'letter' is a formal, polite complaint in the requested language.
Use placeholders like [Your Name] and [Address] for unknown details.
Never invent facts the user did not give."""

def call_ai(contents, json_mode=True):
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM if json_mode else None,
        response_mime_type="application/json" if json_mode else None)
    for model in MODELS:
        for _ in range(2):
            try:
                r = client.models.generate_content(model=model, contents=contents, config=cfg)
                return json.loads(r.text) if json_mode else r.text
            except Exception as e:
                print("AI error:", model, str(e)[:120])
                time.sleep(1)
    return None

st.set_page_config(page_title="Complaint Chaser", page_icon="📮", layout="centered")
st.title("📮 Complaint Chaser")
st.caption("File a civic complaint in minutes, and we keep chasing it until it moves.")

# ---------- Step 1 ----------
st.subheader("1. Describe the problem")
problem = st.text_area("What's wrong?", placeholder="No water supply in our street for 4 days...")
c1, c2 = st.columns(2)
language = c1.selectbox("Letter language", ["English", "Telugu", "Hindi"])
city = c2.text_input("City / area", placeholder="e.g. Rajahmundry")
photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

if st.button("Draft my complaint", type="primary"):
    if not problem.strip():
        st.warning("Please describe the problem first.")
    else:
        prompt = f"Problem: {problem}\nCity: {city}\nLetter language: {language}"
        contents = [prompt]
        if photo:
            contents = [types.Part.from_bytes(data=photo.getvalue(), mime_type=photo.type), prompt]
        with st.spinner("Drafting..."):
            data = call_ai(contents)
        if data:
            st.session_state.draft = data
            st.session_state.pop("filed", None)
        else:
            st.error("The AI is busy. Please try again in a minute.")

# ---------- Step 2 ----------
if "draft" in st.session_state:
    d = st.session_state.draft
    st.subheader("2. Review and file")
    m1, m2 = st.columns([3, 1])
    m1.markdown(f"**Department**\n\n{d.get('department', '-')}")
    m2.markdown(f"**Severity**\n\n{d.get('severity', '-')}/5")
    st.caption(d.get("severity_reason", ""))
    letter = st.text_area("Complaint letter (editable)", d.get("letter", ""), height=280)
    to_email = st.text_input("Send to (use your own test inbox for the demo)")

    if st.button("File complaint & start tracking", type="primary"):
        cid = "CC-" + uuid.uuid4().hex[:6].upper()
        sent = False
        if WEBHOOK_URL and to_email:
            try:
                requests.post(WEBHOOK_URL, timeout=15, json={
                    "id": cid, "to": to_email,
                    "subject": f"[{cid}] {d.get('subject', 'Complaint')}",
                    "letter": letter})
                sent = True
            except Exception as e:
                st.error(f"Could not reach n8n: {e}")
        st.session_state.filed = {"id": cid, "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                                  "letter": letter, "sent": sent, "escalation": None,
                                  "dept": d.get("department")}

# ---------- Step 3 ----------
if "filed" in st.session_state:
    f = st.session_state.filed
    st.subheader("3. Track")
    st.success(f"Complaint {f['id']} filed on {f['time']}" + ("" if f["sent"] else " (demo mode: email not sent)"))
    st.markdown("**Status**")
    st.markdown("✅ Filed  →  ⏳ Waiting for reply  →  " + ("🚨 Escalated" if f["escalation"] else "⬜ Escalation"))

    if st.button("⏩ Simulate 7 days passed with no reply"):
        with st.spinner("Drafting escalation..."):
            f["escalation"] = call_ai(
                f"Write a firm but polite escalation letter to a senior officer. "
                f"No reply was received within 7 days for complaint {f['id']} to {f['dept']}. "
                f"Original complaint:\n{f['letter']}", json_mode=False)
    if f["escalation"]:
        st.text_area("Escalation letter", f["escalation"], height=260)
        st.download_button("Download escalation letter", f["escalation"], file_name=f"{f['id']}_escalation.txt")