import os, json, time, uuid, re, html
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
from concurrent.futures import ThreadPoolExecutor
import requests
import streamlit as st
import re
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
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
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash"]
WEBHOOK_URL = secret("N8N_WEBHOOK_URL")
LANGS = ["English", "Telugu", "Hindi"]
LANG_NAMES = {"English": "English", "Telugu": "తెలుగు", "Hindi": "हिन्दी"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SEV_COLORS = {1: "#16a34a", 2: "#65a30d", 3: "#d97706", 4: "#ea580c", 5: "#dc2626"}


def e(x):
    """Escape text before putting it inside HTML."""
    return html.escape(str(x or ""))


# ---------------------------------------------------------------- translations
UI = {
    "English": {
        "hero_sub": "Turn a civic problem into a clear complaint—and follow up until it moves.",
        "nav_new": "New complaint", "nav_history": "Complaint history", "nav_settings": "Settings",
        "language_lbl": "Language",
        "prefs": "Preferences", "brand_tag": "Civic AI assistant",
        "filed": "Filed", "escalated": "Escalated",
        "urgent_title": "Urgent danger?",
        "urgent_body": "Call <b>112</b>, the national emergency number.",
        "urgent_alt": "Not urgent? You can also file on",
        "theme_dark": "Dark mode", "theme_light": "Light mode",
        "step1": "1. Describe the problem",
        "step1_cap": "Tell us what happened. Add a photo if it helps explain the problem.",
        "problem_label": "What's wrong?",
        "problem_ph": "No water supply in our street for 4 days...",
        "letter_lang": "Letter language", "city_label": "City / area", "city_ph": "e.g. Rajahmundry",
        "photo": "Photo (optional)",
        "draft_btn": "✨ Draft my complaint",
        "warn_describe": "Please describe the problem first.",
        "warn_more": "Please add a few more details: what is the problem, where, and for how long?",
        "drafting": "Drafting and analysing...",
        "need_more_info": "-Write every item in missing in the requested language.",
        "not_civic": "This tool is only for civic issues such as water supply, roads, drainage, garbage, electricity or street lights. Please describe a public problem.",
        "ai_busy": "The AI is busy. Please try again in a minute.",
        "step2": "2. Review and file",
        "dept_lbl": "🏛️ Department responsible", "severity": "⚠️ Severity {n}/5",
        "why_title": "🔎 Why this may have happened", "resp_title": "👥 Who is responsible",
        "analysis_note": "AI analysis based on general knowledge. These are possibilities, not confirmed facts.",
        "letter_label": "Complaint letter (editable)",
        "who_title": "📬 Who should receive it?",
        "searching": "Searching official websites for officers in {city}...",
        "search_unavail": "Officer search is unavailable right now. You can enter an email manually below.",
        "none_found": "No official email addresses found online for this department. Enter one manually below, or file on the central grievance portal:",
        "found_cap": "Found on the web. Tick the officers you want to send this to.",
        "badge_ok": "✅ found on a source page",
        "badge_warn": "⚠️ not confirmed on a page, double-check before sending",
        "badge_off": "🏛️ official domain",
        "sources": "Sources:",
        "extra_label": "Add other email addresses (optional, comma separated)",
        "file_btn": "File complaint & start tracking",
        "bad_email": "Please enter at least one valid email address, like name@example.com.",
        "n8n_err": "Could not reach n8n: {err}",
        "step3": "3. Track",
        "filed_msg": "Complaint {id} filed on {time}",
        "not_sent": " (email not sent: no recipient selected or webhook missing)",
        "sent_to": "Sent to:", "status_lbl": "Status",
        "flow_filed": "✅ Filed", "flow_wait": "⏳ Waiting for reply",
        "flow_esc": "🚨 Escalated", "flow_esc_pending": "⬜ Escalation",
        "sim_btn": "⏩ Demo: skip the 7-day wait.",
        "esc_spin": "Drafting escalation...",
        "esc_label": "Escalation letter", "dl_esc": "Download escalation letter",
        "hist_title": "🗂️ Complaint history",
        "hist_empty": "No complaints filed yet in this session.",
        "status_esc": "🚨 Escalated", "status_wait": "⏳ Waiting for reply",
        "severity_lbl": "Severity", "letter_lbl": "Letter", "not_sent_lbl": "not sent",
        "dl_hist": "Download history (JSON)",
        "set_title": "⚙️ Settings",
        "set_cap": "Saved for this session. Your name, address and phone replace the placeholders in letters.",
        "set_name": "Your name", "set_phone": "Phone", "set_addr": "Address",
        "set_city": "Default city / area", "set_save": "Save settings", "set_saved": "Settings saved.",
    },
    "Telugu": {
        "hero_sub": "పౌర సమస్యను స్పష్టమైన ఫిర్యాదుగా మార్చండి—అది పరిష్కారమయ్యే వరకు వెంటాడండి.",
        "nav_new": "కొత్త ఫిర్యాదు", "nav_history": "ఫిర్యాదుల చరిత్ర", "nav_settings": "సెట్టింగ్స్",
        "language_lbl": "భాష",
        "prefs": "ప్రాధాన్యతలు", "brand_tag": "పౌర AI సహాయకుడు",
        "filed": "దాఖలు", "escalated": "ఉన్నత స్థాయికి",
        "urgent_title": "అత్యవసర ప్రమాదమా?",
        "urgent_body": "జాతీయ అత్యవసర నంబర్ <b>112</b>కు కాల్ చేయండి.",
        "urgent_alt": "అత్యవసరం కాకపోతే ఇక్కడ కూడా ఫిర్యాదు చేయవచ్చు:",
        "theme_dark": "డార్క్ మోడ్", "theme_light": "లైట్ మోడ్",
        "step1": "1. సమస్యను వివరించండి",
        "step1_cap": "ఏం జరిగిందో చెప్పండి. సమస్యను వివరించడానికి ఫోటో జత చేయవచ్చు.",
        "problem_label": "సమస్య ఏమిటి?",
        "problem_ph": "మా వీధిలో 4 రోజులుగా నీటి సరఫరా లేదు...",
        "letter_lang": "ఉత్తరం భాష", "city_label": "నగరం / ప్రాంతం", "city_ph": "ఉదా. రాజమహేంద్రవరం",
        "photo": "ఫోటో (ఐచ్ఛికం)",
        "draft_btn": "✨ నా ఫిర్యాదును సిద్ధం చేయి",
        "warn_describe": "దయచేసి ముందు సమస్యను వివరించండి.",
        "warn_more": "దయచేసి మరిన్ని వివరాలు ఇవ్వండి: సమస్య ఏమిటి, ఎక్కడ, ఎంత కాలంగా?",
        "drafting": "సిద్ధం చేస్తున్నాను, విశ్లేషిస్తున్నాను...",
        "need_more_info": "సరైన ఫిర్యాదు రాయడానికి నాకు కొంచెం ఎక్కువ సమాచారం కావాలి:",
        "not_civic": "ఈ సాధనం నీటి సరఫరా, రోడ్లు, డ్రైనేజీ, చెత్త, విద్యుత్ లేదా వీధి దీపాలు వంటి పౌర సమస్యల కోసం మాత్రమే. దయచేసి ఒక ప్రజా సమస్యను వివరించండి.",
        "ai_busy": "AI ప్రస్తుతం బిజీగా ఉంది. దయచేసి ఒక నిమిషం తర్వాత మళ్ళీ ప్రయత్నించండి.",
        "step2": "2. సమీక్షించి దాఖలు చేయండి",
        "dept_lbl": "🏛️ బాధ్యత వహించే శాఖ", "severity": "⚠️ తీవ్రత {n}/5",
        "why_title": "🔎 ఇది ఎందుకు జరిగి ఉండవచ్చు", "resp_title": "👥 ఎవరు బాధ్యులు",
        "analysis_note": "సాధారణ అవగాహన ఆధారంగా AI చేసిన విశ్లేషణ. ఇవి అవకాశాలు మాత్రమే, ధృవీకరించిన వాస్తవాలు కావు.",
        "letter_label": "ఫిర్యాదు ఉత్తరం (సవరించవచ్చు)",
        "who_title": "📬 ఎవరికి పంపాలి?",
        "searching": "{city}లో అధికారుల కోసం అధికారిక వెబ్‌సైట్లలో వెతుకుతున్నాను...",
        "search_unavail": "అధికారుల శోధన ప్రస్తుతం అందుబాటులో లేదు. క్రింద ఈమెయిల్‌ను మీరే నమోదు చేయవచ్చు.",
        "none_found": "ఈ శాఖకు ఆన్‌లైన్‌లో అధికారిక ఈమెయిల్ చిరునామాలు దొరకలేదు. క్రింద మీరే నమోదు చేయండి, లేదా కేంద్ర ఫిర్యాదుల పోర్టల్‌లో దాఖలు చేయండి:",
        "found_cap": "వెబ్‌లో దొరికాయి. ఈ ఫిర్యాదును ఎవరికి పంపాలో వారిని ఎంచుకోండి.",
        "badge_ok": "✅ మూల పేజీలో కనిపించింది",
        "badge_warn": "⚠️ పేజీలో నిర్ధారణ కాలేదు, పంపే ముందు సరిచూడండి",
        "badge_off": "🏛️ అధికారిక డొమైన్",
        "sources": "మూలాలు:",
        "extra_label": "ఇతర ఈమెయిల్ చిరునామాలు జోడించండి (ఐచ్ఛికం, కామాలతో వేరు చేయండి)",
        "file_btn": "ఫిర్యాదు దాఖలు చేసి ట్రాకింగ్ ప్రారంభించు",
        "bad_email": "దయచేసి కనీసం ఒక సరైన ఈమెయిల్ చిరునామాను నమోదు చేయండి, ఉదా. name@example.com.",
        "n8n_err": "n8nను చేరుకోలేకపోయాం: {err}",
        "step3": "3. ట్రాక్ చేయండి",
        "filed_msg": "ఫిర్యాదు {id} {time}న దాఖలైంది",
        "not_sent": " (ఈమెయిల్ పంపలేదు: గ్రహీత ఎంచుకోలేదు లేదా వెబ్‌హుక్ లేదు)",
        "sent_to": "గ్రహీతలు:", "status_lbl": "స్థితి",
        "flow_filed": "✅ దాఖలు", "flow_wait": "⏳ స్పందన కోసం ఎదురుచూపు",
        "flow_esc": "🚨 ఉన్నత స్థాయికి పంపాం", "flow_esc_pending": "⬜ ఉన్నత స్థాయికి",
        "sim_btn": "⏩ 7 రోజులు గడిచినా స్పందన రాలేదని అనుకోండి",
        "esc_spin": "ఉన్నతాధికారికి లేఖ సిద్ధం చేస్తున్నాను...",
        "esc_label": "ఉన్నతాధికారికి లేఖ", "dl_esc": "లేఖను డౌన్‌లోడ్ చేయండి",
        "hist_title": "🗂️ ఫిర్యాదుల చరిత్ర",
        "hist_empty": "ఈ సెషన్‌లో ఇంకా ఫిర్యాదులు దాఖలు చేయలేదు.",
        "status_esc": "🚨 ఉన్నత స్థాయికి పంపాం", "status_wait": "⏳ స్పందన కోసం ఎదురుచూపు",
        "severity_lbl": "తీవ్రత", "letter_lbl": "ఉత్తరం", "not_sent_lbl": "పంపలేదు",
        "dl_hist": "చరిత్రను డౌన్‌లోడ్ చేయండి (JSON)",
        "set_title": "⚙️ సెట్టింగ్స్",
        "set_cap": "ఈ సెషన్‌కు సేవ్ అవుతాయి. మీ పేరు, చిరునామా, ఫోన్ ఉత్తరాలలోని ఖాళీ స్థానాలను నింపుతాయి.",
        "set_name": "మీ పేరు", "set_phone": "ఫోన్", "set_addr": "చిరునామా",
        "set_city": "డిఫాల్ట్ నగరం / ప్రాంతం", "set_save": "సెట్టింగ్స్ సేవ్ చేయి",
        "set_saved": "సెట్టింగ్స్ సేవ్ అయ్యాయి.",
    },
    "Hindi": {
        "hero_sub": "नागरिक समस्या को स्पष्ट शिकायत में बदलें—और समाधान होने तक पीछा करें।",
        "nav_new": "नई शिकायत", "nav_history": "शिकायत इतिहास", "nav_settings": "सेटिंग्स",
        "language_lbl": "भाषा",
        "prefs": "प्राथमिकताएँ", "brand_tag": "नागरिक AI सहायक",
        "filed": "दर्ज", "escalated": "आगे भेजी",
        "urgent_title": "तत्काल खतरा?",
        "urgent_body": "राष्ट्रीय आपातकालीन नंबर <b>112</b> पर कॉल करें।",
        "urgent_alt": "तत्काल नहीं है? आप यहाँ भी शिकायत दर्ज कर सकते हैं:",
        "theme_dark": "डार्क मोड", "theme_light": "लाइट मोड",
        "step1": "1. समस्या बताइए",
        "step1_cap": "बताइए क्या हुआ। समस्या समझाने के लिए फोटो जोड़ सकते हैं।",
        "problem_label": "क्या समस्या है?",
        "problem_ph": "हमारी गली में 4 दिनों से पानी की आपूर्ति बंद है...",
        "letter_lang": "पत्र की भाषा", "city_label": "शहर / क्षेत्र", "city_ph": "जैसे राजमहेंद्रवरम",
        "photo": "फोटो (वैकल्पिक)",
        "draft_btn": "✨ मेरी शिकायत तैयार करें",
        "warn_describe": "कृपया पहले समस्या बताइए।",
        "warn_more": "कृपया थोड़ा और विवरण दें: समस्या क्या है, कहाँ है और कितने समय से है?",
        "drafting": "तैयार कर रहे हैं और विश्लेषण कर रहे हैं...",
        "need_more_info": "सही शिकायत लिखने के लिए मुझे थोड़ी और जानकारी चाहिए:",
        "not_civic": "यह टूल केवल नागरिक समस्याओं के लिए है, जैसे पानी की आपूर्ति, सड़कें, नाली, कचरा, बिजली या स्ट्रीट लाइट। कृपया किसी सार्वजनिक समस्या का वर्णन करें।",
        "ai_busy": "AI अभी व्यस्त है। कृपया एक मिनट बाद फिर कोशिश करें।",
        "step2": "2. जाँचें और दर्ज करें",
        "dept_lbl": "🏛️ ज़िम्मेदार विभाग", "severity": "⚠️ गंभीरता {n}/5",
        "why_title": "🔎 ऐसा क्यों हुआ होगा", "resp_title": "👥 कौन ज़िम्मेदार है",
        "analysis_note": "सामान्य जानकारी पर आधारित AI विश्लेषण। ये संभावनाएँ हैं, पुष्ट तथ्य नहीं।",
        "letter_label": "शिकायत पत्र (संपादित कर सकते हैं)",
        "who_title": "📬 किसे भेजना है?",
        "searching": "{city} में अधिकारियों के लिए आधिकारिक वेबसाइटों पर खोज रहे हैं...",
        "search_unavail": "अधिकारी खोज अभी उपलब्ध नहीं है। आप नीचे ईमेल खुद दर्ज कर सकते हैं।",
        "none_found": "इस विभाग के लिए ऑनलाइन कोई आधिकारिक ईमेल नहीं मिला। नीचे खुद दर्ज करें, या केंद्रीय शिकायत पोर्टल पर दर्ज करें:",
        "found_cap": "वेब पर मिले। जिन अधिकारियों को भेजना है उन्हें चुनें।",
        "badge_ok": "✅ स्रोत पेज पर मिला",
        "badge_warn": "⚠️ पेज पर पुष्टि नहीं हुई, भेजने से पहले जाँच लें",
        "badge_off": "🏛️ आधिकारिक डोमेन",
        "sources": "स्रोत:",
        "extra_label": "अन्य ईमेल पते जोड़ें (वैकल्पिक, कॉमा से अलग करें)",
        "file_btn": "शिकायत दर्ज करें और ट्रैकिंग शुरू करें",
        "bad_email": "कृपया कम से कम एक सही ईमेल पता दर्ज करें, जैसे name@example.com।",
        "n8n_err": "n8n से संपर्क नहीं हो सका: {err}",
        "step3": "3. ट्रैक करें",
        "filed_msg": "शिकायत {id} {time} को दर्ज हुई",
        "not_sent": " (ईमेल नहीं भेजा गया: कोई प्राप्तकर्ता नहीं चुना या वेबहुक नहीं है)",
        "sent_to": "प्राप्तकर्ता:", "status_lbl": "स्थिति",
        "flow_filed": "✅ दर्ज", "flow_wait": "⏳ जवाब का इंतज़ार",
        "flow_esc": "🚨 आगे भेजी गई", "flow_esc_pending": "⬜ आगे भेजना",
        "sim_btn": "⏩ मान लें 7 दिन बीत गए और कोई जवाब नहीं आया",
        "esc_spin": "उच्च अधिकारी को पत्र तैयार कर रहे हैं...",
        "esc_label": "उच्च अधिकारी को पत्र", "dl_esc": "पत्र डाउनलोड करें",
        "hist_title": "🗂️ शिकायत इतिहास",
        "hist_empty": "इस सत्र में अभी कोई शिकायत दर्ज नहीं हुई।",
        "status_esc": "🚨 आगे भेजी गई", "status_wait": "⏳ जवाब का इंतज़ार",
        "severity_lbl": "गंभीरता", "letter_lbl": "पत्र", "not_sent_lbl": "भेजा नहीं गया",
        "dl_hist": "इतिहास डाउनलोड करें (JSON)",
        "set_title": "⚙️ सेटिंग्स",
        "set_cap": "इस सत्र के लिए सहेजी जाती हैं। आपका नाम, पता और फोन पत्रों के खाली स्थानों में भरे जाएँगे।",
        "set_name": "आपका नाम", "set_phone": "फोन", "set_addr": "पता",
        "set_city": "डिफ़ॉल्ट शहर / क्षेत्र", "set_save": "सेटिंग्स सहेजें",
        "set_saved": "सेटिंग्स सहेजी गईं।",
    },
}


def ui_lang():
    return st.session_state.get("ui_lang", "English")


def t(key, **kw):
    s = UI.get(ui_lang(), {}).get(key) or UI["English"].get(key, key)
    return s.format(**kw) if kw else s


# ---------------------------------------------------------------- AI
SYSTEM = """You help citizens in India file civic complaints.
Return ONLY JSON with these keys:is_civic (true/false), needs_more_info (true/false), missing (list of short questions),
category, department, severity (integer 1-5), severity_reason, subject, letter, language,
possible_causes (list of 2-4 short strings), responsible (list of 2-4 objects with keys role, department, reason).

First decide is_civic. A civic issue is a problem with a public service or shared public space: water supply, roads, drainage, garbage, electricity, street lights, public transport, public health or safety. Personal devices, private disputes, shopping, homework and general questions are NOT civic. If it is not civic, set is_civic to false, set needs_more_info to false, and leave every other field empty. Otherwise set is_civic to true.

If the message does not clearly say WHAT the problem is, set needs_more_info to true,
put 1-3 short questions in "missing", and leave the other fields empty.
Otherwise set needs_more_info to false and fill everything in.

Rules:
- department: the specific local body (for example "Municipal Corporation - Sanitation Wing"), not just "Government".
  Keep department names and role titles in English.
- severity: 1 = minor inconvenience, 3 = affects daily life, 5 = immediate danger to health or safety.
- severity_reason: one short sentence.
- letter: a formal, polite complaint in the requested "Letter language", under 150 words.
  Always mention the location and how long the problem has lasted, if the user gave them.
  Use placeholders like [Your Name], [Address], [Phone] for details the user did not give.
- Use ONLY facts the user gave in the letter. Do not describe conditions, causes or impacts they did not mention.
- Never invent names, dates or numbers that the user did not provide.
- possible_causes: general reasons why this kind of problem commonly happens in Indian cities.
  Phrase each as a possibility ("may be due to ..."). Never put them in the letter.
- responsible: the roles and departments that normally handle this kind of problem
  (for example "Executive Engineer", "Sanitary Inspector"), with one short sentence on why.
  Use role titles only, never personal names.
- Write "missing", "severity_reason", "possible_causes" and each responsible "reason" in the
  "Interface language" given in the user message, in simple, readable words."""


def call_ai(contents, json_mode=True):
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM if json_mode else None,
        response_mime_type="application/json" if json_mode else None)
    for model in MODELS:
        for _ in range(2):
            try:
                r = client.models.generate_content(model=model, contents=contents, config=cfg)
                return json.loads(r.text) if json_mode else r.text
            except Exception as ex:
                print("AI error:", model, str(ex)[:200])
                if "503" not in str(ex) and "429" not in str(ex):
                    break  # not a temporary error, so try the next model
                time.sleep(1.5)
    return None


def _fetch(u):
    try:
        return requests.get(u, timeout=4, headers={"User-Agent": "Mozilla/5.0"}).text.lower()
    except Exception:
        return ""


def find_officers(city, dept):
    """Ask Gemini (with Google Search) for officer emails, then verify them against the source pages."""
    prompt = (
        f"Search the web for official contact details of the officers in {city}, India "
        f"who handle: {dept}.\n"
        "Return one line per officer in exactly this format:\n"
        "ROLE | EMAIL | SOURCE URL\n"
        "Only include email addresses you actually saw on a web page. Never guess, construct "
        "or complete an email address. If you find none, return the single word NONE."
    )
    cfg = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
    resp = None
    for model in MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            break
        except Exception as ex:
            print("Search error:", model, str(ex)[:200])
            time.sleep(1)
    if resp is None:
        return None

    text = resp.text or ""
    sources = []
    try:
        for ch in resp.candidates[0].grounding_metadata.grounding_chunks:
            sources.append((ch.web.title or "source", ch.web.uri))
    except Exception:
        pass

    with ThreadPoolExecutor(6) as pool:
        pages = "".join(pool.map(_fetch, [u for _, u in sources[:6]]))

    officers, seen = [], set()
    for line in text.splitlines():
        m = EMAIL_RE.search(line)
        if not m:
            continue
        email = m.group(0).lower().rstrip(".")
        if email in seen:
            continue
        seen.add(email)
        first = line.split("|")[0].strip(" *`-•")
        role = first if first and "@" not in first else "Officer"
        officers.append({"role": role, "email": email,
                         "verified": email in pages,
                         "official": email.endswith((".gov.in", ".nic.in"))})
    return {"officers": officers, "sources": sources[:3]}


def fill_placeholders(letter, s):
    for ph, key in [("[Your Name]", "name"), ("[Address]", "address"), ("[Phone]", "phone")]:
        if s.get(key):
            letter = letter.replace(ph, s[key])
    return letter


# ---------------------------------------------------------------- theme
def theme_css(dark, lang="English"):
    if dark:
        v = dict(bg="#0E1117", panel="#1A1D27", text="#F3F4F6", sub="#9CA3AF", border="#2F3445",
                 input="#232634", hero1="#1E1B4B", hero2="#2E1065", herob="#4338CA",
                 herot="#C7D2FE", accent="#818CF8", tint="#2B3050", themeico="☀️")
    else:
        v = dict(bg="#FFFFFF", panel="#F8FAFC", text="#111827", sub="#4B5563", border="#E5E7EB",
                 input="#F3F4F6", hero1="#EEF2FF", hero2="#F5F3FF", herob="#C7D2FE",
                 herot="#312E81", accent="#4F46E5", tint="#E0E7FF", themeico="🌙")
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Telugu:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');
.stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
[data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p, [data-testid="stHeading"] *,
button p, textarea, input, .card, .stat {
    font-family: "Source Sans", "Source Sans Pro", "Noto Sans Telugu", "Noto Sans Devanagari", sans-serif; }
.stApp, [data-testid="stHeader"] { background: @bg; }
[data-testid="stSidebar"] { background: @panel; }
.block-container { max-width: 900px; padding-top: 2.5rem; padding-bottom: 3rem; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
[data-testid="stWidgetLabel"] p, [data-testid="stHeading"] *, [data-testid="stCheckbox"] p,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label { color: @text; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: @sub; }
textarea, input, div[data-baseweb="select"] > div { background: @input !important; color: @text !important; border-radius: 10px; }
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
    border-radius: 10px; font-weight: 650; min-height: 46px; }
div[data-testid="stButton"] > button:not([kind="primary"]),
div[data-testid="stDownloadButton"] > button { background: @panel; border: 1px solid @border; }
div[data-testid="stButton"] > button:not([kind="primary"]) p,
div[data-testid="stDownloadButton"] > button p { color: @text; }
[data-testid="stExpander"] { border: 1px solid @border; border-radius: 12px; background: @panel; }
.stMarkdown .hero { background: linear-gradient(135deg, @hero1, @hero2); border: 1px solid @herob;
    border-radius: 18px; padding: 1.5rem 1.7rem; margin-bottom: 1.6rem; }
.stMarkdown .hero h1 { margin: 0; color: @herot; }
.stMarkdown .hero p { margin: .5rem 0 0; color: @sub; font-size: 1.05rem; }
.card { background: @panel; border: 1px solid @border; border-radius: 14px;
    padding: 1rem 1.2rem; margin: .6rem 0; color: @text; }
.dept-card { border-left: 6px solid @accent; }
.lbl { font-size: .8rem; letter-spacing: .04em; text-transform: uppercase; color: @sub; }
.dept { font-size: 1.45rem; font-weight: 700; margin: .25rem 0 .5rem; line-height: 1.3; }
.pill { display: inline-block; color: #fff !important; padding: .15rem .7rem;
    border-radius: 999px; font-size: .85rem; font-weight: 650; }
.why { margin-top: .5rem; color: @sub; }
.role { font-weight: 700; }
.small { color: @sub; font-size: .9rem; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .6rem; }
.brand { display: flex; align-items: center; gap: .8rem; padding: .3rem 0 1rem; }
.logo { width: 46px; height: 46px; flex: 0 0 46px; border-radius: 14px; font-size: 1.55rem;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #6366F1, #8B5CF6); box-shadow: 0 6px 14px rgba(99,102,241,.35); }
.bname { font-size: 1.2rem; font-weight: 800; line-height: 1.15; color: @text; }
.btag { font-size: .78rem; color: @sub; margin-top: .15rem; }

[data-testid="stSidebar"] div[data-testid="stButton"] > button,
[data-testid="stSidebar"] [data-testid="stPopover"] button {
    width: 100%; min-height: 50px; border-radius: 12px; padding: 0 .7rem 0 1rem; margin: 0;
    display: flex; align-items: center; justify-content: flex-start !important; text-align: left;
    transition: border-color .15s, box-shadow .15s; }
[data-testid="stSidebar"] div[data-testid="stButton"] > button > div,
[data-testid="stSidebar"] [data-testid="stPopover"] button > div:first-child {
    flex: 1; justify-content: flex-start !important; text-align: left; }
[data-testid="stSidebar"] div[data-testid="stButton"] > button p,
[data-testid="stSidebar"] [data-testid="stPopover"] button p {
    font-size: 1rem; font-weight: 650; text-align: left; margin: 0; color: @text; }
[data-testid="stSidebar"] [data-testid="stPopover"] button { background: @panel; border: 1px solid @border; }
[data-testid="stSidebar"] button[kind="primary"] p { color: #fff; }
[data-testid="stSidebar"] button:hover { border-color: @accent; box-shadow: 0 2px 10px rgba(99,102,241,.18); }

/* emoji tile on the right side of each button */
[data-testid="stSidebar"] div[data-testid="stButton"] > button::after,
[data-testid="stSidebar"] [data-testid="stPopover"] button::after {
    content: var(--ico, ""); margin-left: auto; flex: 0 0 34px; width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
    border-radius: 10px; background: @tint; }
[data-testid="stSidebar"] button[kind="primary"]::after { background: rgba(255,255,255,.25); }
.st-key-nav_new { --ico: "📝"; }
.st-key-nav_history { --ico: "🗂️"; }
.st-key-nav_settings { --ico: "⚙️"; }
.st-key-side_prefs { --ico: "🌐"; }
.st-key-theme_btn { --ico: "@themeico"; }

/* preferences box */
.st-key-side_prefs { background: @bg; border: 1px solid @border; border-radius: 16px;
    padding: .85rem; margin-top: .4rem; }
.st-key-side_prefs [data-testid="stVerticalBlock"], .st-key-side_prefs { gap: .55rem; }
.st-key-side_prefs .lbl { margin: 0 0 .1rem .15rem; }

/* stats and emergency card */
[data-testid="stSidebar"] .card, [data-testid="stSidebar"] .statrow { margin: 0; }
[data-testid="stSidebar"] .card { border-radius: 14px; padding: .9rem 1rem; }
.statrow { display: flex; gap: .6rem; padding-bottom: 1rem; margin-top: .4rem; }
.stat { flex: 1; background: @bg; border: 1px solid @border; border-radius: 12px;
    text-align: center; padding: .6rem .4rem; font-size: .85rem; color: @text; }
.stat b { display: block; font-size: 1.4rem; }
[data-testid="stPopoverBody"] { background: @panel; border: 1px solid @border; border-radius: 12px; }
[data-testid="stPopoverBody"] p { color: @text; }
[data-testid="stPopoverBody"] button[kind="primary"] p { color: #fff; }
</style>
"""
    if lang != "English":
        # Telugu / Hindi glyphs look thin in fallback fonts, so use heavier weights and darker text
        extra = """
.stMarkdown p, .stMarkdown li, [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p,
textarea, input, button p, .small, .why, .stat, .lbl, .card { font-weight: 600 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, [data-testid="stHeading"] * { font-weight: 700 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .small, .why { color: @text !important; opacity: .9; }
textarea::placeholder, input::placeholder { font-weight: 500; opacity: 1; color: @sub; }
textarea { line-height: 1.7; }
"""
        css = css.replace("</style>", extra + "</style>")
    for k, val in v.items():
        css = css.replace("@" + k, val)
    return css


# ---------------------------------------------------------------- page setup
st.set_page_config(page_title="Complaint Chaser | Civic AI", page_icon="📮",
                   layout="centered", initial_sidebar_state="expanded")

st.session_state.setdefault("history", [])
st.session_state.setdefault("settings", {"name": "", "phone": "", "address": "", "city": ""})
st.session_state.setdefault("page", "new")
st.session_state.setdefault("dark", False)
settings = st.session_state.settings

PAGES = ["new", "history", "settings"]

with st.sidebar:
    st.markdown(
        f'<div class="brand"><div class="logo">📮</div><div>'
        f'<div class="bname">Complaint Chaser</div>'
        f'<div class="btag">{e(t("brand_tag"))}</div></div></div>', unsafe_allow_html=True)

    for p in PAGES:
        active = st.session_state.page == p
        if st.button(t("nav_" + p), key=f"nav_{p}", type="primary" if active else "secondary",
                     use_container_width=True):
            st.session_state.page = p
            st.rerun()

    with st.container(key="side_prefs"):
        st.markdown(f'<div class="lbl">{e(t("prefs"))}</div>', unsafe_allow_html=True)
        with st.popover(t("language_lbl"), use_container_width=True):
            for L in LANGS:
                if st.button(LANG_NAMES[L], key=f"lang_{L}", use_container_width=True,
                             type="primary" if L == ui_lang() else "secondary"):
                    st.session_state.ui_lang = L
                    st.rerun()
        if st.button(t("theme_light") if st.session_state.dark else t("theme_dark"),
                     key="theme_btn", use_container_width=True):
            st.session_state.dark = not st.session_state.dark
            st.rerun()

    hist = st.session_state.history
    esc = sum(1 for h in hist if h["escalation"])
    st.markdown(
        f'<div class="statrow"><div class="stat"><b>{len(hist)}</b>{e(t("filed"))}</div>'
        f'<div class="stat"><b>{esc}</b>{e(t("escalated"))}</div></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="card"><div class="lbl">{e(t("urgent_title"))}</div>'
        f'{t("urgent_body")}'
        f'<div class="small">{e(t("urgent_alt"))} '
        '<a href="https://pgportal.gov.in" target="_blank">pgportal.gov.in</a></div></div>',
        unsafe_allow_html=True)

page = st.session_state.page

dark = st.session_state.dark
st.markdown(theme_css(dark, ui_lang()), unsafe_allow_html=True)

st.markdown(f"""
<div class="hero">
<h1>📮 Complaint Chaser</h1>
<p>{e(t("hero_sub"))}</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- New complaint
def page_new():
    st.subheader(t("step1"))
    st.caption(t("step1_cap"))
    problem = st.text_area(t("problem_label"), placeholder=t("problem_ph"), key="problem")
    c1, c2 = st.columns(2)
    language = c1.selectbox(t("letter_lang"), LANGS, index=LANGS.index(ui_lang()),
                            format_func=lambda x: LANG_NAMES[x])
    city = c2.text_input(t("city_label"), value=settings["city"], placeholder=t("city_ph"), key="city")
    photo = st.file_uploader(t("photo"), type=["jpg", "jpeg", "png"], key="photo")

    if st.button(t("draft_btn"), type="primary", use_container_width=True):
        if not problem.strip():
            st.warning(t("warn_describe"))
        elif len(problem.split()) < 4:
            st.session_state.pop("draft", None)
            st.warning(t("warn_more"))
        else:
            prompt = (f"Problem: {problem[:1500]}\nCity: {city}\nLetter language: {language}\n"
                      f"Interface language: {ui_lang()}")
            contents = [prompt]
            if photo:
                contents = [types.Part.from_bytes(data=photo.getvalue(), mime_type=photo.type), prompt]
            with st.spinner(t("drafting")):
                data = call_ai(contents)

            if data and str(data.get("is_civic")).lower() == "false":
                st.session_state.pop("draft", None)
                st.error(t("not_civic"))
            elif data and data.get("needs_more_info"):
                st.session_state.pop("draft", None)
                st.warning(t("need_more"))
                for q in data.get("missing", []):
                    st.write("•", q)
            elif data:
                data["letter"] = fill_placeholders(data.get("letter", ""), settings)
                data["_city"] = city
                data["_lang"] = language
                data["_id"] = uuid.uuid4().hex[:8]
                st.session_state.draft = data
                st.session_state.pop("filed", None)
            else:
                st.error(t("ai_busy"))

    if "draft" in st.session_state:
        step2()
    if "filed" in st.session_state:
        step3()


def step2():
    d = st.session_state.draft
    dept = d.get("department", "-")
    try:
       sev = int(d.get("severity", 3))
    except Exception:
       sev = 3
    col = SEV_COLORS.get(sev, "#d97706")

    st.subheader(t("step2"))

    st.markdown(
        f'<div class="card dept-card"><div class="lbl">{e(t("dept_lbl"))}</div>'
        f'<div class="dept">{e(dept)}</div>'
        f'<span class="pill" style="background:{col}">{e(t("severity", n=sev))}</span>'
        f'<div class="why">{e(d.get("severity_reason"))}</div></div>',
        unsafe_allow_html=True)

    causes = d.get("possible_causes") or []
    resp = d.get("responsible") or []
    if causes or resp:
        if causes:
            st.markdown(f"#### {t('why_title')}")
            items = "".join(f"<li>{e(c)}</li>" for c in causes)
            st.markdown(f'<div class="card"><ul style="margin:0">{items}</ul></div>',
                        unsafe_allow_html=True)
        if resp:
            st.markdown(f"#### {t('resp_title')}")
            for r in resp:
                st.markdown(
                    f'<div class="card"><span class="role">{e(r.get("role"))}</span> '
                    f'· {e(r.get("department"))}<div class="small">{e(r.get("reason"))}</div></div>',
                    unsafe_allow_html=True)
        st.caption(t("analysis_note"))

    letter = st.text_area(t("letter_label"), d.get("letter", ""), height=360,
                          key=f"letter_{d.get('_id', 'x')}")
    st.caption("AI-drafted. Please review and edit before sending.")

    st.markdown(f"#### {t('who_title')}")
    city = d.get("_city") or settings["city"] or "India"
    key = f"{city.lower()}|{dept}"
    cache = st.session_state.setdefault("officers_cache", {})
    if key not in cache:
        with st.spinner(t("searching", city=city)):
            cache[key] = find_officers(city, dept)
    res = cache[key]

    recipients = []
    if res is None:
        st.warning(t("search_unavail"))
    elif not res["officers"]:
        st.info(t("none_found") + " https://pgportal.gov.in")
    else:
        st.caption(t("found_cap"))
        for o in res["officers"]:
            badges = [t("badge_ok") if o["verified"] else t("badge_warn")]
            if o["official"]:
                badges.append(t("badge_off"))
            checked = st.checkbox(f"**{o['role']}** · {o['email']}  \n{' · '.join(badges)}",
                                  value=o["verified"], key=f"off_{key}_{o['email']}")
            if checked:
                recipients.append(o["email"])
        if res["sources"]:
            st.caption(t("sources") + " " + " · ".join(f"[{ti}]({u})" for ti, u in res["sources"]))

    extra = st.text_input(t("extra_label"), key="extra_email")
    for x in extra.split(","):
        x = x.strip()
        if x and EMAIL_RE.fullmatch(x):
            recipients.append(x)
    recipients = list(dict.fromkeys(recipients))

    if st.button(t("file_btn"), type="primary"):
               bad = [e for e in recipients if not EMAIL_RE.match(e.strip())]
               if not recipients or bad:
                  st.warning(t("bad_email"))
                  if bad:
                     st.caption(", ".join(bad))
                  st.stop()
               cid = "CC-" + uuid.uuid4().hex[:6].upper()
               sent = False
               if WEBHOOK_URL and recipients:
                   try:
                      r=requests.post(WEBHOOK_URL, timeout=15, json={
                      "id": cid, "to": ", ".join(recipients),
                      "subject": f"[{cid}] {d.get('subject', 'Complaint')}",
                      "letter": letter})
                      r.raise_for_status()
                      sent = True
                   except Exception as ex:
                       st.error(t("n8n_err", err=ex))
               filed = {"id": cid, "time": datetime.now(IST).strftime("%d %b %Y, %I:%M %p"),
                 "letter": letter, "sent": sent, "escalation": None, "dept": dept,
                  "severity": sev, "recipients": recipients, "lang": d.get("_lang", "English")}    
               st.session_state.filed = filed
               st.session_state.history.append(filed)  # same object, so later updates show in history


def step3():
    f = st.session_state.filed
    st.subheader(t("step3"))
    st.success(t("filed_msg", id=f["id"], time=f["time"]) + ("" if f["sent"] else t("not_sent")))
    if f["recipients"]:
        st.caption(t("sent_to") + " " + ", ".join(f["recipients"]))
    st.markdown(f"**{t('status_lbl')}**")
    st.markdown(f"{t('flow_filed')}  →  {t('flow_wait')}  →  "
                + (t("flow_esc") if f["escalation"] else t("flow_esc_pending")))

    if st.button(t("sim_btn")):
        with st.spinner(t("esc_spin")):
            f["escalation"] = call_ai(
                f"Write a firm but polite escalation letter to a senior officer, in {f['lang']}. "
                f"No reply was received within 7 days for complaint {f['id']} to {f['dept']}. "
                f"Original complaint:\n{f['letter']}", json_mode=False)
    if f["escalation"]:
        st.text_area(t("esc_label"), f["escalation"], height=260, key=f"esc_{f['id']}")
        st.download_button(t("dl_esc"), f["escalation"], file_name=f"{f['id']}_escalation.txt")


# ---------------------------------------------------------------- History
def page_history():
    st.subheader(t("hist_title"))
    hist = st.session_state.history
    if not hist:
        st.info(t("hist_empty"))
        return
    for h in reversed(hist):
        status = t("status_esc") if h["escalation"] else t("status_wait")
        with st.expander(f"{h['id']} · {h['dept']} · {h['time']}"):
            st.markdown(f"**{t('status_lbl')}:** {status}  \n**{t('severity_lbl')}:** {h['severity']}/5  \n"
                        f"**{t('sent_to')}** {', '.join(h['recipients']) or t('not_sent_lbl')}")
            st.text_area(t("letter_lbl"), h["letter"], height=200, disabled=True, key=f"hl_{h['id']}")
            if h["escalation"]:
                st.text_area(t("esc_label"), h["escalation"], height=200,
                             disabled=True, key=f"he_{h['id']}")
    st.download_button(t("dl_hist"), json.dumps(hist, indent=2, ensure_ascii=False),
                       file_name="complaint_history.json")


# ---------------------------------------------------------------- Settings
def page_settings():
    st.subheader(t("set_title"))
    st.caption(t("set_cap"))
    with st.form("settings_form"):
        name = st.text_input(t("set_name"), value=settings["name"])
        phone = st.text_input(t("set_phone"), value=settings["phone"])
        address = st.text_input(t("set_addr"), value=settings["address"])
        city = st.text_input(t("set_city"), value=settings["city"])
        if st.form_submit_button(t("set_save"), type="primary"):
            settings.update(name=name, phone=phone, address=address, city=city)
            st.success(t("set_saved"))


if page == "new":
    page_new()
elif page == "history":
    page_history()
else:
    page_settings()

