# ui_theme.py
import streamlit as st

THEME = {
    "PRIMARY": "#FF4B4B",   # Streamlit red-ish
    "TEXT": "#111827",
    "SUBTEXT": "#6B7280",
    "BORDER": "rgba(0,0,0,0.10)",
    "BG": "#FFFFFF",
    "BG_SOFT": "#F7F7FB",
    "SHADOW": "0 6px 16px rgba(0,0,0,0.06)",
}

def apply_ui_theme():
    # Apply once
    if st.session_state.get("_hatena_theme_done"):
        return
    st.session_state["_hatena_theme_done"] = True

    css = f"""
<style>
:root {{
  --primary: {THEME["PRIMARY"]};
  --text: {THEME["TEXT"]};
  --subtext: {THEME["SUBTEXT"]};
  --border: {THEME["BORDER"]};
  --bg: {THEME["BG"]};
  --bgSoft: {THEME["BG_SOFT"]};
  --shadow: {THEME["SHADOW"]};
}}

/* Layout */
.block-container{{max-width:760px !important; padding-top: 0.9rem !important; padding-left: 18px !important; padding-right: 18px !important;}}
section[data-testid="stSidebar"], div[data-testid="collapsedControl"]{{display:none !important;}}
div[data-testid="stToolbar"], footer{{visibility:hidden; height:0;}}

/* Buttons: make sure SECONDARY text is visible */
.stButton > button{{
  border-radius: 14px !important;
  padding: 10px 14px !important;
  font-weight: 800 !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow) !important;
}}

/* Streamlit sets kind="primary"/"secondary" on buttons in newer versions */
.stButton > button[kind="primary"]{{
  background: var(--primary) !important;
  color: #fff !important;
  border-color: rgba(0,0,0,0.08) !important;
}}
.stButton > button[kind="secondary"]{{
  background: #fff !important;
  color: var(--text) !important;   /* ✅ 핵심: 글자색 강제 */
}}

/* Top menu row spacing */
.ht-topmenu {{margin-top: 2px; margin-bottom: 8px;}}
.ht-topmenu .stButton > button{{padding: 9px 10px !important; border-radius: 999px !important; font-size: 0.92rem !important;}}

/* Minor typography */
h1,h2,h3,p,span,div{{color: var(--text);}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
