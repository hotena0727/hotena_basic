# theme_hotena.py
from __future__ import annotations
import streamlit as st

# ------------------------------------------------------------
# ✅ Hotena Unified Theme
# - Keep it light-weight and compatible with sub-app CSS.
# - Apply once per run; safe to call multiple times.
# ------------------------------------------------------------

def apply_hotena_theme() -> None:
    st.markdown(
        """
<style>
/* =========================
   Hotena Theme Variables
   ========================= */
:root{
  --hotena-bg: #0B1220;
  --hotena-panel: rgba(255,255,255,0.06);
  --hotena-panel-strong: rgba(255,255,255,0.09);
  --hotena-border: rgba(255,255,255,0.12);
  --hotena-text: rgba(255,255,255,0.92);
  --hotena-subtext: rgba(255,255,255,0.72);
  --hotena-accent: #2F81F7;      /* blue */
  --hotena-accent-2: #22C55E;    /* green */
  --hotena-danger: #EF4444;
  --hotena-radius: 14px;
  --hotena-radius-sm: 10px;
}

/* =========================
   App background + layout
   ========================= */
html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 700px at 10% 0%, rgba(47,129,247,0.22), transparent 60%),
              radial-gradient(900px 600px at 90% 10%, rgba(34,197,94,0.14), transparent 55%),
              var(--hotena-bg) !important;
  color: var(--hotena-text) !important;
}

[data-testid="stHeader"]{
  background: transparent !important;
}

[data-testid="stSidebar"]{
  display: none; /* unified app uses no sidebar */
}

.block-container{
  max-width: 860px;
  padding-top: 1.2rem;
  padding-bottom: 2.2rem;
}

/* =========================
   Typography
   ========================= */
h1,h2,h3,h4,h5,h6{
  color: var(--hotena-text) !important;
  letter-spacing: -0.2px;
}
p, li, label, div{
  color: var(--hotena-text);
}
small, .hotena-subtext{
  color: var(--hotena-subtext) !important;
}

/* =========================
   Cards / panels
   ========================= */
.hotena-card{
  background: var(--hotena-panel);
  border: 1px solid var(--hotena-border);
  border-radius: var(--hotena-radius);
  padding: 14px 14px;
}
.hotena-card-strong{
  background: var(--hotena-panel-strong);
  border: 1px solid var(--hotena-border);
  border-radius: var(--hotena-radius);
  padding: 14px 14px;
}

/* =========================
   Buttons
   ========================= */
.stButton > button{
  border-radius: 12px !important;
  border: 1px solid var(--hotena-border) !important;
  background: rgba(255,255,255,0.06) !important;
  color: var(--hotena-text) !important;
  padding: 0.62rem 0.85rem !important;
  font-weight: 700 !important;
}
.stButton > button:hover{
  border-color: rgba(47,129,247,0.55) !important;
  background: rgba(47,129,247,0.18) !important;
}
.stButton > button:focus{
  box-shadow: 0 0 0 3px rgba(47,129,247,0.25) !important;
}

/* Primary button pattern (use via st.button(..., type="primary") on newer Streamlit) */
button[kind="primary"]{
  background: linear-gradient(180deg, rgba(47,129,247,0.92), rgba(47,129,247,0.72)) !important;
  border: 1px solid rgba(47,129,247,0.55) !important;
  color: #FFFFFF !important;
}
button[kind="primary"]:hover{
  background: linear-gradient(180deg, rgba(47,129,247,0.98), rgba(47,129,247,0.78)) !important;
}

/* =========================
   Inputs
   ========================= */
input, textarea{
  border-radius: 12px !important;
  border: 1px solid var(--hotena-border) !important;
  background: rgba(255,255,255,0.06) !important;
  color: var(--hotena-text) !important;
}

[data-baseweb="select"] > div{
  border-radius: 12px !important;
  border: 1px solid var(--hotena-border) !important;
  background: rgba(255,255,255,0.06) !important;
}

[data-testid="stRadio"] div[role="radiogroup"]{
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--hotena-border);
  border-radius: 12px;
  padding: 10px 12px;
}

/* =========================
   Alerts
   ========================= */
[data-testid="stAlert"]{
  border-radius: 12px !important;
  border: 1px solid var(--hotena-border) !important;
}

/* Hide Streamlit footer */
footer{ visibility: hidden; }
</style>
        """,
        unsafe_allow_html=True,
    )

def hotena_header(title: str, subtitle: str | None = None) -> None:
    apply_hotena_theme()
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<div class='hotena-subtext'>{subtitle}</div>", unsafe_allow_html=True)
