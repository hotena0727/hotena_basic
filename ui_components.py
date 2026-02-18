# ui_components.py
import streamlit as st

# ============================================================
# ✅ V37 UI Components — single source of truth
# - Common header with Home / MyPage navigation
# - Session-state routing (no query params)
# ============================================================

def nav_to(view: str):
    st.session_state["hub_view"] = view
    st.rerun()

def _badge_html(user_plan: str):
    plan = "PRO" if str(user_plan).lower() == "pro" else "FREE"
    cls = "pro" if plan == "PRO" else "free"
    return f"<span class='ht-badge {cls}'>{plan}</span>"

def render_header(
    title: str,
    user_plan: str = "free",
    show_home: bool = True,
    show_mypage: bool = True,
):
    """
    Standard header row:
      [← 홈]   [Title]   [마이페이지] [FREE/PRO badge]
    """
    colL, colC, colR = st.columns([1.15, 2.2, 1.65], vertical_alignment="center")

    with colL:
        if show_home:
            if st.button("← 홈", key=f"hdr_home_{title}"):
                nav_to("홈")

    with colC:
        st.markdown(
            f"<div style='text-align:center;font-weight:900;'>{title}</div>",
            unsafe_allow_html=True,
        )

    with colR:
        r1, r2 = st.columns([1.05, 1.0], vertical_alignment="center")
        with r1:
            if show_mypage:
                if st.button("마이페이지", key=f"hdr_mypage_{title}"):
                    nav_to("마이페이지")
        with r2:
            st.markdown(
                f"<div style='text-align:right;'>{_badge_html(user_plan)}</div>",
                unsafe_allow_html=True,
            )
