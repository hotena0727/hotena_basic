import streamlit as st

st.set_page_config(page_title="회화 훈련", layout="centered")

with st.sidebar:
    if st.button("← 트레이닝 홈", use_container_width=True):
        st.switch_page("home.py")
st.sidebar.divider()

st.markdown("## 🗣️ 회화 훈련")
st.info("여기는 회화 훈련 페이지(준비중)입니다.\n\n원하시면 ‘상황 선택 → 대화 턴 진행 → 피드백’ 구조로 바로 만들어드릴게요.")
st.markdown("- 다음 단계 추천: **상황 선택 + 데스/마스체 + 표현 카드 + 즉시 피드백**")
