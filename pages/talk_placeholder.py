from __future__ import annotations
import streamlit as st

st.set_page_config(page_title="왕초보 탈출 하테나일본어", page_icon="🟦", layout="centered")

st.markdown(
    """
<style>
[data-testid="stSidebar"]{display:none;}
[data-testid="collapsedControl"]{display:none;}
.block-container{padding-top:2.2rem !important; padding-bottom:2.0rem !important;}
@media (max-width:768px){.block-container{padding-top:2.6rem !important;}}
</style>
""",
    unsafe_allow_html=True,
)

st.title("💬 회화 훈련")
st.info("준비중인 기능입니다. 곧 업데이트할게요🙂")

if st.button("🏠 홈으로", use_container_width=True):
    st.switch_page("main.py")
