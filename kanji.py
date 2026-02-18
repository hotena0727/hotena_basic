import streamlit as st
from ui_theme import apply_ui_theme

st.set_page_config(page_title="한자 훈련", layout="centered")
apply_ui_theme()

colL, colC, colR = st.columns([1.1,2.2,1.1], vertical_alignment="center")
with colL:
    if st.button("← 홈", key="back_home_한자_훈련"):
        st.session_state["hub_view"] = "홈"
        try:
            st.query_params["view"] = "홈"
        except Exception:
            pass
        st.rerun()
with colC:
    st.markdown("<div style='text-align:center;font-weight:900;'>한자 훈련</div>", unsafe_allow_html=True)
with colR:
    st.markdown("<div></div>", unsafe_allow_html=True)

st.markdown("<div class='ht-panel'>준비 중입니다.</div>", unsafe_allow_html=True)
