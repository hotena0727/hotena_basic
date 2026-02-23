
import streamlit as st

# ==================================================
# 1. 기본 페이지 설정 (엔트리에서만)
# ==================================================
st.set_page_config(
    page_title="하테나일본어",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================================================
# 2. 상단 공백/빈 블록 제거 CSS (1회만 실행)
# ==================================================
if "_global_cleanup_once" not in st.session_state:
    st.markdown("""
    <style>

    /* 상단 기본 패딩 완전 제거 */
    section.main > div.block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }

    /* 빈 VerticalBlock 제거 */
    div[data-testid="stVerticalBlock"]:empty {
        display: none !important;
    }

    /* 첫 번째 블록 여백 제거 */
    div[data-testid="stVerticalBlock"]:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* Streamlit 기본 헤더/푸터 숨김 */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    </style>
    """, unsafe_allow_html=True)

    st.session_state["_global_cleanup_once"] = True


# ==================================================
# 3. 페이지 라우팅 상태 초기화
# ==================================================
if "page" not in st.session_state:
    st.session_state.page = "home"


# ==================================================
# 4. 페이지 모듈 import
# ==================================================
import hotena_basic   # 단어 훈련
import app            # 한자 훈련
import talk           # 회화 훈련
import mypage         # 마이페이지


# ==================================================
# 5. 홈 화면
# ==================================================
def render_home():
    st.markdown("## 왕초보 탈출 하테나일본어")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📘 단어 훈련"):
            st.session_state.page = "word"
            st.rerun()

    with col2:
        if st.button("🈶 한자 훈련"):
            st.session_state.page = "kanji"
            st.rerun()

    with col3:
        if st.button("🗣 회화 훈련"):
            st.session_state.page = "talk"
            st.rerun()


# ==================================================
# 6. 라우팅 실행
# ==================================================
if st.session_state.page == "home":
    render_home()

elif st.session_state.page == "word":
    hotena_basic.render_word()

elif st.session_state.page == "kanji":
    app.render_kanji()

elif st.session_state.page == "talk":
    talk.render_talk()

elif st.session_state.page == "mypage":
    mypage.render_mypage()
