# ui_components.py
import streamlit as st

VIEWS = ["홈", "단어", "한자", "회화", "마이페이지"]

def nav_to(view: str):
    st.session_state["hub_view"] = view
    st.rerun()

def render_top_menu(active: str):
    cols = st.columns(5, gap="small")
    for i, v in enumerate(VIEWS):
        t = "primary" if v == active else "secondary"
        with cols[i]:
            if st.button(v, type=t, key=f"nav_{v}"):
                nav_to(v)
