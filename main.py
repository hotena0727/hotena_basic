from __future__ import annotations
import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager
import base64

# ============================================================
# 기본 설정
# ============================================================

APP_TITLE = "왕초보 탈출 하테나일본어"
BUILD_ID = "V1-STABLE"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🟦",
    layout="centered",
)

# ============================================================
# Supabase
# ============================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
COOKIE_PASSWORD = st.secrets["COOKIE_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

cookies = EncryptedCookieManager(
    prefix="hotena_auth_",
    password=COOKIE_PASSWORD,
)

if not cookies.ready():
    st.stop()

# ============================================================
# 로그인 유지
# ============================================================

def save_session(session):
    cookies["access_token"] = session.access_token
    cookies["refresh_token"] = session.refresh_token
    cookies.save()

def restore_session():
    at = cookies.get("access_token")
    if at:
        st.session_state["access_token"] = at

def is_logged_in():
    return "access_token" in st.session_state

def logout():
    cookies.clear()
    cookies.save()
    st.session_state.clear()
    st.rerun()

restore_session()

# ============================================================
# 로그인 화면
# ============================================================

def login_page():
    st.title(APP_TITLE)
    st.caption(f"빌드: {BUILD_ID}")

    email = st.text_input("이메일")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.session:
            st.session_state["access_token"] = res.session.access_token
            save_session(res.session)
            st.rerun()
        else:
            st.error("로그인 실패")

# ============================================================
# 상단 메뉴 (항상 고정)
# ============================================================

def top_menu():
    cols = st.columns(6)

    if cols[0].button("홈"):
        st.session_state["page"] = "home"

    if cols[1].button("단어"):
        st.session_state["page"] = "word"

    if cols[2].button("한자"):
        st.session_state["page"] = "kanji"

    if cols[3].button("회화"):
        st.session_state["page"] = "talk"

    if cols[4].button("마이페이지"):
        st.session_state["page"] = "mypage"

    if cols[5].button("로그아웃"):
        logout()

    st.divider()

# ============================================================
# 허브
# ============================================================

def home_page():
    st.title(APP_TITLE)
    st.caption(f"빌드: {BUILD_ID}")

    if st.button("단어 훈련 시작"):
        st.session_state["page"] = "word"

    if st.button("한자 훈련 시작"):
        st.session_state["page"] = "kanji"

    if st.button("회화 훈련"):
        st.session_state["page"] = "talk"

# ============================================================
# 임시 훈련 페이지 (V1 안정용)
# ============================================================

def word_page():
    st.header("단어 훈련 페이지")
    st.write("여기에 기존 단어 앱 로직을 붙이면 됩니다.")

def kanji_page():
    st.header("한자 훈련 페이지")
    st.write("여기에 기존 한자 앱 로직을 붙이면 됩니다.")

def talk_page():
    st.header("회화 훈련")
    st.write("준비중입니다.")

def mypage():
    st.header("마이페이지")
    st.write("회원 정보 영역")

# ============================================================
# 라우터
# ============================================================

if not is_logged_in():
    login_page()
else:
    top_menu()

    page = st.session_state.get("page", "home")

    if page == "home":
        home_page()
    elif page == "word":
        word_page()
    elif page == "kanji":
        kanji_page()
    elif page == "talk":
        talk_page()
    elif page == "mypage":
        mypage()
