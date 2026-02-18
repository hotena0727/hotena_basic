# ui_theme.py
from __future__ import annotations
import streamlit as st

def apply_ui_theme():
    if st.session_state.get("_hatena_theme_done"):
        return
    st.session_state["_hatena_theme_done"] = True

    st.markdown(
        """
<style>
:root{
  --primary: #FF4B4B;
  --text: #111827;
  --subtext:#6B7280;
  --border: rgba(0,0,0,0.08);
  --shadowSoft: 0 8px 20px rgba(0,0,0,0.06);
  --shadowBtn: 0 3px 10px rgba(0,0,0,0.06);
  --bgSoft: #F7F7FB;
}

/* Layout */
.block-container{max-width: 760px !important; padding-top: 0.9rem !important; padding-left: 18px !important; padding-right: 18px !important;}
section[data-testid="stSidebar"], div[data-testid="collapsedControl"]{display:none !important;}
div[data-testid="stToolbar"], footer{visibility:hidden; height:0;}

/* Buttons - ensure secondary text visible */
.stButton > button{
  width:100%;
  border-radius: 999px !important;
  padding: 9px 10px !important;
  font-weight: 900 !important;
  border:1px solid var(--border) !important;
  box-shadow: var(--shadowBtn) !important;
}
.stButton > button[kind="primary"]{
  background: var(--primary) !important;
  color:#fff !important;
}
.stButton > button[kind="secondary"]{
  background:#fff !important;
  color: var(--text) !important;
}

/* Cards */
.ht-card{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:16px 16px;
  box-shadow: var(--shadowSoft);
}
.ht-card + .ht-card{ margin-top: 12px; }
.ht-card-title{ font-size:1.02rem; font-weight:900; margin:0 0 6px 0; color:var(--text); }
.ht-card-sub{ font-size:0.92rem; margin:0; color:var(--subtext); }

.ht-divider{ height:1px; background: rgba(0,0,0,0.06); margin: 14px 0; }
.ht-section-title{ font-weight:900; color: var(--text); margin: 0 0 8px 0; }

/* Badge */
.ht-badge{
  display:inline-flex; align-items:center;
  padding:6px 10px;
  border-radius:999px;
  font-size:0.82rem;
  font-weight:900;
  border:1px solid var(--border);
  background:#fff;
  color: var(--text);
}
.ht-badge.pro{ border-color: rgba(255,75,75,0.35); color: var(--primary); }
.ht-badge.free{ color: var(--subtext); }

</style>
""",
        unsafe_allow_html=True,
    )
