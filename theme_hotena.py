from __future__ import annotations
import streamlit as st

def apply_theme():
    if st.session_state.get("_hotena_theme_applied"):
        return
    st.session_state["_hotena_theme_applied"] = True
    st.markdown(
        """<style>
:root{
  --hotena-navy:#1C2F5C;
  --hotena-navy-weak: rgba(28,47,92,.08);
  --hotena-border: rgba(49,51,63,.12);
  --hotena-radius: 18px;
  --hotena-btn-h: 48px;
}

div[data-testid="stButton"] > button, a[data-testid="stLinkButton"]{
  min-height: var(--hotena-btn-h) !important;
  border-radius: 999px !important;
  font-weight: 700 !important;
}

.block-container{ padding-top: 0.8rem !important; }

.hotena-card{
  border: 1px solid var(--hotena-border);
  border-radius: var(--hotena-radius);
  padding: 14px 14px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(0,0,0,.02);
}

.hotena-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--hotena-border);
  background: var(--hotena-navy-weak);
  color: var(--hotena-navy);
  font-weight: 800;
  font-size: 0.95rem;
}
</style>""",
        unsafe_allow_html=True
    )
