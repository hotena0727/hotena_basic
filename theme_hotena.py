# theme_hotena.py
from __future__ import annotations

import streamlit as st

# ============================================================
# ✅ Hotena Theme (single source of truth)
# - Button height / radius / card styles / badge styles
# - Mobile touch targets
# - Works across all pages (home/words/kanji/talk/mypage)
# ============================================================

HOTENA_BLUE = "#1C2F5C"   # deep navy (brand)
HOTENA_BLUE_SOFT = "#2A3F77"
HOTENA_BG = "#F6F8FC"
HOTENA_TEXT = "#0B1220"
HOTENA_MUTED = "rgba(11,18,32,.65)"

def apply_hotena_theme(force: bool = False):
    """
    Inject global CSS once per session.
    Call this at the start of each page render (safe to call multiple times).
    """
    if not force and st.session_state.get("_hotena_theme_applied"):
        return

    st.markdown(
        f"""
<style>
:root {{
  --hotena-blue: {HOTENA_BLUE};
  --hotena-blue-soft: {HOTENA_BLUE_SOFT};
  --hotena-bg: {HOTENA_BG};
  --hotena-text: {HOTENA_TEXT};
  --hotena-muted: {HOTENA_MUTED};

  --hotena-radius: 18px;
  --hotena-radius-sm: 14px;
  --hotena-btn-h: 48px;
  --hotena-shadow: 0 8px 24px rgba(0,0,0,.06);
  --hotena-border: 1px solid rgba(0,0,0,.08);
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--hotena-bg) !important;
  color: var(--hotena-text) !important;
}}

header[data-testid="stHeader"] {{
  height: 3rem !important;
}}
/* reduce top padding so content sits higher (mobile friendly) */
div[data-testid="stAppViewContainer"] .block-container {{
  padding-top: 1.8rem !important;
  padding-bottom: 5.0rem !important; /* room for floating menu */
  max-width: 720px !important;
}}

@media (max-width: 640px) {{
  div[data-testid="stAppViewContainer"] .block-container {{
    padding-top: 1.4rem !important;
    padding-left: 0.9rem !important;
    padding-right: 0.9rem !important;
    padding-bottom: 5.6rem !important;
  }}
}}

/* ---- Buttons: unify height/radius/tap target ---- */
button[kind="primary"], button[kind="secondary"], .stButton > button {{
  min-height: var(--hotena-btn-h) !important;
  border-radius: var(--hotena-radius-sm) !important;
  font-weight: 700 !important;
}}

/* Make link_button look consistent */
a[data-testid="stLinkButton"], a[data-testid="stLinkButton"] > div {{
  border-radius: var(--hotena-radius-sm) !important;
}}
a[data-testid="stLinkButton"] {{
  min-height: var(--hotena-btn-h) !important;
}}

/* ---- Inputs: unify radius ---- */
input, textarea, .stTextInput input, .stTextArea textarea {{
  border-radius: var(--hotena-radius-sm) !important;
}}

/* ---- Card helper ---- */
.hotena-card {{
  border: var(--hotena-border);
  border-radius: var(--hotena-radius);
  box-shadow: var(--hotena-shadow);
  background: rgba(255,255,255,.82);
  backdrop-filter: blur(6px);
  padding: 14px 14px;
}}

.hotena-card.tight {{
  padding: 10px 12px;
}}

.hotena-title {{
  font-size: 20px;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0 0 6px 0;
}}

.hotena-sub {{
  font-size: 13px;
  color: var(--hotena-muted);
  margin: 0;
}}

/* ---- Badges / Pills ---- */
.hotena-pill {{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,.10);
  background: rgba(255,255,255,.9);
  font-weight: 800;
  font-size: 12px;
}}
.hotena-pill.pro {{
  border-color: rgba(28,47,92,.25);
  background: rgba(28,47,92,.10);
  color: var(--hotena-blue);
}}
.hotena-pill.free {{
  background: rgba(0,0,0,.04);
  color: rgba(0,0,0,.68);
}}

/* ---- Bubble UI (talk) ---- */
.hotena-bubble {{
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,.08);
  background: rgba(255,255,255,.92);
  box-shadow: 0 6px 18px rgba(0,0,0,.05);
}}
.hotena-bubble.me {{
  margin-left:auto;
  background: rgba(28,47,92,.10);
  border-color: rgba(28,47,92,.18);
}}
.hotena-bubble.answer {{
  background: rgba(42,63,119,.12);
  border-color: rgba(42,63,119,.22);
}}
.hotena-bubble .label {{
  font-size: 11px;
  opacity: .7;
  margin-bottom: 4px;
}}
.hotena-bubble .text {{
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
}}

/* ---- Make expanders feel tighter ---- */
details {{
  border-radius: var(--hotena-radius) !important;
  border: var(--hotena-border) !important;
  background: rgba(255,255,255,.78) !important;
}}
summary {{
  padding: 10px 12px !important;
  font-weight: 800 !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )
    st.session_state["_hotena_theme_applied"] = True

def pill(text: str, kind: str = "free"):
    """kind: 'free' | 'pro' | 'neutral'"""
    k = kind if kind in ("free","pro") else ""
    st.markdown(f'<span class="hotena-pill {k}">{text}</span>', unsafe_allow_html=True)

def card_open(tight: bool = False):
    cls = "hotena-card tight" if tight else "hotena-card"
    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)

def card_close():
    st.markdown("</div>", unsafe_allow_html=True)
