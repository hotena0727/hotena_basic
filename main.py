from __future__ import annotations

import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# local modules
import word_app
import kanji_app

# ============================================================
# ✅ Page Config (ONLY ONCE)
# ============================================================
st.set_page_config(
    page_title="hotena",
    page_icon="🟦",
    layout="centered",
)

# ============================================================
# ✅ Top padding fix (상단 잘림 방지)
# ============================================================
st.markdown(
    """
<style>
/* Streamlit 기본 상단 여백이 테마/브라우저에 따라 달라서, 안전하게 padding 확보 */
.block-container{
  padding-top: 2.2rem !important;
  padding-bottom: 2.0rem !important;
}
/* 모바일에서 상단 헤더 겹침 방지 */
@media (max-width: 768px){
  .block-container{ padding-top: 2.6rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ✅ Secrets
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", "change-me")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Supabase secrets(SUPABASE_URL, SUPABASE_ANON_KEY)가 설정되어 있지 않습니다.")
    st.stop()

# ============================================================
# ✅ Shared singletons
# ============================================================
@st.cache_resource(show_spinner=False)
def get_sb():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_cookies():
    # ✅ prefix를 hotena로 통일 (요청사항)
    cm = EncryptedCookieManager(prefix="hotena_", password=COOKIE_PASSWORD)
    if not cm.ready():
        st.stop()
    return cm

sb = get_sb()
cookies = get_cookies()

# ============================================================
# ✅ Session restore (from cookies)
# ============================================================
def restore_session_from_cookie():
    if st.session_state.get("user") and st.session_state.get("access_token"):
        return

    at = cookies.get("access_token")
    rt = cookies.get("refresh_token")

    if at:
        st.session_state["access_token"] = at
        st.session_state["refresh_token"] = rt

        try:
            # supabase-py: get_user(jwt)
            u = sb.auth.get_user(at)
            if u and getattr(u, "user", None):
                st.session_state["user"] = u.user
                st.session_state["login_email"] = getattr(u.user, "email", None) or st.session_state.get("login_email", "")
        except Exception:
            # 토큰이 만료/무효일 수 있음. 일단 비움
            st.session_state.pop("user", None)
            st.session_state.pop("access_token", None)
            st.session_state.pop("refresh_token", None)

def clear_session():
    for k in ["user", "access_token", "refresh_token", "login_email"]:
        st.session_state.pop(k, None)
    try:
        cookies.pop("access_token", None)
        cookies.pop("refresh_token", None)
        cookies.save()
    except Exception:
        pass

restore_session_from_cookie()

# ============================================================
# ✅ Hub state
# ============================================================
if "hub_view" not in st.session_state:
    st.session_state["hub_view"] = "home"  # home | word | kanji | talk

# ============================================================
# ✅ Auth UI (허브에서 1번만)
# ============================================================
def render_login():
    st.markdown("<div style='max-width:520px; margin:0 auto;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-weight:900; font-size:22px; margin:4px 0 8px 0;'>로그인</div>", unsafe_allow_html=True)

    if "hub_auth_mode" not in st.session_state:
        st.session_state["hub_auth_mode"] = "login"

    mode = st.radio(
        label="",
        options=["login", "signup"],
        format_func=lambda x: "로그인" if x == "login" else "회원가입",
        horizontal=True,
        key="hub_auth_mode_radio",
        index=0 if st.session_state["hub_auth_mode"] == "login" else 1,
    )
    st.session_state["hub_auth_mode"] = mode

    if mode == "login":
        email = st.text_input("이메일", key="hub_login_email")
        pw = st.text_input("비밀번호", type="password", key="hub_login_pw")

        if st.button("로그인", use_container_width=True, key="hub_btn_login"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state["user"] = res.user
                st.session_state["login_email"] = email.strip()

                if res.session and res.session.access_token:
                    st.session_state["access_token"] = res.session.access_token
                    st.session_state["refresh_token"] = res.session.refresh_token
                    cookies["access_token"] = res.session.access_token
                    cookies["refresh_token"] = res.session.refresh_token
                    cookies.save()
                st.success("로그인 완료!")
                st.rerun()
            except Exception:
                st.error("로그인 실패: 이메일/비밀번호 또는 이메일 인증 상태를 확인해주세요.")
                st.stop()
    else:
        email = st.text_input("이메일", key="hub_signup_email")
        pw = st.text_input("비밀번호", type="password", key="hub_signup_pw")
        st.caption("비밀번호는 8자리 이상을 권장합니다.")
        if st.button("회원가입", use_container_width=True, key="hub_btn_signup"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()
            try:
                sb.auth.sign_up({"email": email, "password": pw})
                st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요. 메일함 확인 후 로그인해 주세요.")
            except Exception:
                st.error("회원가입 실패: 이미 가입된 이메일이거나, 비밀번호 조건을 확인해주세요.")
                st.stop()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ✅ Global header (logged-in)
# ============================================================
def render_header():
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")

    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("🏠 홈", use_container_width=True, key="hub_home_btn"):
            st.session_state["hub_view"] = "home"
            st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center; font-weight:900; font-size:16px;'>hotena</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center; opacity:.75; font-size:12px;'>{email}</div>", unsafe_allow_html=True)
    with c3:
        if st.button("로그아웃", use_container_width=True, key="hub_logout_btn"):
            clear_session()
            st.session_state["hub_view"] = "home"
            st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# ============================================================
# ✅ Home (3 buttons)
# ============================================================
def render_home():
    st.markdown("<div style='font-weight:900; font-size:30px; line-height:1.1;'>오늘의 훈련을 선택하세요</div>", unsafe_allow_html=True)
    st.markdown("<div style='opacity:.8; margin-top:6px;'>단어 / 한자 / 회화(준비중)</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("단어", use_container_width=True, key="hub_btn_word", type="primary"):
            st.session_state["hub_view"] = "word"
            st.rerun()
    with b2:
        if st.button("한자", use_container_width=True, key="hub_btn_kanji"):
            st.session_state["hub_view"] = "kanji"
            st.rerun()
    with b3:
        if st.button("회화(준비중)", use_container_width=True, key="hub_btn_talk"):
            st.session_state["hub_view"] = "talk"
            st.rerun()

# ============================================================
# ✅ Talk placeholder
# ============================================================
def render_talk_placeholder():
    st.info("회화 훈련은 현재 제작 중입니다. 조금만 기다려 주세요 🙂")

# ============================================================
# ✅ Main
# ============================================================
if not st.session_state.get("user") or not st.session_state.get("access_token"):
    # 로그인 이전에도 홈 버튼 3개는 보여줄 수 있지만,
    # 요청사항: '허브에서 한번만 로그인'이므로 여기서 먼저 로그인 처리
    render_login()
    st.stop()

render_header()

view = st.session_state.get("hub_view", "home")

if view == "home":
    render_home()
elif view == "word":
    # ✅ word_app은 내부적으로 st.session_state.user/access_token을 그대로 사용
    word_app.render_word_app()
elif view == "kanji":
    kanji_app.render_kanji_app()
else:
    render_talk_placeholder()
