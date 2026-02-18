import streamlit as st

from ui_theme import apply_ui_theme
from ui_components import render_top_menu

import word
import kanji
import talk

st.set_page_config(page_title="Hatena Basic", layout="centered")
st.session_state["_page_config_set"] = True
apply_ui_theme()

st.session_state.setdefault("hub_view", "홈")
view = st.session_state["hub_view"]

render_top_menu(view)
st.markdown("---")

if view == "홈":
    st.subheader("홈")
    st.write("상단 메뉴로 이동하세요.")

elif view == "단어":
    st.subheader("단어 훈련")
    word.render_word()

elif view == "한자":
    st.subheader("한자 훈련")
    kanji.render_kanji()

elif view == "회화":
    st.subheader("회화 훈련")
    talk.render_talk()

elif view == "마이페이지":
    st.subheader("마이페이지")
    st.info("마이페이지는 다음 단계에서 붙입니다.")
