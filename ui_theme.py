# ui_theme.py
import streamlit as st

# ============================================================
# ✅ V37 UI Theme (Phase 2) - Common CSS
# - Brand: Calm Blue + Minimal
# - Apply once per page
# ============================================================

THEME = {
    "PRIMARY": "#2F5FA7",
    "PRIMARY_L": "#3A7BD5",
    "BG_SOFT": "#F5F7FA",
    "TEXT": "#1C1C1C",
    "SUBTEXT": "#6B7280",
    "DANGER": "#D9534F",
    "BORDER": "rgba(0,0,0,0.06)",
    "SHADOW_SOFT": "0 4px 14px rgba(0,0,0,0.05)",
    "SHADOW_BTN": "0 2px 6px rgba(0,0,0,0.08)",
}

def apply_ui_theme():
    """
    Call this once per page (right after st.set_page_config()).
    """
    st.markdown(
        f"""
<style>
/* ============================================================
   ✅ Global layout
   ============================================================ */
:root {{
  --primary: {THEME["PRIMARY"]};
  --primaryL: {THEME["PRIMARY_L"]};
  --bgSoft: {THEME["BG_SOFT"]};
  --text: {THEME["TEXT"]};
  --subtext: {THEME["SUBTEXT"]};
  --danger: {THEME["DANGER"]};
  --border: {THEME["BORDER"]};
  --shadowSoft: {THEME["SHADOW_SOFT"]};
  --shadowBtn: {THEME["SHADOW_BTN"]};
}}

html, body, [class*="css"] {{
  color: var(--text);
}}

.block-container {{
  padding-top: 1.2rem !important;
  padding-bottom: 2.2rem !important;
  padding-left: 18px !important;
  padding-right: 18px !important;
  max-width: 720px !important;
}}

@media (min-width: 900px) {{
  .block-container {{
    padding-left: 20px !important;
    padding-right: 20px !important;
  }}
}}

/* ============================================================
   ✅ Hide sidebar (no sidebar UX)
   ============================================================ */
section[data-testid="stSidebar"] {{
  display: none !important;
}}
div[data-testid="collapsedControl"] {{
  display: none !important;
}}

/* ============================================================
   ✅ Header / title spacing normalization
   ============================================================ */
h1, h2, h3 {{
  letter-spacing: -0.2px;
}}
h1 {{
  font-size: 1.35rem !important;
  margin: 0.4rem 0 0.65rem 0 !important;
}}
h2 {{
  font-size: 1.1rem !important;
  margin: 0.8rem 0 0.5rem 0 !important;
}}
p {{
  color: var(--subtext);
}}

/* ============================================================
   ✅ Buttons (Streamlit default buttons)
   ============================================================ */
.stButton > button {{
  width: 100%;
  border-radius: 14px !important;
  padding: 12px 16px !important;
  font-weight: 600 !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadowBtn) !important;
  transition: transform 0.06s ease, filter 0.12s ease;
}}

.stButton > button:hover {{
  filter: brightness(1.05);
}}

.stButton > button:active {{
  transform: translateY(1px);
}}

/* ============================================================
   ✅ Cards (use .ht-card wrapper)
   ============================================================ */
.ht-card {{
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: var(--shadowSoft);
}}

.ht-card + .ht-card {{
  margin-top: 16px;
}}

.ht-card-title {{
  font-size: 1.02rem;
  font-weight: 800;
  color: var(--text);
  margin: 0 0 6px 0;
}}

.ht-card-sub {{
  font-size: 0.92rem;
  color: var(--subtext);
  margin: 0;
}}

/* ============================================================
   ✅ Badges
   ============================================================ */
.ht-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text);
}}

.ht-badge.pro {{
  border-color: rgba(58,123,213,0.35);
  color: var(--primaryL);
}}

.ht-badge.free {{
  color: var(--subtext);
}}

/* ============================================================
   ✅ Panels (talk/info boxes)
   ============================================================ */
.ht-panel {{
  background: var(--bgSoft);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 14px;
}}

.ht-divider {{
  height: 1px;
  background: rgba(0,0,0,0.06);
  margin: 14px 0;
}}

/* ============================================================
   ✅ Inputs
   ============================================================ */
div[data-baseweb="input"] > div {{
  border-radius: 14px !important;
}}
div[data-baseweb="textarea"] > div {{
  border-radius: 14px !important;
}}

/* ============================================================
   ✅ Reduce noisy default decorations
   ============================================================ */
div[data-testid="stToolbar"] {{
  visibility: hidden;
  height: 0px;
  position: fixed;
}}
footer {{
  visibility: hidden;
  height: 0px;
}}
</style>
        """,
        unsafe_allow_html=True,
    )
