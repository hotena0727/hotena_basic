import streamlit as st

st.set_page_config(page_title="한자 훈련", layout="centered")

with st.sidebar:
    if st.button("← 트레이닝 홈", use_container_width=True):
        st.switch_page("home.py")
st.sidebar.divider()

st.markdown("## 🈶 한자 훈련")
st.info("여기는 한자 훈련 페이지(준비중)입니다.\n\n원하시면 선우님 ‘한자쓰기 앱’ 코드를 그대로 붙여서 바로 연결해드릴게요.")
st.markdown("- 다음 단계 추천: **쓰기 캔버스 + 자기채점 + 오답/복습 루틴**")
