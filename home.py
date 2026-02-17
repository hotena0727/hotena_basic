import streamlit as st

st.set_page_config(page_title="하테나 트레이닝 홈", layout="centered")

st.markdown("## 🏠 하테나 트레이닝 홈")
st.caption("원하는 훈련을 선택하세요.")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### 📚 단어 훈련")
    st.write("단어/뜻/발음 퀴즈")
    if st.button("단어 훈련 시작", use_container_width=True, key="go_words"):
        st.switch_page("pages/1_단어훈련.py")

with c2:
    st.markdown("### 🈶 한자 훈련")
    st.write("쓰기/자기채점")
    if st.button("한자 훈련 시작", use_container_width=True, key="go_kanji"):
        st.switch_page("pages/2_한자훈련.py")

with c3:
    st.markdown("### 🗣️ 회화 훈련")
    st.write("롤플레이/패턴 연습")
    if st.button("회화 훈련 시작", use_container_width=True, key="go_talk"):
        st.switch_page("pages/3_회화훈련.py")

st.divider()
st.info("✅ 팁: 왼쪽 상단 ☰ 메뉴(또는 사이드바)에서 페이지를 직접 이동할 수도 있어요.")
