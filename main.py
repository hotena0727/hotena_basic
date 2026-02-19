from __future__ import annotations

import os
import traceback
import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

import ui

# ============================================================
# ✅ Page Config (ONLY ONCE)
# ============================================================
st.set_page_config(page_title=ui.APP_TITLE, page_icon="🟦", layout="centered")

# ============================================================
# ✅ Global styles (Design lock)
# ============================================================
ui.apply_global_styles()

# ============================================================
# ✅ Secrets / Supabase
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", "change-me")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None

# ============================================================
# ✅ Cookies (ONLY ONE)
# ============================================================
cookies = EncryptedCookieManager(prefix="hotena_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

# ============================================================
# ✅ Auth helpers
# ============================================================
def _restore_session_from_cookies() -> bool:
    if not supabase:
        return False

    at = (cookies.get("access_token") or "").strip()
    rt = (cookies.get("refresh_token") or "").strip()

    if not at:
        return False

    try:
        res = supabase.auth.get_user(at)
        u = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
        if not u:
            return False

        st.session_state["access_token"] = at
        st.session_state["refresh_token"] = rt
        st.session_state["user"] = u
        return True
    except Exception:
        return False

def is_logged_in() -> bool:
    return bool(st.session_state.get("user")) and bool(st.session_state.get("access_token"))

def require_login():
    if is_logged_in():
        return
    _restore_session_from_cookies()

def render_login():
    ui.hub_header()

    if not supabase:
        st.error("Supabase 설정이 없습니다. secrets에 SUPABASE_URL / SUPABASE_ANON_KEY를 설정해주세요.")
        return

    st.session_state.setdefault("auth_mode", "login")
    cols = st.columns(2)
    with cols[0]:
        if st.button("로그인", use_container_width=True):
            st.session_state["auth_mode"] = "login"
    with cols[1]:
        if st.button("회원가입", use_container_width=True):
            st.session_state["auth_mode"] = "signup"

    mode = st.session_state["auth_mode"]
    ui.hr()

    email = st.text_input("이메일", key="auth_email")
    pw = st.text_input("비밀번호", type="password", key="auth_pw")

    if mode == "login":
        if st.button("로그인하기", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                session = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
                user = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
                if not session or not user:
                    st.error("로그인에 실패했습니다.")
                    return

                st.session_state["user"] = user
                st.session_state["access_token"] = session.access_token
                st.session_state["refresh_token"] = session.refresh_token

                cookies["access_token"] = session.access_token
                cookies["refresh_token"] = session.refresh_token
                cookies.save()

                st.session_state["page"] = "home"
                st.rerun()
            except Exception as e:
                st.error(f"로그인 오류: {e}")

    else:
        if st.button("회원가입하기", use_container_width=True):
            try:
                res = supabase.auth.sign_up({"email": email, "password": pw})
                st.success("회원가입 요청이 처리되었습니다. 이메일 인증이 필요한 경우 메일을 확인해주세요.")
            except Exception as e:
                st.error(f"회원가입 오류: {e}")

def render_home():
    ui.hub_header()

    # (optional) show login status small
    if is_logged_in():
        u = st.session_state.get("user")
        email = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else "")
        st.caption(f"로그인됨: {email}")

    # Main actions (V1)
    if st.button("📘 단어 훈련", use_container_width=True):
        st.session_state["page"] = "word"
        st.session_state["entry_target"] = "quiz"
        st.rerun()

    if st.button("✍️ 한자 훈련", use_container_width=True):
        st.session_state["page"] = "kanji"
        st.session_state["entry_target"] = "quiz"
        st.rerun()

    if st.button("🗣 회화 훈련", use_container_width=True):
        st.session_state["page"] = "talk"
        st.rerun()

def render_talk():
    ui.slim_header("회화 훈련", "준비중")
    st.info("회화 기능은 준비 중입니다.")

def _run_child(entry: str, which: str):
    # Router runs wrappers that execute the original apps safely
    if which == "word":
        import word_app
        word_app.run(entry=entry)
    elif which == "kanji":
        import kanji_app
        kanji_app.run(entry=entry)

def render_router():
    page = st.session_state.get("page", "home")
    if page == "home":
        render_home()
        return

    if not is_logged_in():
        # If user navigates directly, force login
        st.session_state["page"] = "home"
        st.rerun()

    entry = st.session_state.get("entry_target", "quiz")

    if page == "word":
        ui.slim_header("단어 훈련")
        _run_child(entry, "word")
        return

    if page == "kanji":
        ui.slim_header("한자 훈련")
        _run_child(entry, "kanji")
        return

    if page == "talk":
        render_talk()
        return

    st.session_state["page"] = "home"
    st.rerun()

# ============================================================
# ✅ App entry
# ============================================================
try:
    require_login()
    if not is_logged_in():
        render_login()
    else:
        render_router()
except Exception:
    st.error("예상치 못한 오류가 발생했습니다.")
    st.code(traceback.format_exc())
