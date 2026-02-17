import streamlit as st

st.set_page_config(page_title="회화 훈련", layout="centered")

st.title("회화 훈련 페이지")
st.caption("여기에 회화 훈련 코드를 붙이면 됩니다.")

if st.button("← 홈으로", use_container_width=True):
    st.switch_page("home.py")
