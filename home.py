from __future__ import annotations
import streamlit as st
from ui import top_nav
from auth import logout

def render_home():
    top_nav()

    user = st.session_state.get("user", {})
    st.markdown('<div class="hotena-title">Hotena Training</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hotena-sub">로그인: {user.get("email","")} | 플랜: {st.session_state.get("user_plan","free").upper()}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([3,1])
    with c2:
        if st.button("로그아웃", use_container_width=True):
            logout()

    st.divider()

    # ✅ 첫 홈화면: 버튼 3개만
    b1, b2, b3 = st.columns(3)
    if b1.button("단어 훈련", use_container_width=True):
        st.session_state["page"] = "words"
        st.rerun()
    if b2.button("한자 훈련", use_container_width=True):
        st.session_state["page"] = "kanji"
        st.rerun()
    if b3.button("회화 훈련", use_container_width=True):
        st.session_state["page"] = "talk"
        st.rerun()
