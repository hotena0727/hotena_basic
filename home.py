import streamlit as st

st.set_page_config(
    page_title="왕초보탈출 하테나일본어",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 사이드바 숨기기 (깔끔한 홈 화면용)
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("왕초보탈출 하테나일본어")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📘 단어", use_container_width=True):
        st.switch_page("pages/word.py")

with col2:
    if st.button("🈶 한자", use_container_width=True):
        st.switch_page("pages/kanji.py")

with col3:
    if st.button("💬 회화 훈련", use_container_width=True):
        st.switch_page("pages/conversation.py")
