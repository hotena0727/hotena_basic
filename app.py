from __future__ import annotations
import streamlit as st

from auth import restore_login, login_ui
from ui import inject_theme_once

st.set_page_config(page_title="Hotena", layout="centered")

# session defaults
st.session_state.setdefault("page", "home")
st.session_state.setdefault("user", None)
st.session_state.setdefault("user_plan", "free")

inject_theme_once()
restore_login()

# 로그인 안 되어 있으면 로그인 화면만
if not st.session_state.get("user"):
    login_ui()
    st.stop()

# 라우팅
page = st.session_state.get("page", "home")

if page == "home":
    from home import render_home
    render_home()
elif page == "words":
    from words import render_words
    render_words()
elif page == "kanji":
    from kanji import render_kanji
    render_kanji()
elif page == "talk":
    from talk import render_talk
    render_talk()
else:
    st.session_state["page"] = "home"
    st.rerun()
