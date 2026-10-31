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
Return ONLY JSON with these keys: needs_more_info (true/false), missing (list of short questions),
category, department, severity (integer 1-5), severity_reason, subject, letter, language.

If the message does not clearly say WHAT the problem is, set needs_more_info to true,
put 1-3 short questions in "missing", and leave the other fields empty.
Otherwise set needs_more_info to false and fill everything in.

Rules:
- department: the specific local body (for example "Municipal Corporation - Sanitation Wing"), not just "Government".
- severity: 1 = minor inconvenience, 3 = affects daily life, 5 = immediate danger to health or safety.
- severity_reason: one short sentence.
- letter: a formal, polite complaint in the requested language, under 150 words.
  Always mention the location and how long the problem has lasted, if the user gave them.
  Use placeholders like [Your Name], [Address], [Phone] for details the user did not give.
- Use ONLY facts the user gave. Do not describe conditions, causes or impacts they did not mention.
- Never invent names, dates or numbers that the user did not provide."""

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

st.set_page_config(
    page_title="Complaint Chaser | Civic AI",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        max-width: 900px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stButton"] > button {
        border-radius: 10px;
        font-weight: 650;
        min-height: 46px;
    }

    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input {
        border-radius: 10px;
    }

    .hero {
        background: linear-gradient(135deg, #EEF2FF, #F5F3FF);
        border: 1px solid #C7D2FE;
        border-radius: 18px;
        padding: 1.5rem 1.7rem;
        margin-bottom: 1.6rem;
    }

    .hero h1 {
        margin: 0;
        color: #312E81;
    }

    .hero p {
        margin: 0.5rem 0 0;
        color: #4B5563;
        font-size: 1.05rem;
    }
</style>

<div class="hero">
    <h1>📮 Complaint Chaser</h1>
    <p>Turn a civic problem into a clear complaint—and follow up until it moves.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Step 1 ----------
st.subheader("1. Describe the problem")
st.caption("Tell us what happened. Add a photo if it helps explain the problem.")
problem = st.text_area("What's wrong?", placeholder="No water supply in our street for 4 days...")
c1, c2 = st.columns(2)
language = c1.selectbox("Letter language", ["English", "Telugu", "Hindi"])
city = c2.text_input("City / area", placeholder="e.g. Rajahmundry")
photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

if st.button("✨ Draft my complaint", type="primary", use_container_width=True):
     if not problem.strip():
        st.warning("Please describe the problem first.")
     elif len(problem.split()) < 4:
        st.session_state.pop("draft", None)
        st.warning("Please add a few more details: what is the problem, where, and for how long?")
     else:
        prompt = f"Problem: {problem}\nCity: {city}\nLetter language: {language}"
        contents = [prompt]
        if photo:
            contents = [types.Part.from_bytes(data=photo.getvalue(), mime_type=photo.type), prompt]
        with st.spinner("Drafting..."):
            data = call_ai(contents)
        if data and data.get("needs_more_info"):
            st.session_state.pop("draft", None)
            st.warning("I need a bit more detail to write a proper complaint:")
            for q in data.get("missing", []):
                st.write("•", q)
        elif data:
            st.session_state.draft = data
            st.session_state.pop("filed", None)
        else:
            st.error("The AI is busy. Please try again in a minute.")

# ---------- Step 2 ----------
if "draft" in st.session_state:
    d = st.session_state.draft

    st.subheader("2. Review and file")
    st.caption("Review the AI suggestion, edit the letter if needed, then choose how to file it.")

    m1, m2 = st.columns([2, 1])
    m1.metric("🏛️ Suggested department", d.get("department", "-"))
    m2.metric("⚠️ Severity", f"{d.get('severity', '-')}/5")

    st.caption(d.get("severity_reason", ""))
    letter = st.text_area("Complaint letter (editable)", d.get("letter", ""), height=280)
    to_email = st.text_input("Send to(use your own test inbox for the demo)")
    if st.button("File complaint & start tracking", type="primary"):
        cid = "CC-" + uuid.uuid4().hex[:6].upper()
        sent = False
        if WEBHOOK_URL and to_email:
                       try:
                           r = requests.post(WEBHOOK_URL, timeout=15, json={
                               "id": cid, "to": to_email,
                               "subject": f"[{cid}] {d.get('subject', 'Complaint')}",
                               "letter": letter})
                           r.raise_for_status()
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
