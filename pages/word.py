import streamlit as st

st.set_page_config(page_title="단어", layout="centered")

st.title("단어 페이지")
st.caption("여기에 단어 앱 코드를 붙이면 됩니다.")

if st.button("← 홈으로", use_container_width=True):
    st.switch_page("home.py")
