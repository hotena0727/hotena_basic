from __future__ import annotations
import streamlit as st

def apply_hotena_theme():
    # Safe: inject once per session
    if st.session_state.get("_hotena_theme_applied"):
        return
    st.session_state["_hotena_theme_applied"] = True

    st.markdown(
        """
<style>
:root{
  --hotena-primary:#1C2F5C;
  --hotena-bg:#F7F9FC;
  --hotena-card:#FFFFFF;
  --hotena-border: rgba(0,0,0,.08);
  --hotena-shadow: 0 8px 24px rgba(16,24,40,.06);
  --hotena-radius: 18px;
  --hotena-btn-h: 48px;
}
html, body { background: var(--hotena-bg) !important; }
.block-container{ padding-top: 1.0rem !important; padding-bottom: 2.0rem !important; }
@media (max-width: 768px){
  .block-container{ padding-left: 1.0rem !important; padding-right: 1.0rem !important; padding-top: .7rem !important; }
}
/* Buttons */
.stButton > button, .stDownloadButton > button, a[data-testid="stLinkButton"]{
  min-height: var(--hotena-btn-h) !important;
  border-radius: 14px !important;
  font-weight: 700 !important;
}
.stButton > button{ border: 1px solid var(--hotena-border) !important; }
/* Cards helper */
.hotena-card{
  background: var(--hotena-card);
  border: 1px solid var(--hotena-border);
  border-radius: var(--hotena-radius);
  box-shadow: var(--hotena-shadow);
  padding: 14px 14px;
}
.hotena-pill{
  display:inline-flex; align-items:center; gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--hotena-border);
  background: rgba(255,255,255,.85);
  font-weight: 800;
}
.hotena-pill.pro{ background: rgba(255, 233, 233, .85); }
.hotena-pill.free{ background: rgba(233, 245, 255, .85); }
.hotena-bubble{
  max-width: 92%;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid var(--hotena-border);
  background: rgba(255,255,255,.92);
  box-shadow: 0 6px 18px rgba(16,24,40,.05);
  line-height: 1.55;
}
.hotena-bubble.me{ margin-left:auto; background: rgba(233,245,255,.92); border-color: rgba(28,47,92,.18); }
.hotena-bubble.answer{ background: rgba(28,47,92,.06); border-color: rgba(28,47,92,.20); }
.hotena-subtle{ opacity:.75; font-size: 13px; }
</style>
""",
        unsafe_allow_html=True
    )
