from __future__ import annotations

import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Page Config (ONLY ONCE)
# ============================================================
st.set_page_config(
    page_title="왕초보 탈출 하테나일본어",
    page_icon="🟦",
    layout="centered",
)

# ============================================================
# ✅ UI: no sidebar + top padding fix
# ============================================================
st.markdown(
    """
<style>
[data-testid="stSidebar"]{display:none !important;}
.block-container{ padding-top: 2.4rem !important; padding-bottom: 2.0rem !important; }
@media (max-width: 768px){ .block-container{ padding-top: 2.8rem !important; } }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ✅ Secrets / Supabase
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", "")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================================
# ✅ Cookies (ONLY ONE)
# ============================================================
cookies = EncryptedCookieManager(prefix="hotena_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

def _save_tokens_to_cookies(access_token: str, refresh_token: str):
    cookies["access_token"] = access_token or ""
    cookies["refresh_token"] = refresh_token or ""
    cookies.save()

    # ✅ also mirror to session_state so sub-apps can read without creating cookie components
    st.session_state["_hotena_cookie_access_token"] = access_token or ""
    st.session_state["_hotena_cookie_refresh_token"] = refresh_token or ""

def _restore_session_from_cookies() -> bool:
    at = (cookies.get("access_token") or "").strip()
    rt = (cookies.get("refresh_token") or "").strip()

    if at:
        st.session_state["_hotena_cookie_access_token"] = at
    if rt:
        st.session_state["_hotena_cookie_refresh_token"] = rt

    if not at:
        return False

    try:
        res = supabase.auth.get_user(at)
        u = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
        if not u:
            return False
        st.session_state["user"] = u
        st.session_state["access_token"] = at
        st.session_state["refresh_token"] = rt
        return True
    except Exception:
        return False

def _is_logged_in() -> bool:
    return st.session_state.get("user") is not None and bool(st.session_state.get("access_token"))

def render_login():
    st.title("왕초보 탈출 하테나일본어")
    st.caption("로그인은 허브에서 한 번만 하면 됩니다.")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        email = st.text_input("이메일", key="login_email")
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", type="primary", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                session = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
                user = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
                if not session or not user:
                    st.error("로그인에 실패했습니다.")
                    st.stop()

                at = getattr(session, "access_token", None) or session.get("access_token")
                rt = getattr(session, "refresh_token", None) or session.get("refresh_token")

                st.session_state["user"] = user
                st.session_state["access_token"] = at
                st.session_state["refresh_token"] = rt

                _save_tokens_to_cookies(at, rt)

                # 허브는 홈으로
                st.session_state["hub_view"] = "home"
                st.rerun()
            except Exception as e:
                st.error(f"로그인 오류: {e}")

    with tab2:
        email = st.text_input("이메일", key="signup_email")
        pw = st.text_input("비밀번호", type="password", key="signup_pw")
        if st.button("회원가입", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.success("회원가입 요청을 보냈습니다. 이메일 인증이 필요할 수 있어요.")
            except Exception as e:
                st.error(f"회원가입 오류: {e}")

def render_hub():
    st.markdown("### 무엇을 훈련할까요?")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("단어 훈련", type="primary", use_container_width=True):
            st.session_state["hub_view"] = "word"
            st.rerun()
    with c2:
        if st.button("한자 훈련", type="primary", use_container_width=True):
            st.session_state["hub_view"] = "kanji"
            st.rerun()
    with c3:
        if st.button("회화 훈련", use_container_width=True):
            st.session_state["hub_view"] = "talk"
            st.rerun()

    st.markdown("---")
    if st.button("로그아웃", use_container_width=True):
        # clear
        for k in ["user","access_token","refresh_token"]:
            st.session_state.pop(k, None)
        for k in ["_hotena_cookie_access_token","_hotena_cookie_refresh_token"]:
            st.session_state.pop(k, None)
        _save_tokens_to_cookies("", "")
        st.session_state["hub_view"]="home"
        st.rerun()

def run_word():
    # ✅ 바로 시험(quiz)로
    st.session_state.page = "quiz"
    import runpy
    runpy.run_path("word_app.py", run_name="__main__")

def run_kanji():
    st.session_state.page = "quiz"
    import runpy
    runpy.run_path("kanji_app.py", run_name="__main__")

def render_talk():
    st.title("회화 훈련")
    st.info("회화 기능은 준비 중입니다.")

# ============================================================
# ✅ App flow
# ============================================================
# restore once each run (if possible)
_restore_session_from_cookies()

if "hub_view" not in st.session_state:
    st.session_state["hub_view"] = "home"

if not _is_logged_in():
    render_login()
    st.stop()

view = st.session_state.get("hub_view", "home")

if view == "home":
    render_hub()
elif view == "word":
    run_word()
elif view == "kanji":
    run_kanji()
else:
    render_talk()
