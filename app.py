import streamlit as st
import time
import os
import uuid
import tempfile
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from utils.audio_processor import process_input
from utils.db import (
    init_db,
    save_session, load_session, get_user_sessions,
    update_chat_history, delete_session
)
from utils.auth import render_auth
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, load_rag_chain, ask_question

init_db()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS (Minimalist Cyberpunk Theme) ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
    --bg: #0a0a0f; --surface: #111118; --surface-2: #1a1a25;
    --border: #2a2a3a; --accent: #7c3aed; --accent-glow: #9f67ff;
    --accent-2: #06b6d4; --text: #e8e8f0; --text-muted: #7070a0;
    --success: #10b981; --warning: #f59e0b; --danger: #ef4444;
}

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background: var(--bg) !important; }

.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(124,58,237,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,58,237,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none; z-index: 0;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
h1,h2,h3,h4,h5,h6 { font-family: 'Syne', sans-serif !important; color: var(--text) !important; }

.hero-title {
    font-family: 'Syne', sans-serif; font-size: clamp(2rem,5vw,3.5rem);
    font-weight: 800; line-height: 1.1; margin: 0;
    background: linear-gradient(135deg,#ffffff 0%,var(--accent-glow) 50%,var(--accent-2) 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
    color: var(--text-muted); letter-spacing: 0.2em; text-transform: uppercase; margin-top: 0.5rem;
}

.card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.5rem; margin-bottom: 1rem; position: relative; overflow: hidden; transition: border-color 0.2s;
}
.card:hover { border-color: var(--accent); }
.card::before {
    content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
}
.card-title {
    font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.75rem;
}
.card-content { font-size: 0.875rem; line-height: 1.7; color: var(--text); }

.badge {
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
}
.badge-purple { background: rgba(124,58,237,0.2); color: var(--accent-glow); border: 1px solid rgba(124,58,237,0.3); }
.badge-cyan   { background: rgba(6,182,212,0.15); color: var(--accent-2);    border: 1px solid rgba(6,182,212,0.3); }
.badge-green  { background: rgba(16,185,129,0.15); color: var(--success);    border: 1px solid rgba(16,185,129,0.3); }

.stTextInput > div > div > input, .stSelectbox > div > div {
    background: var(--surface-2) !important; border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important; box-shadow: 0 0 0 2px rgba(124,58,237,0.2) !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #5b21b6) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
    font-size: 0.875rem !important; letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important; transition: all 0.2s !important; text-transform: uppercase !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 8px 25px rgba(124,58,237,0.4) !important; }
.stButton > button[kind="secondary"] { background: var(--surface-2) !important; border: 1px solid var(--border) !important; }

.status-bar {
    display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
    background: var(--surface-2); border-radius: 8px; margin: 0.4rem 0;
    border: 1px solid var(--border); font-size: 0.8rem;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-active  { background: var(--accent-glow); box-shadow: 0 0 8px var(--accent-glow); animation: pulse 1.5s infinite; }
.dot-done    { background: var(--success); }
.dot-pending { background: var(--border); }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

.chat-container {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.25rem; max-height: 420px; overflow-y: auto; margin-bottom: 1rem;
}
.chat-msg { margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.2rem; }
.chat-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; }
.chat-bubble { display: inline-block; padding: 0.6rem 1rem; border-radius: 10px; font-size: 0.85rem; line-height: 1.6; max-width: 90%; }
.user-label  { color: var(--accent-glow); }
.bot-label   { color: var(--accent-2); }
.user-bubble { background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.25); align-self: flex-end; }
.bot-bubble  { background: rgba(6,182,212,0.1);  border: 1px solid rgba(6,182,212,0.2);   align-self: flex-start; }

.transcript-box {
    background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px;
    padding: 1.25rem; font-size: 0.82rem; line-height: 1.8; max-height: 300px;
    overflow-y: auto; color: var(--text-muted); white-space: pre-wrap; word-break: break-word;
}

.stProgress > div > div > div { background: var(--accent) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }
label { color: var(--text-muted) !important; font-size: 0.8rem !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "user": None,
    "result": None,
    "chat_history": [],
    "pipeline_done": False,
    "pipeline_steps": {},
    "input_mode": "url",
    "active_session_id": None,
    "auth_mode": "login",
    "show_welcome_notice": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Helpers ────────────────────────────────────────────────────────────────────
def step_status(steps: dict, key: str) -> str:
    s = steps.get(key, "pending")
    if s == "active": return "dot-active"
    if s == "done":   return "dot-done"
    return "dot-pending"

def render_step_bar(label: str, key: str, icon: str, placeholder):
    css = step_status(st.session_state.pipeline_steps, key)
    placeholder.markdown(f"""
    <div class="status-bar">
        <div class="status-dot {css}"></div>
        <span>{icon} {label}</span>
    </div>""", unsafe_allow_html=True)

def render_chat(chat_history: list):
    if not chat_history:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">💬</div>
            <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
        </div>""", unsafe_allow_html=True)
        return
    chat_html = '<div class="chat-container">'
    for msg in chat_history:
        if msg["role"] == "user":
            chat_html += f'<div class="chat-msg" style="align-items:flex-end"><span class="chat-label user-label">You</span><div class="chat-bubble user-bubble">{msg["content"]}</div></div>'
        else:
            chat_html += f'<div class="chat-msg" style="align-items:flex-start"><span class="chat-label bot-label">🤖 Assistant</span><div class="chat-bubble bot-bubble">{msg["content"]}</div></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

# ─── Main App ────────────────────────────────────────────────────────────────────
def render_app():
    user = st.session_state.user

    # ── Welcome Notice — dismissible banner after login ──────────────────────
    if st.session_state.show_welcome_notice:
        col1, col2 = st.columns([11, 1])
        with col1:
            st.warning(
                "💡 **YouTube URL** is not supported on cloud deployment. "
                "Download your video from **[yt2mp3.ai](https://yt2mp3.ai/)** "
                "and upload it here as MP3/MP4."
            )
        with col2:
            if st.button("✕", key="dismiss_notice", type="secondary"):
                st.session_state.show_welcome_notice = False
                st.rerun()
        st.session_state.show_welcome_notice = False

    with st.sidebar:
        st.markdown('<div class="hero-title" style="font-size:1.6rem">🎬 AI Video<br>Assistant</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-sub">Video Intelligence</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem'>👤 {user['username']}</div>", unsafe_allow_html=True)
        st.markdown("---")

        st.markdown('<span class="badge badge-purple">Input</span>', unsafe_allow_html=True)

        col_url, col_file = st.columns(2)
        with col_url:
            if st.button("🔗 URL", use_container_width=True,
                         type="primary" if st.session_state.input_mode == "url" else "secondary"):
                st.session_state.input_mode = "url"
                st.rerun()
        with col_file:
            if st.button("📁 Local", use_container_width=True,
                         type="primary" if st.session_state.input_mode == "file" else "secondary"):
                st.session_state.input_mode = "file"
                st.rerun()

        source = None
        uploaded_file = None

        if st.session_state.input_mode == "url":
            source = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...")
        else:
            uploaded_file = st.file_uploader("Upload Media", type=["mp3", "mp4", "wav", "m4a", "ogg", "webm"])

        language = st.selectbox("Language", ["english", "telugu", "hindi", "kannada", "tamil"], index=0)
        run_btn = st.button("⚡  Analyse", use_container_width=True)

        st.markdown("---")
        st.markdown('<span class="badge badge-green">Pipeline Status</span>', unsafe_allow_html=True)

        step_placeholders = {}
        for step, icon, label in [
            ("audio",      "🔊", "Audio Processing"),
            ("transcript", "📝", "Transcription"),
            ("title",      "🏷️",  "Title Generation"),
            ("summary",    "📋", "Summarisation"),
            ("extract",    "🔍", "Extraction"),
            ("rag",        "🧠", "RAG Engine"),
        ]:
            ph = st.empty()
            step_placeholders[step] = (ph, icon, label)
            render_step_bar(label, step, icon, ph)

        # ── Past Sessions ─────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<span class="badge badge-cyan">Past Sessions</span>', unsafe_allow_html=True)

        past_sessions = get_user_sessions(user["id"])

        if not past_sessions:
            st.markdown("<div style='font-size:0.78rem;color:var(--text-muted);margin-top:0.5rem'>No past sessions yet.</div>", unsafe_allow_html=True)
        else:
            for s in past_sessions:
                date_str = s["created_at"][:10]
                col_s, col_del = st.columns([4, 1])
                with col_s:
                    label_text = f"📄 {s['title'][:22]}...\n{date_str}" if len(s['title']) > 22 else f"📄 {s['title']}\n{date_str}"
                    if st.button(label_text, key=f"load_{s['id']}", use_container_width=True, type="secondary"):
                        session_data = load_session(s["id"], user["id"])
                        if session_data:
                            rag_chain = load_rag_chain(session_data["collection_name"])
                            st.session_state.result = {
                                "title": session_data["title"],
                                "transcript": session_data["transcript"],
                                "summary": session_data["summary"],
                                "action_items": session_data["action_items"],
                                "key_decisions": session_data["key_decisions"],
                                "open_questions": session_data["open_questions"],
                                "rag_chain": rag_chain,
                                "session_id": session_data["id"],
                            }
                            st.session_state.chat_history = session_data["chat_history"]
                            st.session_state.active_session_id = session_data["id"]
                            st.session_state.pipeline_done = True
                            st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{s['id']}", type="secondary"):
                        delete_session(s["id"], user["id"])
                        if st.session_state.active_session_id == s["id"]:
                            st.session_state.result = None
                            st.session_state.chat_history = []
                            st.session_state.active_session_id = None
                        st.rerun()

        # ── Reset & Logout ────────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("➕ New Analysis", use_container_width=True, type="primary"):
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.pipeline_done = False
            st.session_state.pipeline_steps = {}
            st.session_state.active_session_id = None
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.user = None
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.pipeline_done = False
            st.session_state.pipeline_steps = {}
            st.session_state.active_session_id = None
            st.rerun()

    # ── Main Area ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with Videos</div>', unsafe_allow_html=True)
    st.markdown("---")

    if run_btn:
        if st.session_state.input_mode == "url" and not (source and source.strip()):
            st.error("Please enter a YouTube URL.")
        elif st.session_state.input_mode == "file" and uploaded_file is None:
            st.error("Please upload an audio/video file.")
        else:
            st.session_state.pipeline_done = False
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.pipeline_steps = {}
            st.session_state.active_session_id = None

            for step, (ph, icon, label) in step_placeholders.items():
                render_step_bar(label, step, icon, ph)

            progress_placeholder = st.empty()

            def update_step(key, state):
                st.session_state.pipeline_steps[key] = state
                ph, icon, label = step_placeholders[key]
                render_step_bar(label, key, icon, ph)

            try:
                with progress_placeholder.container():
                    st.info("⚙️ Pipeline running…")

                if st.session_state.input_mode == "file":
                    suffix = os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.read())
                        actual_source = tmp.name
                    source_label = uploaded_file.name
                else:
                    actual_source = source.strip()
                    source_label = source.strip()

                update_step("audio", "active")
                chunks = process_input(actual_source)
                update_step("audio", "done")

                update_step("transcript", "active")
                transcript = transcribe_all(chunks, language)
                update_step("transcript", "done")

                update_step("title", "active")
                title = generate_title(transcript)
                update_step("title", "done")

                update_step("summary", "active")
                summary = summarize(transcript)
                update_step("summary", "done")

                update_step("extract", "active")
                action_items = extract_action_items(transcript)
                decisions    = extract_key_decisions(transcript)
                questions    = extract_questions(transcript)
                update_step("extract", "done")

                update_step("rag", "active")
                session_id      = str(uuid.uuid4())[:8]
                collection_name = f"meeting_{session_id}"
                rag_chain       = build_rag_chain(transcript, collection_name)
                update_step("rag", "done")

                # Cleanup uploaded temp file immediately
                if st.session_state.input_mode == "file":
                    try: os.remove(actual_source)
                    except Exception: pass

                save_session(
                    session_id=session_id, user_id=user["id"], title=title,
                    source=source_label, language=language, transcript=transcript,
                    summary=summary, action_items=action_items, key_decisions=decisions,
                    open_questions=questions, collection_name=collection_name,
                )

                st.session_state.result = {
                    "title": title, "transcript": transcript, "summary": summary,
                    "action_items": action_items, "key_decisions": decisions,
                    "open_questions": questions, "rag_chain": rag_chain, "session_id": session_id,
                }
                st.session_state.active_session_id = session_id
                st.session_state.pipeline_done = True
                progress_placeholder.success("✅ Analysis complete!")
                time.sleep(0.5)
                progress_placeholder.empty()
                st.rerun()

            except Exception as e:
                for k in ["audio", "transcript", "title", "summary", "extract", "rag"]:
                    if st.session_state.pipeline_steps.get(k) == "active":
                        st.session_state.pipeline_steps[k] = "pending"
                        ph, icon, label = step_placeholders[k]
                        render_step_bar(label, k, icon, ph)
                progress_placeholder.error(f"❌ Error: {e}")

    if st.session_state.result:
        r = st.session_state.result

        st.markdown(f"""
        <div class="card">
            <div class="card-title">📌 Session Title</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:700;color:var(--text)">{r['title']}</div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns([3, 2], gap="medium")
        with col1:
            st.markdown(f'<div class="card"><div class="card-title">📋 Summary</div><div class="card-content">{r["summary"]}</div></div>', unsafe_allow_html=True)
        with col2:
            with st.expander("📝 Full Transcript", expanded=False):
                st.markdown(f'<div class="transcript-box">{r["transcript"]}</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            st.markdown(f'<div class="card"><div class="card-title">✅ Action Items</div><div class="card-content">{r["action_items"]}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="card"><div class="card-title">🔑 Key Decisions</div><div class="card-content">{r["key_decisions"]}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="card"><div class="card-title">❓ Open Questions</div><div class="card-content">{r["open_questions"]}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-size:1.2rem;font-weight:700;margin-bottom:1rem">💬 Chat with your Meeting</div>', unsafe_allow_html=True)

        render_chat(st.session_state.chat_history)

        chat_col1, chat_col2 = st.columns([5, 1], gap="small")
        with chat_col1:
            user_input = st.text_input("Your question", placeholder="What were the main decisions made?", label_visibility="collapsed", key="chat_input")
        with chat_col2:
            send_btn = st.button("Send →", use_container_width=True)

        if send_btn and user_input.strip():
            with st.spinner("Thinking…"):
                # FIX: pass chat history so RAG remembers conversation context
                answer = ask_question(r["rag_chain"], user_input.strip(), history=st.session_state.chat_history)
            st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            if st.session_state.active_session_id:
                update_chat_history(st.session_state.active_session_id, st.session_state.chat_history)
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat", type="secondary"):
                st.session_state.chat_history = []
                if st.session_state.active_session_id:
                    update_chat_history(st.session_state.active_session_id, [])
                st.rerun()
    else:
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5rem 2rem;text-align:center">
            <div style="font-size:4rem;margin-bottom:1rem">🎬</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:var(--text);margin-bottom:0.5rem">Ready to Analyse</div>
            <div style="color:var(--text-muted);font-size:0.85rem;max-width:380px;line-height:1.7">
                Choose YouTube URL or upload a local file, pick your language, and hit <strong>Analyse</strong> to get started.
            </div>
            <div style="margin-top:2rem;display:flex;gap:1rem;flex-wrap:wrap;justify-content:center">
                <span class="badge badge-purple">Transcription</span>
                <span class="badge badge-cyan">Summarisation</span>
                <span class="badge badge-green">RAG Chat</span>
            </div>
        </div>""", unsafe_allow_html=True)

# ─── Router ──────────────────────────────────────────────────────────────────────
if st.session_state.user is None:
    render_auth()
else:
    render_app()