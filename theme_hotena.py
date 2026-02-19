# theme_hotena.py
from __future__ import annotations
import streamlit as st

def apply_hotena_theme():
    """Apply global Hotena theme styles once per session."""
    if st.session_state.get("_hotena_theme_applied"):
        return
    st.session_state["_hotena_theme_applied"] = True

    st.markdown(
        """
<style>
:root{
  --hotena-navy:#1C2F5C;
  --hotena-navy2:#223B73;
  --hotena-bg:#F6F8FC;
  --hotena-card:#FFFFFF;
  --hotena-border: rgba(0,0,0,.08);
  --hotena-radius:18px;
  --hotena-btn-h:48px;
}

/* Background + base spacing */
html, body, [data-testid="stAppViewContainer"]{
  background: var(--hotena-bg) !important;
}

/* Remove excessive top padding; keep safe space for Streamlit header */
section.main > div{
  padding-top: 0.6rem !important;
}

/* Cards */
.hotena-card{
  border:1px solid var(--hotena-border);
  border-radius: var(--hotena-radius);
  background: var(--hotena-card);
  padding: 14px 14px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

/* Buttons */
div.stButton > button, a[data-testid="stLinkButton"]{
  min-height: var(--hotena-btn-h) !important;
  border-radius: 14px !important;
  font-weight: 700 !important;
}

/* Pill badges */
.hotena-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border-radius: 999px;
  border:1px solid var(--hotena-border);
  background: rgba(255,255,255,.85);
  font-size: 13px;
  font-weight: 700;
}

/* Touch targets on mobile */
@media (max-width: 520px){
  div.stButton > button, a[data-testid="stLinkButton"]{
    min-height: 50px !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )
