# ui_theme.py
import streamlit as st

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
    if st.session_state.get("_hatena_ui_theme_applied"):
        return
    st.session_state["_hatena_ui_theme_applied"] = True

    st.markdown(
        f"""
<style>
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

html, body, [class*="css"] {{ color: var(--text); }}

.block-container {{
  padding-top: 1.15rem !important;
  padding-bottom: 2.2rem !important;
  padding-left: 18px !important;
  padding-right: 18px !important;
  max-width: 720px !important;
}}

section[data-testid="stSidebar"], div[data-testid="collapsedControl"] {{
  display:none !important;
}}

h1 {{ font-size: 1.35rem !important; margin: 0.4rem 0 0.65rem 0 !important; }}
h2 {{ font-size: 1.10rem !important; margin: 0.8rem 0 0.5rem 0 !important; }}
p {{ color: var(--subtext); }}

/* Buttons */
.stButton > button {{
  width: 100%;
  border-radius: 14px !important;
  padding: 12px 16px !important;
  font-weight: 700 !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadowBtn) !important;
  transition: transform 0.06s ease, filter 0.12s ease;
}}
.stButton > button:hover {{ filter: brightness(1.05); }}
.stButton > button:active {{ transform: translateY(1px); }}

.stButton > button[kind="primary"]{{
  background: var(--primary) !important;
  color: #fff !important;
  border: 1px solid rgba(47,95,167,.45) !important;
}}
.stButton > button[kind="secondary"]{{
  background: #fff !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
}}

/* Cards */
.ht-card {{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:18px 18px;
  box-shadow: var(--shadowSoft);
}}
.ht-card + .ht-card {{ margin-top: 14px; }}
.ht-card-title {{ font-size: 1.02rem; font-weight: 900; margin: 0 0 6px 0; color: var(--text);}}
.ht-card-sub {{ font-size: 0.92rem; margin: 0; color: var(--subtext);}}
.ht-panel {{
  background: var(--bgSoft);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 14px;
}}
.ht-divider {{ height:1px; background: rgba(0,0,0,0.06); margin: 14px 0; }}

/* Badge */
.ht-badge {{
  display:inline-flex; align-items:center; gap:6px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 800;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text);
}}
.ht-badge.pro {{ border-color: rgba(58,123,213,0.35); color: var(--primaryL);}}
.ht-badge.free {{ color: var(--subtext);}}

/* Header */
.ht-header {{
  display:flex; align-items:center; justify-content:space-between;
  gap:12px; padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:#fff;
  box-shadow: var(--shadowSoft);
  margin: 2px 0 12px 0;
}}
.ht-header-title {{ font-weight: 900; text-align:center; flex:1; }}
.ht-header-left {{ min-width: 80px; }}
.ht-header-right {{ min-width: 140px; display:flex; justify-content:flex-end; }}

/* Home card buttons */
.ht-cardbtn-anchor{{display:block;height:0;overflow:hidden}}
#ht_card_word + div[data-testid="stButton"] > button,
#ht_card_kanji + div[data-testid="stButton"] > button,
#ht_card_talk + div[data-testid="stButton"] > button{{
  text-align:left !important;
  white-space:normal !important;
  height:auto !important;
  padding:18px 18px !important;
  border-radius:18px !important;
  border:1px solid var(--border) !important;
  background:#fff !important;
  box-shadow: var(--shadowSoft) !important;
  font-weight:900 !important;
  line-height:1.2 !important;
}}

/* MyPage KPIs */
.ht-mypage-wrap{{display:flex;flex-direction:column;gap:14px;margin-top:6px}}
.ht-kpi-row{{display:flex;gap:10px}}
.ht-kpi{{
  flex:1;background:#fff;border:1px solid var(--border);
  border-radius:16px;padding:14px 14px;box-shadow: var(--shadowSoft);
}}
.ht-kpi-label{{font-size:0.82rem;color:var(--subtext);font-weight:800;margin-bottom:6px}}
.ht-kpi-value{{font-size:1.25rem;color:var(--text);font-weight:900;line-height:1.1}}
.ht-kpi-sub{{font-size:0.86rem;color:var(--subtext);margin-top:6px}}
.ht-section-title{{font-weight:900;color:var(--text);margin:2px 0 2px 0}}
.ht-cta{{
  background: rgba(47,95,167,.06);
  border: 1px solid rgba(47,95,167,.18);
  border-radius:18px;
  padding:16px 16px;
}}
.ht-cta-title{{font-weight:900;color:var(--text);margin:0 0 6px 0}}
.ht-cta-sub{{color:var(--subtext);margin:0}}

/* 7-day mini heatmap */
.ht-heatmap{{
  display:grid; grid-template-columns: repeat(7, 1fr);
  gap:8px; margin-top:8px;
}}
.ht-heatcell{{
  border-radius:12px; border:1px solid var(--border);
  padding:10px 10px; background:#fff; box-shadow: var(--shadowSoft);
}}
.ht-heat-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.ht-heat-day{{font-weight:900;color:var(--text);font-size:0.9rem}}
.ht-heat-date{{color:var(--subtext);font-size:0.78rem;font-weight:800}}
.ht-heat-bar{{height:8px;border-radius:999px;background:rgba(47,95,167,.10);overflow:hidden}}
.ht-heat-bar > span{{display:block;height:100%;border-radius:999px;background:rgba(47,95,167,.55);}}
.ht-heat-num{{margin-top:8px;color:var(--subtext);font-size:0.82rem;font-weight:800}}
@media (max-width: 520px){{
  .ht-heatmap{{grid-template-columns: repeat(4, 1fr);}}
}}

/* Hide Streamlit chrome */
div[data-testid="stToolbar"] {{ visibility:hidden; height:0; position:fixed; }}
footer {{ visibility:hidden; height:0; }}

/* ============================================================
   ✅ MyPage dashboard extras: goal + recent list
   ============================================================ */
.ht-goal{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:16px 16px;
  box-shadow: var(--shadowSoft);
}
.ht-goal-top{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.ht-goal-title{font-weight:900;color:var(--text);margin:0}
.ht-goal-sub{color:var(--subtext);font-weight:800;font-size:0.86rem;margin:0}
.ht-recent{
  background:#fff;
  border:1px solid var(--border);
  border-radius:18px;
  padding:14px 14px;
  box-shadow: var(--shadowSoft);
}
.ht-recent-item{
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 10px;border-radius:14px;
  border:1px solid rgba(0,0,0,0.04);
  background: rgba(0,0,0,0.015);
}
.ht-recent-item + .ht-recent-item{margin-top:8px}
.ht-recent-left{display:flex;flex-direction:column;gap:2px}
.ht-recent-mode{font-weight:900;color:var(--text);font-size:0.92rem}
.ht-recent-time{color:var(--subtext);font-weight:800;font-size:0.78rem}
.ht-recent-score{font-weight:900;color:var(--primaryL)}

</style>
""",
        unsafe_allow_html=True,
    )
