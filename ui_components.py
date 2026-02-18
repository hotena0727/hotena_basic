# ui_components.py
from __future__ import annotations
import streamlit as st

# hub_page codes
MENU = [
    ("home", "홈"),
    ("word", "단어"),
    ("kanji", "한자"),
    ("talk", "회화"),
    ("mypage", "마이페이지"),
]

def go(page: str):
    st.session_state["hub_page"] = page
    st.rerun()

def render_top_menu(active_page: str):
    # Top pill buttons (no sidebar)
    cols = st.columns(5, gap="small")
    for i, (code, label) in enumerate(MENU):
        btn_type = "primary" if str(active_page) == code else "secondary"
        with cols[i]:
            if st.button(label, type=btn_type, key=f"top_{code}"):
                go(code)
