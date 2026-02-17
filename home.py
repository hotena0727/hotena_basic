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
section[data-testid="stSidebar"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ✅ 홈: 버튼 3개만
st.markdown("## は  하테나일본어")
st.caption("원하는 훈련을 선택하세요.")

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("📘 단어 훈련", use_container_width=True):
        st.session_state["page"] = "word"   # ← 단어 퀴즈 라우트 키
        st.rerun()

with c2:
    if st.button("🈶 한자 훈련", use_container_width=True):
        st.session_state["page"] = "kanji"  # ← 한자 퀴즈 라우트 키
        st.rerun()

with c3:
    if st.button("💬 회화 훈련", use_container_width=True):
        st.session_state["page"] = "kaiwa"  # ← 회화 훈련 라우트 키
        st.rerun()
