# home.py
from __future__ import annotations
import streamlit as st

# ✅ 사이드바 숨김 + 심플 레이아웃
st.set_page_config(
    page_title="하테나일본어",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
</style>
""",
    unsafe_allow_html=True,
)

P_HOME  = "home"
P_WORD  = "word"
P_KANJI = "kanji"
P_KAIWA = "kaiwa"

ALLOWED = {P_HOME, P_WORD, P_KANJI, P_KAIWA}

if "page" not in st.session_state:
    st.session_state.page = P_HOME
if st.session_state.page not in ALLOWED:
    st.session_state.page = P_HOME

def render_home():
    st.markdown("## は  하테나일본어")
    st.caption("원하는 훈련을 선택하세요.")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📘 단어 훈련", use_container_width=True):
            st.session_state.page = P_WORD
            st.rerun()

    with c2:
        if st.button("🈶 한자 훈련", use_container_width=True):
            st.session_state.page = P_KANJI
            st.rerun()

    with c3:
        if st.button("💬 회화 훈련", use_container_width=True):
            st.session_state.page = P_KAIWA
            st.rerun()

page = st.session_state.page

if page == P_HOME:
    render_home()

elif page == P_WORD:
    # ✅ word.py의 Streamlit 앱을 여기에서 실행
    import word
    word.render_word()

elif page == P_KANJI:
    st.markdown("## 🈶 한자 훈련")
    st.info("다음 단계: kanji.py를 만들고 render_kanji()를 연결하면 됩니다.")
    if st.button("← 홈", use_container_width=True):
        st.session_state.page = P_HOME
        st.rerun()

elif page == P_KAIWA:
    st.markdown("## 💬 회화 훈련")
    st.info("다음 단계: kaiwa.py를 만들고 render_kaiwa()를 연결하면 됩니다.")
    if st.button("← 홈", use_container_width=True):
        st.session_state.page = P_HOME
        st.rerun()
