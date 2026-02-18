# ui_shared.py
from __future__ import annotations

import streamlit as st

# ------------------------------------------------------------
# ✅ Global UI tokens + styles (minimal, fast)
# ------------------------------------------------------------
def inject_global_styles():
    if st.session_state.get("_ui_styles_injected"):
        return
    st.session_state["_ui_styles_injected"] = True

    st.markdown(
        """
<style>
/* ===== Tokens ===== */
:root{
  --h-bg:#ffffff;
  --h-surface:#ffffff;
  --h-border: rgba(15, 23, 42, 0.10);
  --h-text: #0f172a;     /* slate-900 */
  --h-muted:#475569;     /* slate-600 */
  --h-brand:#0ea5e9;     /* sky-500 */
  --h-brand-weak: rgba(14,165,233,.10);
  --h-success:#16a34a;   /* green-600 */
  --h-danger:#ef4444;    /* red-500 */
  --h-radius: 14px;
  --h-pad: 14px;
  --h-gap: 10px;
}

/* ===== Page ===== */
.block-container{
  padding-top: 1.1rem !important;
  padding-bottom: 2rem !important;
  max-width: 980px !important;
}
html, body, [class*="css"]{
  color: var(--h-text);
}

/* ===== Sticky Top Nav Wrapper ===== */
.h-topnav{
  position: sticky;
  top: 0;
  z-index: 999;
  background: var(--h-bg);
  border-bottom: 1px solid var(--h-border);
  padding: 8px 0 10px 0;
  margin: -8px 0 14px 0;
}

/* Make radio look like tabs */
.h-topnav [data-testid="stRadio"] > div{
  gap: 6px;
}
.h-topnav label{
  margin-right: 6px !important;
}
.h-topnav [data-testid="stRadio"] label{
  background: transparent;
  border-radius: 999px;
  padding: 6px 10px;
  border: 1px solid transparent;
}
.h-topnav [data-testid="stRadio"] input:checked + div{
  background: var(--h-brand-weak);
  border: 1px solid rgba(14,165,233,.35);
}

/* ===== Plan badge ===== */
.h-plan{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  border: 1px solid var(--h-border);
  color: var(--h-text);
  background: #fff;
  white-space: nowrap;
}
.h-plan.pro{
  border-color: rgba(14,165,233,.35);
  background: var(--h-brand-weak);
}

/* ===== Cards ===== */
.h-card{
  background: var(--h-surface);
  border: 1px solid var(--h-border);
  border-radius: var(--h-radius);
  padding: var(--h-pad);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}
.h-card + .h-card{ margin-top: 10px; }

/* ===== Buttons (global) ===== */
[data-testid="stButton"] button{
  border-radius: 999px !important;
  font-weight: 800 !important;
  padding: 0.55rem 0.95rem !important;
  border: 1px solid var(--h-border) !important;
}
[data-testid="stButton"] button:hover{
  border-color: rgba(14,165,233,.35) !important;
}

/* ===== Spacing normalization ===== */
div[data-testid="stVerticalBlock"] > div{
  gap: var(--h-gap);
}
</style>
        """,
        unsafe_allow_html=True,
    )

def _plan_label() -> str:
    plan = (st.session_state.get("user_plan") or "free").lower()
    return "PRO" if plan == "pro" else "FREE"

def render_top_nav():
    """Sticky top nav: 홈 | 단어 | 한자 | 회화 | 마이페이지 + plan badge (right)."""
    inject_global_styles()

    # Map hub_page -> label and reverse
    page_to_label = {
        "home": "홈",
        "word": "단어",
        "kanji": "한자",
        "talk": "회화",
        "mypage": "마이페이지",
    }
    label_to_page = {v: k for k, v in page_to_label.items()}

    current_page = st.session_state.get("hub_page", "home")
    default_label = page_to_label.get(current_page, "홈")

    options = ["홈", "단어", "한자", "회화", "마이페이지"]

    st.markdown('<div class="h-topnav">', unsafe_allow_html=True)
    left, right = st.columns([0.86, 0.14], vertical_alignment="center")

    with left:
        view = st.radio(
            label="",
            options=options,
            index=options.index(default_label) if default_label in options else 0,
            horizontal=True,
            key="hub_topnav",
            label_visibility="collapsed",
        )

    with right:
        plan = _plan_label()
        cls = "h-plan pro" if plan == "PRO" else "h-plan"
        st.markdown(f'<div style="text-align:right;"><span class="{cls}">{plan}</span></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Navigate if changed
    target_page = label_to_page.get(view, "home")
    if target_page != current_page:
        st.session_state["_hub_nav_token"] = st.session_state.get("_hub_nav_token") or "1"
        st.session_state["hub_page"] = target_page
        st.rerun()
