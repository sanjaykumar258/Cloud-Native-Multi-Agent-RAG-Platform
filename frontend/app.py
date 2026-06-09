"""
app.py — Cloud-Native Multi-Agent RAG Platform: Streamlit Dashboard
Premium redesign with animated gradient background, glassmorphism panels,
particle-style decorative elements, and polished typography.
"""

from __future__ import annotations

import os
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import logging
import time
from pathlib import Path
from backend.brain.utils import format_duration
import streamlit as st

st.set_page_config(
    page_title="Multi-Agent RAG Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ════════════════════════════════════════════
   ROOT & ANIMATED GRADIENT BACKGROUND
   ════════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #020817;
    background-image:
        radial-gradient(ellipse 80% 60% at 50% -10%, rgba(99,102,241,0.25) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 90% 80%, rgba(139,92,246,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 10% 90%, rgba(59,130,246,0.15) 0%, transparent 60%);
    min-height: 100vh;
    color: #e2e8f0;
}

/* Animated top border glow */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6, #3b82f6, #6366f1);
    background-size: 200% 100%;
    animation: shimmer 4s linear infinite;
    z-index: 9999;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Subtle animated noise pattern */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
}

/* ════════════════════════════════════════════
   SIDEBAR — GLASS PANEL
   ════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.85) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-right: 1px solid rgba(99,102,241,0.2) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.4);
}
[data-testid="stSidebar"] .block-container {
    padding-top: 1.8rem;
}

/* ── Sidebar brand ── */
.brand-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 0.25rem;
}
.brand-icon {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
    box-shadow: 0 4px 16px rgba(99,102,241,0.4);
    flex-shrink: 0;
}
.brand-title {
    font-size: 1.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.3px;
    line-height: 1.2;
}
.brand-sub {
    font-size: 0.7rem;
    color: #64748b;
    font-weight: 400;
    margin-top: 1px;
}

/* ── Section labels ── */
.sidebar-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #4f46e5;
    margin: 1.4rem 0 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 6px;
}
.sidebar-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(99,102,241,0.3), transparent);
}

/* ── Status badge ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 100px;
    width: 100%;
    margin-bottom: 0.5rem;
}
.badge-green  { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-yellow { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.badge-red    { background: rgba(239,68,68,0.12);  color: #f87171; border: 1px solid rgba(239,68,68,0.3);  }
.badge-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    animation: pulse-dot 2s infinite;
    flex-shrink: 0;
}
.badge-dot-green  { background: #34d399; box-shadow: 0 0 6px #34d399; }
.badge-dot-yellow { background: #fbbf24; box-shadow: 0 0 6px #fbbf24; }
.badge-dot-red    { background: #f87171; }
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.6; transform: scale(0.85); }
}

/* ── Source pill ── */
.source-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(99,102,241,0.06);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.75rem;
    color: #94a3b8;
    margin-bottom: 5px;
    font-family: 'JetBrains Mono', monospace;
}
.source-pill-icon { color: #6366f1; }

/* ── Stat card ── */
.stat-card {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
}
.stat-num { font-size: 1.4rem; font-weight: 800; color: #a5b4fc; line-height: 1; }
.stat-lbl { font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px; margin-top: 3px; }

/* ════════════════════════════════════════════
   MAIN AREA
   ════════════════════════════════════════════ */
.block-container { padding-top: 2rem !important; position: relative; z-index: 1; }

/* ── Page title ── */
.page-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 50%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
    margin-bottom: 0.15rem;
    line-height: 1.1;
}
.page-sub {
    color: #475569;
    font-size: 0.88rem;
    margin-bottom: 1.5rem;
}

/* ── Welcome hero ── */
.hero-wrap {
    text-align: center;
    padding: 5rem 2rem 4rem;
}
.hero-glow {
    display: inline-block;
    font-size: 5.5rem;
    filter: drop-shadow(0 0 32px rgba(99,102,241,0.5));
    animation: float 4s ease-in-out infinite;
    margin-bottom: 1.5rem;
    line-height: 1;
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%       { transform: translateY(-10px); }
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #e2e8f0 0%, #a5b4fc 60%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
    margin-bottom: 1rem;
}
.hero-desc {
    font-size: 1.05rem;
    color: #64748b;
    max-width: 480px;
    margin: 0 auto 2.5rem;
    line-height: 1.65;
}

/* ── Feature cards row ── */
.features-row {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 1rem;
}
.feat-card {
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    min-width: 148px;
    max-width: 180px;
    flex: 1;
    backdrop-filter: blur(12px);
    transition: border-color 0.2s, transform 0.2s;
}
.feat-card:hover {
    border-color: rgba(99,102,241,0.45);
    transform: translateY(-3px);
}
.feat-icon { font-size: 1.9rem; margin-bottom: 0.6rem; }
.feat-title { font-weight: 700; color: #e2e8f0; font-size: 0.88rem; margin-bottom: 3px; }
.feat-desc  { font-size: 0.73rem; color: #64748b; }

/* ── Instruction steps ── */
.steps-row {
    display: flex;
    gap: 0;
    justify-content: center;
    margin: 2.5rem auto;
    max-width: 680px;
    position: relative;
}
.step {
    flex: 1;
    text-align: center;
    padding: 0 0.5rem;
    position: relative;
}
.step-num {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.85rem; color: white;
    margin: 0 auto 0.6rem;
    box-shadow: 0 4px 14px rgba(99,102,241,0.4);
}
.step-label { font-size: 0.75rem; color: #94a3b8; font-weight: 500; }
.step-connector {
    position: absolute;
    top: 18px; left: 50%; right: -50%;
    height: 1px;
    background: linear-gradient(90deg, rgba(99,102,241,0.4), rgba(99,102,241,0.15));
    z-index: 0;
}

/* ════════════════════════════════════════════
   CHAT BUBBLES
   ════════════════════════════════════════════ */
.chat-wrap { display: flex; flex-direction: column; gap: 1.2rem; padding-bottom: 1rem; }

.user-bubble {
    align-self: stretch;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: #fff;
    padding: 1.1rem 1.6rem;
    border-radius: 18px;
    margin: 0.8rem 0;
    box-shadow: 0 4px 24px rgba(79,70,229,0.3);
    font-size: 0.95rem;
    line-height: 1.62;
    word-wrap: break-word;
    border: 1px solid rgba(255,255,255,0.12);
}

.assistant-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    max-width: 88%;
}
.assistant-avatar {
    width: 34px; height: 34px;
    border-radius: 10px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
    box-shadow: 0 2px 10px rgba(99,102,241,0.35);
}
.assistant-bubble {
    background: rgba(15,23,42,0.75);
    border: 1px solid rgba(99,102,241,0.18);
    border-radius: 4px 20px 20px 20px;
    padding: 0.9rem 1.2rem;
    color: #e2e8f0;
    font-size: 0.92rem;
    line-height: 1.7;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    word-wrap: break-word;
    flex: 1;
}

/* ════════════════════════════════════════════
   CITATION CARDS
   ════════════════════════════════════════════ */
.cit-card {
    background: rgba(10,15,30,0.7);
    border: 1px solid rgba(99,102,241,0.15);
    border-left: 3px solid #6366f1;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    margin: 0.45rem 0;
    backdrop-filter: blur(8px);
}
.cit-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #818cf8;
    margin-bottom: 4px;
}
.cit-meta {
    font-size: 0.72rem;
    color: #475569;
    margin-bottom: 6px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}
.cit-meta span {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.15);
    padding: 1px 7px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
}
.latency-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    color: #4f46e5;
    background: rgba(79,70,229,0.08);
    border: 1px solid rgba(79,70,229,0.15);
    padding: 2px 8px;
    border-radius: 6px;
    margin-top: 8px;
    font-family: 'JetBrains Mono', monospace;
}
.cit-snippet {
    font-size: 0.77rem;
    color: #64748b;
    font-style: italic;
    line-height: 1.5;
    border-top: 1px solid rgba(99,102,241,0.1);
    padding-top: 6px;
    margin-top: 4px;
}

/* ════════════════════════════════════════════
   BUTTONS & INPUTS
   ════════════════════════════════════════════ */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 1.2rem !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.3) !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(99,102,241,0.5) !important;
    transform: translateY(-1px) !important;
    opacity: 0.95 !important;
}
.stButton > button:active { transform: translateY(0) !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(15,23,42,0.8) !important;
    border: 1px solid rgba(99,102,241,0.25) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.88rem !important;
    transition: border-color 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(99,102,241,0.6) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
}

/* ── Divider ── */
.stDivider { border-color: rgba(99,102,241,0.12) !important; }

/* ── Progress bar ── */
.stProgress > div > div > div { background: linear-gradient(90deg, #6366f1, #8b5cf6) !important; }

/* ── Chat input ── */
/* Remove fixed positioning to let Streamlit handle sidebar responsive layout */
.stChatInput {
    background: #020617 !important;
    backdrop-filter: blur(24px) !important;
    z-index: 1000 !important;
    border-top: 1px solid rgba(79,70,229,0.15) !important;
    padding: 1.2rem 2% !important; /* Reduced horizontal padding for responsiveness */
}
.stChatInput > div {
    background: rgba(15,23,42,0.8) !important;
    border: 1px solid rgba(79,70,229,0.3) !important;
    border-radius: 12px !important;
    padding: 4px 8px !important;
}
.stChatInput > div:focus-within {
    border-color: rgba(99,102,241,0.6) !important;
    box-shadow: 0 0 0 4px rgba(99,102,241,0.1) !important;
}

/* ── Thinking Bar (Reference Matching) ── */
.thinking-bar {
    background: #0b0f1a;
    border: 1px solid rgba(79,70,229,0.2);
    border-radius: 8px;
    padding: 10px 18px;
    margin: 12px 0;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.88rem;
    color: #a5b4fc;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    width: 100%;
}
.loader-mini {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(165,180,252,0.2);
    border-top: 2px solid #a5b4fc;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Add padding to the bottom of the main container */
.block-container { padding-bottom: 160px !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(15,23,42,0.6) !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 10px !important;
    font-size: 0.82rem !important;
    color: #818cf8 !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: rgba(10,15,30,0.4) !important;
    border: 1px solid rgba(99,102,241,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }

/* ── Hide Streamlit footer and main menu (safe selectors) ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #6366f1 !important; }

/* ════════════════════════════════════════════
   PYTHON ENGINE — CODE & RESULT BUBBLES
   ════════════════════════════════════════════ */
.code-bubble {
    background: rgba(8,12,25,0.85);
    border: 1px solid rgba(99,102,241,0.3);
    border-left: 3px solid #6366f1;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #a5b4fc;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 320px;
    overflow-y: auto;
}
.code-bubble-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #6366f1;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.result-bubble {
    background: rgba(6,25,15,0.75);
    border: 1px solid rgba(16,185,129,0.3);
    border-left: 3px solid #10b981;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #34d399;
    white-space: pre-wrap;
}
.result-bubble-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #10b981;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.python-badge-on  { background:rgba(16,185,129,0.1); color:#34d399; border:1px solid rgba(16,185,129,0.3); }
.python-badge-off { background:rgba(239,68,68,0.1);  color:#f87171; border:1px solid rgba(239,68,68,0.3);  }
</style>
""", unsafe_allow_html=True)




logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


# ── Session state ─────────────────────────────────────────────────────────────
def _init_state():
    import uuid
    for k, v in {
        "messages": [],
        "indexed": False,
        "folder_path": "",
        "brain_graph": None,
        "vectorstore": None,
        "provider": "none",
        "chunk_count": 0,
        "file_count": 0,
        "ollama_model": os.getenv("OLLAMA_MODEL", "llama-3.1-8b-instant"),
        "embed_model": os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2"),
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Environment Sync ─────────────────────────────────────────────────────────
# Read the current UI state to ensure LLM providers are aware of keys immediately
if "ollama_model_input" in st.session_state:
    os.environ["OLLAMA_MODEL"] = st.session_state["ollama_model_input"]
if "embed_model_input" in st.session_state:
    os.environ["EMBED_MODEL"] = st.session_state["embed_model_input"]



# ════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════
with st.sidebar:
    # Brand
    st.markdown("""
    <div class="brand-wrap">
        <div class="brand-icon">🧠</div>
        <div>
            <div class="brand-title">Cloud Brain</div>
            <div class="brand-sub">Multi-Agent RAG Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Status badge
    st.markdown('<div class="sidebar-label">⚡ System</div>', unsafe_allow_html=True)
    from backend.llm_provider import get_active_provider
    # Pass prefer_groq=True so it picks it up if key is present
    provider = get_active_provider(prefer_groq=True)
    if provider == "groq":
        st.markdown('<div class="badge badge-yellow"><span class="badge-dot badge-dot-yellow"></span>Groq Cloud — Active (Fast)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge badge-red"><span class="badge-dot badge-dot-red"></span>No LLM Connected</div>', unsafe_allow_html=True)


    # Stats bar
    if st.session_state.get("indexed"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{st.session_state.get("file_count",0)}</div><div class="stat-lbl">Files</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-num">{st.session_state.get("chunk_count",0)}</div><div class="stat-lbl">Chunks</div></div>', unsafe_allow_html=True)
        
        if st.session_state.get("ingest_time"):
            st.markdown(f'<div class="stat-card" style="margin-top:0.5rem;"><div class="stat-num">{format_duration(st.session_state["ingest_time"])}</div><div class="stat-lbl">Time to Index</div></div>', unsafe_allow_html=True)

    # Folder picker
    st.markdown('<div class="sidebar-label">📁 Document Folder</div>', unsafe_allow_html=True)

    st.text_input("Path to folder", key="folder_path", label_visibility="collapsed", placeholder="/path/to/documents")

    def _open_folder_dialog():
        """Open native folder picker and store result in session state."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            selected = filedialog.askdirectory(title="Select Document Folder")
            root.destroy()
            if selected:
                st.session_state["folder_path"] = selected
            return True
        except Exception as e:
            st.error("⚠️ Folder browsing is only supported when running locally. Please type the path manually in the box above.")
            return False

    if st.button("📂 Browse Folder (Local Only)", use_container_width=True, key="browse_folder"):
        if _open_folder_dialog():
            st.rerun()

    _current_path = st.session_state.get("folder_path", "")
    if _current_path:
        st.markdown(f'<div class="source-pill"><span class="source-pill-icon">📁</span>{_current_path}</div>', unsafe_allow_html=True)
    else:
        st.caption("No folder selected")


    # Settings
    st.markdown('<div class="sidebar-label">⚙️ Model Settings</div>', unsafe_allow_html=True)
    embed_model   = st.text_input("Embed Model",  value=st.session_state["embed_model"], key="embed_model_input")
    enable_vision = st.checkbox("🔍 Enable Vision (Slows indexing)", value=False, help="Extract detailed descriptions for images inside PDFs. Uses Vision LLM.", key="v_toggle")
    enable_tables = st.checkbox("📊 Enable Tables (Slows indexing)", value=False, help="Extract tables from PDFs using Camelot/OCR.", key="t_toggle")
    enable_graph  = st.checkbox("🕸 Build Knowledge Graph (Slow)", value=False, help="Extract entities and relations using LLM during indexing.", key="g_toggle")
    
    st.session_state["embed_model"] = embed_model




    ingest_btn = st.button("⚡ Ingest", use_container_width=True)
    clear_btn  = st.button("🗑 Clear", use_container_width=True)

    # ── Python Engine status ──────────────────────────────────────────────────
    st.markdown('<div class="sidebar-label">🐍 Python Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="badge badge-yellow">'
        '<span class="badge-dot badge-dot-yellow"></span>'
        'Native Python Execution</div>',
        unsafe_allow_html=True,
    )

    # Indexed sources
    if st.session_state.get("indexed"):
        vs = st.session_state.get("vectorstore")
        if vs:
            st.markdown('<div class="sidebar-label">📚 Indexed Files</div>', unsafe_allow_html=True)
            for s in vs.list_sources():
                st.markdown(f'<div class="source-pill"><span class="source-pill-icon">📄</span>{s}</div>', unsafe_allow_html=True)

    st.divider()
    
    st.markdown('<div style="font-size:0.68rem;color:#334155;text-align:center;">Cloud-Powered • Lightning Fast • Scalable</div>', unsafe_allow_html=True)


# ── Apply env overrides ───────────────────────────────────────────────────────
if embed_model:  os.environ["EMBED_MODEL"]  = embed_model

if clear_btn:
    st.session_state["messages"] = []
    st.rerun()


# ════════════════════════════════════════
#  INGEST
# ════════════════════════════════════════
if ingest_btn:
    folder_path = st.session_state.get("folder_path", "").strip()
    if not folder_path:
        st.sidebar.error("⚠️ Enter or browse to a folder path.")
    elif not Path(folder_path).exists():
        st.sidebar.error(f"⚠️ Not found: `{folder_path}`")
    else:
        st.session_state.update({"indexed": False, "brain_graph": None})
        with st.sidebar:
            st.markdown('<div class="sidebar-label">⏳ Indexing</div>', unsafe_allow_html=True)
            prog_bar   = st.progress(0.0)
            status_box = st.empty()

        try:
            from backend.brain.ingest import ingest_folder
            from backend.brain.vectorstore import VectorStore

            vs = VectorStore()
            fc = 0
            start_t = time.time()
            for event in ingest_folder(folder_path, enable_vision=enable_vision, enable_tables=enable_tables, enable_graph=enable_graph):
                prog_bar.progress(min(event["progress"], 1.0))
                status_box.caption(event["message"])
                if event["type"] == "file": fc += 1
                if event["type"] == "error": st.sidebar.warning(event["message"])

            elapsed_t = time.time() - start_t
            prog_bar.progress(1.0)
            status_box.markdown("✅ **Indexing complete!**")

            from backend.llm_provider import get_active_provider

            st.session_state.update({
                "vectorstore": vs,
                "indexed": True,
                "provider": get_active_provider(),
                "file_count": len(vs.list_sources()),
                "chunk_count": vs.count(),
                "ingest_time": elapsed_t,
            })
            st.rerun()

        except Exception as exc:
            st.sidebar.error(f"Ingestion failed: {exc}")
            logger.exception("Ingestion error")


# ════════════════════════════════════════
#  MESSAGE RENDERING
# ════════════════════════════════════════
def _render_message(msg: dict):
    """Consistent message rendering for both history and live response."""
    role = msg["role"]
    content = msg.get("content", "")
    intent = msg.get("intent", "chat")
    sources = msg.get("sources", [])
    generated_code = msg.get("generated_code", "")
    elapsed = msg.get("elapsed", None)

    with st.chat_message(role, avatar="🧠" if role=="assistant" else None):
        if role == "user":
            st.markdown(f'<div class="chat-wrap"><div class="user-bubble">{content}</div></div>', unsafe_allow_html=True)
        else:
            time_tag = f'<div class="latency-badge">⚡ {format_duration(elapsed)}</div>' if elapsed is not None else ""
            if intent == "code":
                 st.markdown(
                    f'<div class="chat-wrap">'
                    f'<div class="assistant-bubble">'
                    f'<div class="code-bubble-label">Generated Script</div>'
                    f'<div class="code-bubble">{generated_code}</div>'
                    f'<div class="result-bubble-label">✅ Result</div>'
                    f'<div class="result-bubble">{content}</div>'
                    f'{time_tag}'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            elif intent == "report":
                st.markdown(
                    f'<div class="chat-wrap">'
                    f'<div class="assistant-bubble">{content}{time_tag}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(f'''
                <div class="chat-wrap">
                    <div class="assistant-bubble">{content}{time_tag}</div>
                </div>''', unsafe_allow_html=True)

            if sources:
                with st.expander(f"📚 {len(sources)} source(s) used"):
                    _render_citations(sources)

def _render_citations(sources: list[dict]):
    for i, src in enumerate(sources, 1):
        meta    = src.get("metadata", {})
        source  = meta.get("source", "Unknown")
        page    = meta.get("page_number", "")
        heading = meta.get("heading", "")
        etype   = meta.get("element_type", "")
        snippet = src.get("text", "")[:220].replace("\n", " ")

        meta_tags = ""
        if page:    meta_tags += f'<span>📄 Page {page}</span>'
        if heading: meta_tags += f'<span>🔖 {heading[:40]}</span>'
        if etype:   meta_tags += f'<span>🏷 {etype}</span>'

        st.markdown(f"""
        <div class="cit-card">
            <div class="cit-header">#{i} &nbsp;{source}</div>
            <div class="cit-meta">{meta_tags}</div>
            <div class="cit-snippet">"{snippet}…"</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════
#  MAIN AREA
# ════════════════════════════════════════
if not st.session_state.get("indexed"):
    # ── WELCOME HERO ─────────
    st.markdown("""
<div style="text-align:center;padding-top:3.5rem;">
    <div style="font-size:5.5rem;filter:drop-shadow(0 0 32px rgba(99,102,241,0.55));
        display:inline-block;line-height:1;margin-bottom:1.4rem;">🌐</div>
    <div style="font-size:2.8rem;font-weight:800;letter-spacing:-1px;margin-bottom:0.9rem;
        background:linear-gradient(135deg,#e2e8f0 0%,#a5b4fc 60%,#8b5cf6 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
        Multi-Agent RAG Platform
    </div>
    <div style="font-size:1.05rem;color:#64748b;max-width:480px;margin:0 auto 2.5rem;line-height:1.65;">
        Drop in any folder of PDFs, Markdown, or text files.<br>
        Ask questions and get answers with <strong style="color:#a5b4fc;">exact citations</strong> — powered by Cloud LLMs.
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    for col, num, label in [(sc1,"1","Enter folder path"),(sc2,"2","Click Ingest"),(sc3,"3","Ask anything")]:
        with col:
            st.markdown(f"""
<div style="text-align:center;padding:0 0.5rem;">
    <div style="width:38px;height:38px;border-radius:50%;
        background:linear-gradient(135deg,#6366f1,#8b5cf6);
        display:flex;align-items:center;justify-content:center;
        font-weight:800;font-size:0.9rem;color:white;
        margin:0 auto 0.55rem;
        box-shadow:0 4px 14px rgba(99,102,241,0.45);">{num}</div>
    <div style="font-size:0.78rem;color:#94a3b8;font-weight:500;">{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    features = [
        (fc1, "📄", "PDF Tables",      "Understands complex tables and multi-page docs"),
        (fc2, "✂️", "Semantic Split",  "Chunks on meaning, not character count"),
        (fc3, "🔁", "Self-Correction", "Dual-agent loop guards hallucinations"),
        (fc4, "📍", "Exact Citations", "File, Page, Section per answer"),
        (fc5, "☁️", "Cloud Native",      "Groq API + ChromaDB"),
    ]
    for col, icon, title, desc in features:
        with col:
            st.markdown(f"""
<div style="background:rgba(15,23,42,0.65);border:1px solid rgba(99,102,241,0.2);
    border-radius:16px;padding:1.2rem 1rem;text-align:center;height:100%;">
    <div style="font-size:1.75rem;margin-bottom:0.5rem;">{icon}</div>
    <div style="font-weight:700;color:#e2e8f0;font-size:0.83rem;margin-bottom:4px;">{title}</div>
    <div style="font-size:0.71rem;color:#64748b;line-height:1.4;">{desc}</div>
</div>""", unsafe_allow_html=True)

else:
    tab_chat, tab_graph = st.tabs(["💬 Chat", "🕸 Knowledge Graph"])

    with tab_graph:
        st.markdown("<div class='page-sub'>Explore entities and relationships extracted from your documents</div>", unsafe_allow_html=True)
        try:
            from backend.brain.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            html = kg.to_pyvis_html()
            import streamlit.components.v1 as components
            components.html(html, height=620)
        except Exception as e:
            st.error(f"Failed to load graph: {e}")

    with tab_chat:
        st.markdown("""
        <div style="margin-bottom:1.5rem">
            <div class="page-title">☁️ Cloud Brain</div>
            <div class="page-sub">Ask anything about your indexed documents</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Conversation Container ──
        # This container holds history and the active reasoning placeholder.
        # It ensures they appear ABOVE the chat input.
        chat_container = st.container()

        with chat_container:
            for msg in st.session_state["messages"]:
                _render_message(msg)

        # ── Chat Input ──
        # Always appears at the bottom of the tab/area.
        if prompt := st.chat_input("Ask something about your documents…"):
            st.session_state["messages"].append({"role": "user", "content": prompt, "sources": []})
            with chat_container:
                _render_message(st.session_state["messages"][-1])

            vs = st.session_state.get("vectorstore")
            if vs is None:
                st.error("Brain not initialised — please ingest a folder first.")
            else:
                with chat_container:
                    ans_placeholder = st.empty()
                    # Custom thinking bar placeholder
                    status_placeholder = st.empty()
                    
                try:
                    from backend.llm_provider import get_llm
                    from backend.agents.graph import BrainGraph
                    
                    if st.session_state.get("brain_graph") is None:
                        llm = get_llm()
                        st.session_state["brain_graph"] = BrainGraph(vectorstore=vs, llm=llm)
                    
                    graph = st.session_state["brain_graph"]
                    
                    status_placeholder.markdown(
                        f'<div class="thinking-bar"><div class="loader-mini"></div><div style="margin-left:8px">Thinking...</div></div>',
                        unsafe_allow_html=True
                    )
                    
                    thread_id = st.session_state.get("thread_id", "default_user")
                    result = {}
                    start_ask = time.time()
                    for node_name, state in graph.stream_ask(prompt, thread_id=thread_id):
                        if node_name == "route_intent":
                            intent = state.get("intent", "chat")
                            status_placeholder.markdown(
                                f'<div class="thinking-bar"><div class="loader-mini"></div>🔍 Intent: {intent.upper()}</div>',
                                unsafe_allow_html=True
                            )
                        elif node_name == "code_exec":
                            status_placeholder.markdown(
                                f'<div class="thinking-bar"><div class="loader-mini"></div>🐍 Executing Python sandbox logic...</div>',
                                unsafe_allow_html=True
                            )
                            if state.get("generated_code"):
                                ans_placeholder.markdown(
                                    f'<div class="chat-wrap"><div class="assistant-row">'
                                    f'<div class="assistant-avatar">🐍</div>'
                                    f'<div class="assistant-bubble">'
                                    f'<div class="code-bubble-label">Generated Script</div>'
                                    f'<div class="code-bubble">{state["generated_code"]}</div>'
                                    f'</div></div></div>',
                                    unsafe_allow_html=True
                                )
                        elif node_name == "reporting_node":
                            status_placeholder.markdown(
                                f'<div class="thinking-bar"><div class="thinking-icon">📊</div>Generating workspace report...</div>',
                                unsafe_allow_html=True
                            )
                        result = state
                    elapsed_ask = time.time() - start_ask

                    full_answer     = result.get("answer", "")
                    sources         = result.get("sources", [])
                    intent          = result.get("intent", "chat")
                    generated_code  = result.get("generated_code", "")
                    
                    if intent == "code":
                        stdout = result.get("code_result", {}).get("stdout", "")
                        if stdout: full_answer = stdout

                    status_placeholder.empty()
                    
                    msg_data = {
                        "role": "assistant",
                        "content": full_answer,
                        "sources": sources,
                        "intent": intent,
                        "generated_code": generated_code,
                        "elapsed": elapsed_ask
                    }
                    
                    ans_placeholder.empty()
                    with ans_placeholder:
                        _render_message(msg_data)
                    
                    st.session_state["messages"].append(msg_data)

                except Exception as exc:
                    err = f"Error during reasoning: {exc}"
                    status_placeholder.empty()
                    msg_data = {"role": "assistant", "content": err, "intent": "chat"}
                    with ans_placeholder:
                        _render_message(msg_data)
                    st.session_state["messages"].append(msg_data)
                    logger.exception("Agent error")
