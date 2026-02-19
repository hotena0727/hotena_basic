from __future__ import annotations

from pathlib import Path
import os
import runpy

import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ App Config (ONLY ONCE)
# ============================================================
st.set_page_config(
    page_title="왕초보 탈출 하테나일본어",
    page_icon="🟦",
    layout="centered",
)

# ============================================================
# ✅ Global UI fixes (no sidebar + top clipping fix)
# ============================================================
st.markdown(
    """
<style>
/* 상단 잘림 방지 */
.block-container{
  padding-top: 2.2rem !important;
  padding-bottom: 2.0rem !important;
}
@media (max-width: 768px){
  .block-container{ padding-top: 2.6rem !important; }
}

/* 사이드바 완전 숨김 */
section[data-testid="stSidebar"]{display:none !important;}
div[data-testid="stSidebarNav"]{display:none !important;}
button[kind="header"]{display:none !important;}
</style>
""",
    unsafe_allow_html=True,
)

# ✅ HUB MODE FLAG (router execution)
st.session_state["__hotena_hub_mode__"] = True

# ============================================================
# ✅ Settings / Secrets
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", "")).strip()
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_ANON_KEY", "")).strip()
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", os.environ.get("COOKIE_PASSWORD", "")).strip()

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("SUPABASE_URL / SUPABASE_ANON_KEY 가 설정되어 있지 않습니다. (Streamlit secrets 또는 환경변수)")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def _ensure_user_object():
    # word_app/kanji_app는 st.session_state['user']가 있어야 로그인 UI가 뜨지 않음
    if st.session_state.get("user") is not None:
        return
    at = st.session_state.get("access_token") or ""
    uemail = st.session_state.get("user_email") or ""
    if at:
        try:
            res = sb.auth.get_user(at)
            u = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
            if u is not None:
                st.session_state["user"] = u
                return
        except Exception:
            pass
    # 최후의 fallback: 최소 객체(일부 기능은 제한될 수 있음)
    if uemail:
        from types import SimpleNamespace
        st.session_state["user"] = SimpleNamespace(id="", email=uemail)

# ============================================================
# ✅ Router
# ============================================================
if "page" not in st.session_state:
    st.session_state["page"] = "home"

def goto(page: str):
    st.session_state["page"] = page
    st.rerun()

# ============================================================
# ✅ Auth (Hub-only)
# - 쿠키 컴포넌트 중복을 피하려고: home 화면에서만 cookies 생성
# ============================================================
def _home_cookies():
    cookies = EncryptedCookieManager(prefix="hotena_", password=COOKIE_PASSWORD or "hotena_cookie_password")
    if not cookies.ready():
        st.stop()
    return cookies

def _restore_session_from_cookies() -> bool:
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

def require_login():
    if st.session_state.get("is_authed") and st.session_state.get("access_token"):
        _ensure_user_object()
        return
    # if not authed, go home
    st.session_state["page"] = "home"
    st.rerun()

def render_home():
    st.title("왕초보 탈출 하테나일본어")
    st.caption("단어 / 한자 / 회화 훈련을 선택해 주세요.")

    cookies = _home_cookies()
    if not st.session_state.get("is_authed"):
        _restore_session_from_cookies()
        _ensure_user_object()

    if not st.session_state.get("is_authed"):
        st.subheader("로그인")
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("이메일", key="login_email")
            pw = st.text_input("비밀번호", type="password", key="login_pw")
            col1, col2 = st.columns(2)
            login_btn = col1.form_submit_button("로그인", use_container_width=True)
            signup_btn = col2.form_submit_button("회원가입", use_container_width=True)

        if login_btn:
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                sess = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
                if not sess:
                    st.error("로그인에 실패했습니다. 이메일/비밀번호를 확인해 주세요.")
                else:
                    at = getattr(sess, "access_token", None) or sess.get("access_token")
                    rt = getattr(sess, "refresh_token", None) or sess.get("refresh_token")
                    cookies["access_token"] = at or ""
                    cookies["refresh_token"] = rt or ""
                    cookies["user_email"] = email or ""
                    cookies.save()
                    st.session_state["access_token"] = at or ""
                    st.session_state["refresh_token"] = rt or ""
                    st.session_state["user_email"] = email or ""
                    st.session_state["is_authed"] = True
                    st.success("로그인 완료!")
                    st.rerun()
            except Exception as e:
                st.error(f"로그인 오류: {e}")

        if signup_btn:
            try:
                res = sb.auth.sign_up({"email": email, "password": pw})
                st.success("회원가입 요청이 완료되었습니다. 이메일 인증이 필요한 경우 메일함을 확인해 주세요.")
            except Exception as e:
                st.error(f"회원가입 오류: {e}")

        st.stop()

    st.success(f"로그인 상태: {st.session_state.get('user_email','')}".strip() or "로그인 상태")

    st.markdown("### 훈련 선택")
    b1, b2, b3 = st.columns(3)
    if b1.button("📘 단어 훈련", use_container_width=True):
        goto("word")
    if b2.button("✍️ 한자 훈련", use_container_width=True):
        goto("kanji")
    if b3.button("🗣 회화 훈련", use_container_width=True):
        goto("talk")

def render_talk():
    require_login()
    st.title("🗣 회화 훈련")
    st.info("회화 기능은 현재 준비 중입니다.")
    if st.button("← 홈으로", use_container_width=True):
        goto("home")

def _run_script(filename: str):
    require_login()
    # 상단에 홈 버튼 (사이드바 없이)
    top = st.columns([1, 6])[0]
    if top.button("← 홈", use_container_width=True):
        goto("home")

    path = Path(__file__).parent / filename
    if not path.exists():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()

    # 실행 전에 hub 세션 정보를 환경으로도 살짝 제공(필요시)
    os.environ["HOTENA_ACCESS_TOKEN"] = st.session_state.get("access_token", "") or ""
    os.environ["HOTENA_USER_EMAIL"] = st.session_state.get("user_email", "") or ""

    # runpy로 '별도 스크립트처럼' 실행 (import 충돌 최소화)
    runpy.run_path(str(path), run_name="__main__")

page = st.session_state.get("page", "home")

if page == "home":
    render_home()
elif page == "word":
    _run_script("word_app.py")
elif page == "kanji":
    _run_script("kanji_app.py")
elif page == "talk":
    render_talk()
else:
    st.session_state["page"] = "home"
    st.rerun()
