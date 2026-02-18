# home.py
import streamlit as st
from ui_theme import apply_ui_theme
from ui_components import render_top_menu, nav_to

import word
import kanji
import talk

st.set_page_config(page_title="Hatena Basic", layout="centered")
apply_ui_theme()

st.session_state.setdefault("hub_view", "홈")
view = st.session_state["hub_view"]

render_top_menu(view)
st.markdown("---")

if view == "홈":
    st.subheader("홈")
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

elif view == "단어":
    st.subheader("단어 훈련")
    if hasattr(word, "render_word"):
        word.render_word()
    else:
        st.error("word.py에 render_word()가 없습니다.")

elif view == "한자":
    st.subheader("한자 훈련")
    if hasattr(kanji, "render_kanji"):
        kanji.render_kanji()
    else:
        st.error("kanji.py에 render_kanji()가 없습니다.")

elif view == "회화":
    st.subheader("회화 훈련")
    if hasattr(talk, "render_talk"):
        talk.render_talk()
    else:
        st.info("talk.py는 다음 단계에서 정리합니다.")

elif view == "마이페이지":
    st.subheader("마이페이지")
    st.info("마이페이지는 다음 단계에서 붙입니다.")
