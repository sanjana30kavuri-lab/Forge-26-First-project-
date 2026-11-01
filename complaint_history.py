"""
Complaint history for Complaint Chaser (Streamlit).

Drop this file next to your main app and:
  1. call save_complaint(...) when a complaint is filed
  2. call render_history_page() on the "Complaint history" page
  3. use sidebar_counts() for the Filed / Escalated boxes
"""
from __future__ import annotations

import hashlib
import os
import smtplib
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.message import EmailMessage
from html import escape as e
from pathlib import Path

import streamlit as st

# ---- Match these to your app's navigation ---------------------------------
NAV_KEY = "page"              # st.session_state key your sidebar uses
NEW_COMPLAINT_PAGE = "new"            # your sidebar stores "new", "history", "settings"
# ---------------------------------------------------------------------------

DB_PATH = Path(os.getenv("CC_DB_PATH", "complaints.db"))
UPLOAD_DIR = Path(os.getenv("CC_UPLOAD_DIR", "uploads"))
DEMO_MODE = os.getenv("CC_DEMO") == "1"   # shows an "Advance status" button for testing

STATUSES = ["Submitted", "Under review", "In progress", "Resolved"]

CATEGORY_KEYWORDS = {
    "Water": ["water", "tap", "pipe", "supply", "leak"],
    "Roads": ["road", "pothole", "footpath", "traffic", "bridge"],
    "Garbage": ["garbage", "trash", "waste", "dustbin", "litter"],
    "Streetlight": ["streetlight", "street light", "lamp", "light pole"],
    "Drainage": ["drain", "sewage", "sewer", "overflow", "flood"],
    "Electricity": ["electric", "power cut", "transformer", "wire", "outage"],
}
# Days in which each kind of problem should reasonably be fixed
SLA_DAYS = {"Water": 3, "Roads": 14, "Garbage": 2, "Streetlight": 5,
            "Drainage": 5, "Electricity": 2, "Other": 10}


# ============================== Storage ====================================

@contextmanager
def _db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)
    with _db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS complaints(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ref TEXT UNIQUE,
                owner TEXT NOT NULL,
                title TEXT, category TEXT, description TEXT, letter TEXT,
                city TEXT, language TEXT, photo_path TEXT,
                status TEXT DEFAULT 'Submitted',
                escalated INTEGER DEFAULT 0,
                created_at TEXT, updated_at TEXT, due_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER, note TEXT, created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_owner ON complaints(owner);
            """
        )


def _owner_key(raw: str) -> str:
    """Turn an email/phone into a private id, so the raw number never goes in the URL."""
    salt = os.getenv("HISTORY_SALT", "complaint-chaser")
    return "u-" + hashlib.sha256((salt + raw.strip().lower()).encode()).hexdigest()[:16]


def set_owner(raw: str) -> None:
    """Link this browser to a phone/email. The private id is kept in the page address
    (?u=...), so the history survives a refresh."""
    if not raw or not raw.strip():
        return
    key = _owner_key(raw)
    st.session_state["owner"] = key
    st.query_params["u"] = key


def clear_owner() -> None:
    st.session_state.pop("owner", None)
    st.session_state.pop("guest_id", None)
    st.query_params.clear()


def get_owner() -> str:
    """Saved id (session or page address), else a private id for this browser session,
    so visitors never see each other's complaints."""
    if st.session_state.get("owner"):
        return st.session_state["owner"]
    q = st.query_params.get("u")
    if q:
        st.session_state["owner"] = q
        return q
    return st.session_state.setdefault("guest_id", "guest-" + uuid.uuid4().hex[:10])


def guess_category(text: str) -> str:
    low = text.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in low for w in words):
            return cat
    return "Other"


def _make_title(text: str) -> str:
    first = text.strip().split("\n")[0].split(".")[0].strip()
    return first if len(first) <= 70 else first[:67].rstrip() + "..."


def _add_event(con, complaint_id: int, note: str) -> None:
    con.execute(
        "INSERT INTO events(complaint_id, note, created_at) VALUES (?,?,?)",
        (complaint_id, note, datetime.now().isoformat(timespec="seconds")),
    )


def save_complaint(description: str, city: str = "", language: str = "English",
                   letter: str = "", photo=None, owner: str | None = None) -> str:
    """Save a filed complaint. `photo` is the object from st.file_uploader (or None).
    Returns the complaint reference, e.g. CF-2026-00012."""
    init_db()
    now = datetime.now()
    category = guess_category(description)
    photo_path = ""
    if photo is not None:
        ext = Path(getattr(photo, "name", "photo.jpg")).suffix or ".jpg"
        photo_path = str(UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}")
        Path(photo_path).write_bytes(photo.getvalue())

    with _db() as con:
        cur = con.execute(
            """INSERT INTO complaints(owner,title,category,description,letter,city,
               language,photo_path,created_at,updated_at,due_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (owner or get_owner(), _make_title(description), category, description,
             letter, city.strip(), language, photo_path,
             now.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"),
             (now + timedelta(days=SLA_DAYS[category])).isoformat(timespec="seconds")),
        )
        cid = cur.lastrowid
        ref = f"CF-{now.year}-{cid:05d}"
        con.execute("UPDATE complaints SET ref=? WHERE id=?", (ref, cid))
        _add_event(con, cid, "Complaint filed.")
    return ref


def list_complaints(owner: str, status: str = "All", category: str = "All",
                    query: str = "", sort: str = "Newest first"):
    init_db()
    sql, args = "SELECT * FROM complaints WHERE owner=?", [owner]
    if status != "All":
        sql += " AND status=?"; args.append(status)
    if category != "All":
        sql += " AND category=?"; args.append(category)
    if query.strip():
        sql += " AND (title LIKE ? OR description LIKE ? OR ref LIKE ?)"
        args += [f"%{query.strip()}%"] * 3
    order = {"Newest first": "created_at DESC", "Oldest first": "created_at ASC",
             "Due soonest": "(status='Resolved') ASC, due_at ASC"}[sort]
    with _db() as con:
        return con.execute(sql + " ORDER BY " + order, args).fetchall()


def get_events(cid: int):
    with _db() as con:
        return con.execute(
            "SELECT * FROM events WHERE complaint_id=? ORDER BY id DESC", (cid,)
        ).fetchall()


def sidebar_counts(owner: str | None = None) -> tuple[int, int]:
    """(filed, escalated) for the two boxes in the sidebar."""
    init_db()
    with _db() as con:
        row = con.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(escalated),0) AS esc "
            "FROM complaints WHERE owner=?", (owner or get_owner(),)
        ).fetchone()
    return row["n"], row["esc"]


# ============================== Actions ====================================

def notify(owner: str, subject: str, body: str) -> None:
    """Email the owner when their complaint changes. Needs SMTP_HOST, SMTP_USER,
    SMTP_PASSWORD env vars and an email address as the owner. Silently skipped otherwise."""
    host = os.getenv("SMTP_HOST")
    if not host or "@" not in owner:
        return
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, os.getenv("SMTP_USER"), owner
        msg.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587"))) as s:
            s.starttls()
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            s.send_message(msg)
    except Exception:
        pass  # never break the app because an email failed


def update_status(cid: int, status: str, note: str) -> None:
    with _db() as con:
        con.execute("UPDATE complaints SET status=?, updated_at=? WHERE id=?",
                    (status, datetime.now().isoformat(timespec="seconds"), cid))
        _add_event(con, cid, note)
        row = con.execute("SELECT ref, owner FROM complaints WHERE id=?", (cid,)).fetchone()
    notify(row["owner"], f"{row['ref']}: {status}", note)


def advance_status(cid: int) -> None:
    with _db() as con:
        cur = con.execute("SELECT status FROM complaints WHERE id=?", (cid,)).fetchone()["status"]
    nxt = STATUSES[min(STATUSES.index(cur) + 1, len(STATUSES) - 1)]
    update_status(cid, nxt, f"Status changed to {nxt}.")


def escalate(cid: int) -> None:
    with _db() as con:
        con.execute("UPDATE complaints SET escalated=1, updated_at=? WHERE id=?",
                    (datetime.now().isoformat(timespec="seconds"), cid))
        _add_event(con, cid, "You escalated this complaint.")


def add_followup(cid: int) -> None:
    key = f"fu_{cid}"
    note = st.session_state.get(key, "").strip()
    if note:
        with _db() as con:
            _add_event(con, cid, f"Your update: {note}")
        st.session_state[key] = ""


def withdraw(cid: int) -> None:
    with _db() as con:
        row = con.execute("SELECT photo_path FROM complaints WHERE id=?", (cid,)).fetchone()
        con.execute("DELETE FROM events WHERE complaint_id=?", (cid,))
        con.execute("DELETE FROM complaints WHERE id=?", (cid,))
    if row and row["photo_path"]:
        Path(row["photo_path"]).unlink(missing_ok=True)


def _go_new_complaint() -> None:
    st.session_state[NAV_KEY] = NEW_COMPLAINT_PAGE


def _set_owner() -> None:
    set_owner(st.session_state.get("owner_input", ""))


# ============================== Rendering ==================================

CSS = """
<style>
.cc-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.cc-title{font-size:1.1rem;font-weight:700;line-height:1.3}
.cc-badge{white-space:nowrap;font-size:.8rem;font-weight:600;padding:3px 10px;border-radius:999px}
.cc-submitted{background:rgba(100,116,139,.16);color:#64748b}
.cc-under-review{background:rgba(245,158,11,.16);color:#b45309}
.cc-in-progress{background:rgba(79,70,229,.15);color:#4f46e5}
.cc-resolved{background:rgba(16,185,129,.16);color:#047857}
.cc-meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:8px 0 18px;font-size:.85rem}
.cc-chip{background:rgba(99,102,241,.10);color:#4f46e5;padding:2px 9px;border-radius:8px;font-weight:500}
.cc-esc{background:rgba(220,38,38,.12);color:#dc2626}
.cc-when{opacity:.65}
.cc-due{font-weight:600}
.cc-due.ok{color:#047857}
.cc-due.late{color:#dc2626}
.cc-steps{display:flex;margin:4px 0 6px}
.cc-step{flex:1;position:relative;text-align:center;font-size:.8rem}
.cc-step:not(:first-child)::before{content:"";position:absolute;top:10px;left:-50%;width:100%;
  height:2px;background:rgba(99,102,241,.22)}
.cc-step.done::before,.cc-step.now::before{background:#4f46e5}
.cc-dot{position:relative;z-index:1;display:flex;align-items:center;justify-content:center;
  width:22px;height:22px;margin:0 auto 6px;border-radius:50%;font-size:12px;color:#fff;
  background:rgba(99,102,241,.22)}
.cc-step.done .cc-dot{background:#4f46e5}
.cc-step.now .cc-dot{background:#fff;border:6px solid #4f46e5;box-sizing:border-box}
.cc-step.todo{opacity:.55}
.cc-step.now .cc-lbl{font-weight:700;color:#4f46e5}
.cc-empty{border:1px dashed rgba(99,102,241,.4);border-radius:14px;padding:28px 20px;
  text-align:center;background:rgba(99,102,241,.05);margin-bottom:12px}
.cc-empty b{font-size:1.1rem}
</style>
"""


def _fmt(iso: str) -> str:
    d = datetime.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def _due_text(row) -> tuple[str, str]:
    if row["status"] == "Resolved":
        return f"Resolved on {_fmt(row['updated_at'])}", "ok"
    days = (datetime.fromisoformat(row["due_at"]).date() - datetime.now().date()).days
    if days >= 0:
        return f"Expected by {_fmt(row['due_at'])}", "ok"
    n = -days
    return f"Overdue by {n} day{'s' if n != 1 else ''}", "late"


def _timeline(status: str) -> str:
    idx = STATUSES.index(status)
    out = ""
    for i, s in enumerate(STATUSES):
        cls = "done" if i < idx or status == "Resolved" else "now" if i == idx else "todo"
        mark = "&#10003;" if cls == "done" else ""
        out += f'<div class="cc-step {cls}"><div class="cc-dot">{mark}</div><div class="cc-lbl">{s}</div></div>'
    return f'<div class="cc-steps">{out}</div>'


def _card(row) -> None:
    cid = row["id"]
    due_label, due_kind = _due_text(row)
    slug = row["status"].lower().replace(" ", "-")
    city = f'<span class="cc-chip">{e(row["city"])}</span>' if row["city"] else ""
    esc = '<span class="cc-chip cc-esc">Escalated</span>' if row["escalated"] else ""

    with st.container(border=True):
        st.markdown(
            '<div class="cc-head">'
            f'<div class="cc-title">{e(row["title"])}</div>'
            f'<span class="cc-badge cc-{slug}">{e(row["status"])}</span></div>'
            '<div class="cc-meta">'
            f'<span class="cc-chip">{e(row["ref"])}</span>'
            f'<span class="cc-chip">{e(row["category"])}</span>{city}{esc}'
            f'<span class="cc-when">Filed {_fmt(row["created_at"])}</span>'
            f'<span class="cc-due {due_kind}">{e(due_label)}</span></div>'
            + _timeline(row["status"]),
            unsafe_allow_html=True,
        )

        with st.expander("Details and actions"):
            st.markdown("**What you reported**")
            st.write(row["description"])
            if row["photo_path"] and Path(row["photo_path"]).exists():
                st.image(row["photo_path"], width=280)

            if row["letter"]:
                st.markdown("**Your complaint letter**")
                st.text_area("Letter", row["letter"], height=180, disabled=True,
                             key=f"ltr_{cid}", label_visibility="collapsed")
                st.download_button("Download letter", row["letter"],
                                   file_name=f"{row['ref']}.txt", key=f"dl_{cid}")

            st.markdown("**Activity**")
            for ev in get_events(cid):
                st.markdown(f"- {ev['note']} ({_fmt(ev['created_at'])})")

            if row["status"] != "Resolved":
                st.text_input("Add an update", key=f"fu_{cid}",
                              placeholder="e.g. Still no water, now 6 days")
                st.button("Save update", key=f"fub_{cid}", on_click=add_followup, args=(cid,))

            cols = st.columns(4)
            if row["status"] != "Resolved":
                cols[0].button("Mark as resolved", key=f"res_{cid}", on_click=update_status,
                               args=(cid, "Resolved", "You marked this as resolved."))
                if not row["escalated"]:
                    cols[1].button("Escalate", key=f"esc_{cid}", type="primary",
                                   on_click=escalate, args=(cid,))
            else:
                cols[0].button("Not fixed, reopen", key=f"reo_{cid}", on_click=update_status,
                               args=(cid, "Under review", "You reopened this: the issue was not fixed."))
            if row["status"] == "Submitted":
                cols[2].button("Withdraw", key=f"wd_{cid}", on_click=withdraw, args=(cid,))
            if DEMO_MODE and row["status"] != "Resolved":
                cols[3].button("Advance (demo)", key=f"adv_{cid}", on_click=advance_status, args=(cid,))

            if row["escalated"] and row["status"] != "Resolved":
                st.info("Next step: file the same letter on pgportal.gov.in so a higher authority sees it.")


def render_history_page() -> None:
    init_db()
    st.markdown(CSS, unsafe_allow_html=True)

    owner = get_owner()
    if not st.session_state.get("owner"):
        with st.container(border=True):
            st.markdown("**Keep your history after a refresh**")
            c1, c2 = st.columns([4, 1])
            c1.text_input("Email or phone", key="owner_input", label_visibility="collapsed",
                          placeholder="Your email or phone number")
            c2.button("Save", on_click=_set_owner, use_container_width=True)
            st.caption("Save your number before you file. Without it, your complaints are visible "
                       "only in this browser session and a refresh starts a new one.")
    else:
        st.caption("Your history is linked to your saved number. Bookmark this page to open it "
                   "again after a refresh, or enter the same number on another device.")
        st.button("Use a different number", on_click=clear_owner)

    all_rows = list_complaints(owner)
    if not all_rows:
        st.markdown(
            '<div class="cc-empty"><b>You haven\'t filed a complaint yet</b><br>'
            "Describe the problem and we'll draft the letter and track it for you.</div>",
            unsafe_allow_html=True,
        )
        st.button("File a complaint", type="primary", on_click=_go_new_complaint)
        return

    f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
    query = f1.text_input("Search", placeholder="Search by ID or keyword", label_visibility="collapsed")
    status = f2.selectbox("Status", ["All"] + STATUSES, label_visibility="collapsed",
                          format_func=lambda s: "All statuses" if s == "All" else s)
    cats = ["All"] + sorted({r["category"] for r in all_rows})
    category = f3.selectbox("Category", cats, label_visibility="collapsed",
                            format_func=lambda s: "All categories" if s == "All" else s)
    sort = f4.selectbox("Sort", ["Newest first", "Oldest first", "Due soonest"],
                        label_visibility="collapsed")

    rows = list_complaints(owner, status, category, query, sort)
    st.caption(f"Showing {len(rows)} of {len(all_rows)} complaints")
    if not rows:
        st.info("No complaints match these filters. Clear the search or pick a different status.")
    for r in rows:
        _card(r)
