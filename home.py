# home.py
from __future__ import annotations
import streamlit as st

from word import render_word
# (아직 파일이 없으면 아래 2개는 일단 주석 처리해도 됩니다.)
# from kanji import render_kanji
# from kaiwa import render_kaiwa


# ✅ 사이드바 숨김 (원치 않는 UI 제거)
st.set_page_config(page_title="하테나일본어", layout="centered", initial_sidebar_state="collapsed")
st.markdown(
    """
<style>
section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
</style>
""",
    unsafe_allow_html=True,
)


def render_home():
    st.markdown("## は  하테나일본어")
    st.caption("원하는 훈련을 선택하세요.")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📘 단어 훈련", use_container_width=True):
            st.session_state.page = "word"
            st.rerun()

    with c2:
        if st.button("🈶 한자 훈련", use_container_width=True):
            st.session_state.page = "kanji"
            st.rerun()

    with c3:
        if st.button("💬 회화 훈련", use_container_width=True):
            st.session_state.page = "kaiwa"
            st.rerun()


# ✅ 라우터
ALLOWED = {"home", "word", "kanji", "kaiwa"}
if "page" not in st.session_state:
    st.session_state.page = "home"
if st.session_state.page not in ALLOWED:
    st.session_state.page = "home"

page = st.session_state.page

if page == "home":
    render_home()

elif page == "word":
    render_word()

elif page == "kanji":
    st.info("kanji.py의 render_kanji()를 연결하면 됩니다.")
    if st.button("← 홈으로", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
    # render_kanji()

elif page == "kaiwa":
    st.info("kaiwa.py의 render_kaiwa()를 연결하면 됩니다.")
    if st.button("← 홈으로", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
    # render_kaiwa()
