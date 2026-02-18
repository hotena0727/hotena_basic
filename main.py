from __future__ import annotations

import os
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
# ✅ UI Fix: hide sidebar + top padding (no sidebar, no clipping)
# ============================================================
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

# ============================================================
# ✅ Secrets / Supabase
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", os.getenv("COOKIE_PASSWORD", ""))

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("SUPABASE_URL / SUPABASE_ANON_KEY 가 설정되어 있지 않습니다.")
    st.stop()
if not COOKIE_PASSWORD:
    st.error("COOKIE_PASSWORD 가 설정되어 있지 않습니다.")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================================
# ✅ Cookies (ONE manager only)
# ============================================================
cookies = EncryptedCookieManager(prefix="hotena_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.info("잠깐만요! 곧 시작할게요🙂")
    st.stop()

def _restore_session_from_cookies() -> bool:
    at = (cookies.get("access_token") or "").strip()
    rt = (cookies.get("refresh_token") or "").strip()
    if not at:
        return False

    # session_state restore
    st.session_state["access_token"] = at
    if rt:
        st.session_state["refresh_token"] = rt

    # try to get user (best effort)
    try:
        u = sb.auth.get_user(at).user
        st.session_state["user"] = u
        return True
    except Exception:
        return False

def is_logged_in() -> bool:
    return bool(st.session_state.get("user")) and bool(st.session_state.get("access_token"))

def require_login() -> None:
    if is_logged_in():
        return
    if _restore_session_from_cookies():
        return

    # ---------------------------
    # Login / Signup UI (hub only)
    # ---------------------------
    st.title("왕초보 탈출 하테나일본어")
    st.caption("단어·한자·회화 훈련을 한 곳에서 이용합니다. 로그인은 여기서 한 번만 하면 됩니다.")

    mode = st.segmented_control(
        " ",
        options=["login", "signup"],
        format_func=lambda x: "로그인" if x == "login" else "회원가입",
        default="login",
        label_visibility="collapsed",
        key="hub_auth_mode",
    )

    if mode == "login":
        email = st.text_input("이메일", key="hub_login_email")
        pw = st.text_input("비밀번호", type="password", key="hub_login_pw")

        if st.button("로그인", use_container_width=True, key="hub_btn_login"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()
            try:
                res = sb.auth.sign_in_with_password({"email": email.strip(), "password": pw})
                st.session_state["user"] = res.user
                if res.session and res.session.access_token:
                    st.session_state["access_token"] = res.session.access_token
                    st.session_state["refresh_token"] = res.session.refresh_token or ""
                    cookies["access_token"] = res.session.access_token
                    cookies["refresh_token"] = res.session.refresh_token or ""
                    cookies.save()
                st.success("로그인 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"로그인 실패: {e}")

    else:
        email = st.text_input("이메일", key="hub_signup_email")
        pw = st.text_input("비밀번호(8자리 이상 권장)", type="password", key="hub_signup_pw")
        pw2 = st.text_input("비밀번호 확인", type="password", key="hub_signup_pw2")

        if st.button("회원가입", use_container_width=True, key="hub_btn_signup"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()
            if pw != pw2:
                st.warning("비밀번호가 일치하지 않습니다.")
                st.stop()
            try:
                sb.auth.sign_up({"email": email.strip(), "password": pw})
                st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요. 인증 후 로그인해 주세요.")
            except Exception as e:
                st.error(f"회원가입 실패: {e}")

    st.stop()

# ============================================================
# ✅ Hub Home
# ============================================================
require_login()

st.title("왕초보 탈출 하테나일본어")
st.write("원하는 훈련을 선택해 주세요.")

col1, col2, col3 = st.columns(3, gap="small")

with col1:
    if st.button("📘 단어 훈련", use_container_width=True, key="hub_go_word"):
        st.switch_page("pages/word_app.py")

with col2:
    if st.button("🈶 한자 훈련", use_container_width=True, key="hub_go_kanji"):
        st.switch_page("pages/kanji_app.py")

with col3:
    if st.button("💬 회화 훈련", use_container_width=True, key="hub_go_talk"):
        st.switch_page("pages/talk_placeholder.py")

st.divider()

if st.button("로그아웃", use_container_width=True, key="hub_logout"):
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    for k in ["user", "access_token", "refresh_token"]:
        st.session_state.pop(k, None)
    # clear cookies
    cookies["access_token"] = ""
    cookies["refresh_token"] = ""
    cookies.save()
    st.rerun()
