# home.py
import streamlit as st
from ui_theme import apply_ui_theme
from ui_components import render_top_menu, nav_to

import word
import kanji
import talk
import mypage

st.set_page_config(page_title="Hatena Basic", layout="centered")
apply_ui_theme()

st.session_state.setdefault("hub_view", "홈")
view = st.session_state["hub_view"]

render_top_menu(view)
st.markdown("---")

if view == "홈":
    st.header("홈")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("단어 훈련", type="primary"):
            nav_to("단어")
    with c2:
        if st.button("한자 훈련", type="secondary"):
            nav_to("한자")
    with c3:
        if st.button("회화 훈련", type="secondary"):
            nav_to("회화")
    st.caption("상단 메뉴로 언제든 이동할 수 있어요.")

elif view == "단어":
    st.header("단어 훈련")
    word.render_word()

elif view == "한자":
    st.header("한자 훈련")
    kanji.render_kanji()

elif view == "회화":
    st.header("회화 훈련")
    talk.render_talk()

elif view == "마이페이지":
    st.header("마이페이지")
    mypage.render_mypage()
