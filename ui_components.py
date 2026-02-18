# ui_components.py
import streamlit as st

VIEWS = ["홈", "단어", "한자", "회화", "마이페이지"]

def nav_to(view: str):
    st.session_state["hub_view"] = view
    st.rerun()

def render_top_menu(active: str):
    st.markdown('<div class="ht-topmenu">', unsafe_allow_html=True)
    cols = st.columns(5, gap="small")
    for i, v in enumerate(VIEWS):
        btn_type = "primary" if v == active else "secondary"
        with cols[i]:
            if st.button(v, type=btn_type, key=f"nav_{v}"):
                nav_to(v)
    st.markdown("</div>", unsafe_allow_html=True)
