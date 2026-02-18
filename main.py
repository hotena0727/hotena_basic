from __future__ import annotations

from pathlib import Path
import time
import traceback

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
# ✅ Top padding fix (상단 잘림 방지)
# ============================================================
st.markdown(
    """
<style>
.block-container{
  padding-top: 2.2rem !important;
  padding-bottom: 2.0rem !important;
}
@media (max-width: 768px){
  .block-container{ padding-top: 2.7rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ✅ Secrets / Clients
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", "")

if not SUPABASE_URL or not SUPABASE_ANON_KEY or not COOKIE_PASSWORD:
    st.error("secrets 설정이 필요합니다: SUPABASE_URL, SUPABASE_ANON_KEY, COOKIE_PASSWORD")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ✅ 두 앱(단어/한자)이 각각 다른 prefix를 쓰는 경우가 있어, 둘 다에 토큰을 저장합니다.
cookies_word = EncryptedCookieManager(prefix="hotena_beginner_", password=COOKIE_PASSWORD)
cookies_kanji = EncryptedCookieManager(prefix="hotena_kanji_", password=COOKIE_PASSWORD)

if not cookies_word.ready() or not cookies_kanji.ready():
    st.stop()

def _set_tokens_to_all_cookies(access_token: str, refresh_token: str):
    for ck in (cookies_word, cookies_kanji):
        ck["access_token"] = access_token or ""
        ck["refresh_token"] = refresh_token or ""
        try:
            ck.save()
        except Exception:
            pass

def _clear_tokens_all():
    _set_tokens_to_all_cookies("", "")
    for k in ["user", "access_token", "refresh_token", "login_email", "plan_cached"]:
        if k in st.session_state:
            del st.session_state[k]

def _restore_session_from_cookies() -> bool:
    # 이미 복원됨
    if st.session_state.get("user") is not None and st.session_state.get("access_token"):
        return True

    at = (cookies_word.get("access_token") or "").strip()
    rt = (cookies_word.get("refresh_token") or "").strip()

    # word 쪽에 없으면 kanji 쪽에서 한 번 더
    if not at and not rt:
        at = (cookies_kanji.get("access_token") or "").strip()
        rt = (cookies_kanji.get("refresh_token") or "").strip()

    if not at and not rt:
        return False

    # access_token이 있으면 우선 set_session 시도
    try:
        if at and rt:
            sb.auth.set_session(at, rt)
        elif rt and not at:
            # refresh_token만 있다면 refresh 시도
            refreshed = sb.auth.refresh_session(rt)
            if refreshed and getattr(refreshed, "session", None):
                at = refreshed.session.access_token
                rt = refreshed.session.refresh_token
                sb.auth.set_session(at, rt)

        u = sb.auth.get_user()
        user_obj = getattr(u, "user", None) or getattr(u, "data", None) or None
        if user_obj is None:
            return False

        st.session_state["user"] = user_obj
        st.session_state["access_token"] = at
        st.session_state["refresh_token"] = rt
        email = getattr(user_obj, "email", None)
        if email:
            st.session_state["login_email"] = str(email).strip()

        # 두 prefix에 모두 저장
        _set_tokens_to_all_cookies(at, rt)
        return True
    except Exception:
        return False

def require_login():
    if _restore_session_from_cookies():
        return

    st.markdown("## 왕초보 탈출 하테나일본어")
    st.caption("로그인은 한 번만 하면 됩니다. (단어/한자 공통)")
    with st.container(border=True):
        mode = st.radio("",
                        ["login", "signup"],
                        format_func=lambda x: "로그인" if x == "login" else "회원가입",
                        horizontal=True)
        email = st.text_input("이메일", key="hub_email")
        pw = st.text_input("비밀번호", type="password", key="hub_pw")

        if mode == "login":
            if st.button("로그인", type="primary", use_container_width=True):
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                    sess = getattr(res, "session", None)
                    user_obj = getattr(res, "user", None)
                    if not sess or not user_obj:
                        st.error("로그인에 실패했습니다. 이메일/비밀번호를 확인해 주세요.")
                        st.stop()

                    st.session_state["user"] = user_obj
                    st.session_state["access_token"] = sess.access_token
                    st.session_state["refresh_token"] = sess.refresh_token
                    st.session_state["login_email"] = email.strip()
                    _set_tokens_to_all_cookies(sess.access_token, sess.refresh_token)
                    st.rerun()
                except Exception as e:
                    st.error(f"로그인 오류: {e}")
                    st.stop()
        else:
            if st.button("회원가입", type="primary", use_container_width=True):
                try:
                    res = sb.auth.sign_up({"email": email, "password": pw})
                    st.success("회원가입 요청 완료! 이메일 인증이 필요한 설정이라면 메일을 확인해 주세요.")
                except Exception as e:
                    st.error(f"회원가입 오류: {e}")
                    st.stop()

    st.stop()

# ============================================================
# ✅ Router (sidebar 없이)
# ============================================================
if "route" not in st.session_state:
    st.session_state["route"] = "home"

def go(route: str):
    st.session_state["route"] = route
    st.rerun()

# 로그인 1회 통합
require_login()

# 상단 유저 표시 + 로그아웃
u = st.session_state.get("user")
email = getattr(u, "email", None) if u else None
top_l, top_r = st.columns([3, 1])
with top_l:
    st.caption(f"✅ 로그인됨: {email}" if email else "✅ 로그인됨")
with top_r:
    if st.button("로그아웃", use_container_width=True):
        try:
            sb.auth.sign_out()
        except Exception:
            pass
        _clear_tokens_all()
        go("home")

st.markdown("---")

route = st.session_state.get("route", "home")

if route == "home":
    st.markdown("## 메뉴 선택")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("단어 훈련", use_container_width=True, type="primary"):
            # 충돌 완화: 다른 앱 키 일부 정리
            for k in ["page", "quiz", "answers", "submitted", "wrong_list"]:
                st.session_state.pop(k, None)
            go("word")
    with c2:
        if st.button("한자 훈련", use_container_width=True, type="primary"):
            for k in ["page", "quiz", "answers", "submitted", "wrong_list"]:
                st.session_state.pop(k, None)
            go("kanji")
    with c3:
        if st.button("회화 훈련", use_container_width=True):
            go("talk")

    st.caption("※ 홈은 사이드바 없이 버튼으로만 이동합니다.")

elif route == "talk":
    st.markdown("## 회화 훈련")
    st.info("준비중입니다 🙂")
    if st.button("⬅ 홈으로", use_container_width=True):
        go("home")

elif route in ("word", "kanji"):
    # 공통: 홈으로
    if st.button("⬅ 홈으로", use_container_width=True):
        go("home")

    # --------------------------------------------------------
    # ✅ Run selected app in isolated namespace
    # --------------------------------------------------------
    base = Path(__file__).parent
    src_path = base / ("word_src.py" if route == "word" else "kanji_src.py")
    try:
        code = src_path.read_text(encoding="utf-8")
    except Exception as e:
        st.error(f"앱 파일을 찾을 수 없습니다: {src_path} ({e})")
        st.stop()

    # pages에서 set_page_config를 다시 호출하지 않도록, main이 이미 처리함
    # (word_src/kanji_src에서 set_page_config는 제거됨)

    g = {
        "__file__": str(src_path),
        "__name__": "__main__",
        "st": st,
    }
    try:
        exec(compile(code, str(src_path), "exec"), g, g)
    except Exception as e:
        st.error("앱 실행 중 오류가 발생했습니다.")
        st.code(traceback.format_exc())
        st.stop()

else:
    st.session_state["route"] = "home"
    st.rerun()
