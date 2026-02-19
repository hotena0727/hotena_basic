from __future__ import annotations

import base64
import traceback
import streamlit as st
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Identity (naming rules)
# - internal id: hotena (fixed)
# - display name: 하테나일본어 / 왕초보 탈출 하테나일본어
# ============================================================
APP_ID = "hotena"
APP_TITLE = "왕초보 탈출 하테나일본어"
APP_SLOGAN = "오늘도 10문제만."
BUILD_ID = "V1-LOCKED-20260219-230000"  # ✅ 적용 확인용(필요시 바꿔도 됨)

# ============================================================
# ✅ Page config (ONLY ONCE)
# ============================================================
st.set_page_config(page_title=APP_TITLE, page_icon="🟦", layout="centered")

# ============================================================
# ✅ Design lock (global styles)
# ============================================================
def apply_global_styles():
    st.markdown(
        r"""
<style>
/* width + top clipping fix */
.block-container{
  max-width: min(820px, 92vw) !important;
  padding-top: 2.7rem !important;
  padding-bottom: 2.0rem !important;
}

/* hide chrome */
header[data-testid="stHeader"]{visibility:hidden;height:0;}
footer{visibility:hidden;height:0;}
#MainMenu{visibility:hidden;}
[data-testid="stSidebar"]{display:none !important;}

/* buttons */
.stButton > button{
  height: 44px;
  font-size: 14px;
  border-radius: 999px;
  padding: 0 12px;
}

/* hub */
.hub-title{text-align:center;font-size:26px;font-weight:700;margin:0 0 6px;}
.hub-subtitle{text-align:center;font-size:15px;color:rgba(0,0,0,0.62);margin:0 0 14px;}
.build{ text-align:center;font-size:12px;color:rgba(0,0,0,0.45);margin:0 0 18px;}
.hr{height:1px;background:rgba(0,0,0,0.08);margin:12px 0 14px;}
.slimbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 10px;}
.slim-left{font-size:16px;font-weight:700;}
.slim-right{font-size:13px;color:rgba(0,0,0,0.55);}

/* top menu */
.topmenu-wrap{ margin: 0 0 10px; }
</style>
""",
        unsafe_allow_html=True,
    )

apply_global_styles()

def hub_header():
    st.markdown(f'<div class="hub-title">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hub-subtitle">{APP_SLOGAN}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="build">빌드: {BUILD_ID}</div>', unsafe_allow_html=True)

def hr():
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

def slim_header(left: str, right: str = ""):
    st.markdown(
        f'<div class="slimbar"><div class="slim-left">{left}</div><div class="slim-right">{right}</div></div>',
        unsafe_allow_html=True,
    )

# ============================================================
# ✅ Supabase + Cookies (ONLY ONE cookie component)
# ============================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
COOKIE_PASSWORD = st.secrets.get("COOKIE_PASSWORD", "change-me")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None

cookies = EncryptedCookieManager(prefix=f"{APP_ID}_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()

# ============================================================
# ✅ Hub token source-of-truth (protect against embedded apps)
# ============================================================
def hub_set_tokens(at: str | None, rt: str | None):
    if at is not None:
        st.session_state["_hub_access_token"] = at
        st.session_state["access_token"] = at
    if rt is not None:
        st.session_state["_hub_refresh_token"] = rt
        st.session_state["refresh_token"] = rt

def hub_restore_tokens():
    at = st.session_state.get("_hub_access_token")
    rt = st.session_state.get("_hub_refresh_token")
    if at:
        st.session_state["access_token"] = at
    if rt:
        st.session_state["refresh_token"] = rt

# ============================================================
# ✅ Auth persistence
# ============================================================
def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token"))

def restore_session_from_cookies() -> bool:
    at = (cookies.get("access_token") or "").strip()
    rt = (cookies.get("refresh_token") or "").strip()
    email = (cookies.get("user_email") or "").strip()

    if not at and not rt:
        return False

    if at:
        hub_set_tokens(at, None)
    if rt:
        hub_set_tokens(None, rt)

    if email and not st.session_state.get("user"):
        st.session_state["user"] = {"email": email}

    if supabase and at:
        try:
            res = supabase.auth.get_user(at)
            u = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
            if u:
                st.session_state["user"] = u
        except Exception:
            pass

    return is_logged_in()

def do_logout():
    try:
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
    except Exception:
        pass

    try:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        cookies["user_email"] = ""
        cookies.save()
    except Exception:
        pass

    st.session_state.clear()
    st.session_state["hub_page"] = "home"
    st.rerun()

# ============================================================
# ✅ Common top menu (always 6 buttons)
# ============================================================
def top_menu(active: str | None = None) -> str | None:
    items = [
        ("home", "홈"),
        ("word", "단어"),
        ("kanji", "한자"),
        ("talk", "회화"),
        ("mypage", "마이페이지"),
        ("logout", "로그아웃"),
    ]
    st.markdown('<div class="topmenu-wrap"></div>', unsafe_allow_html=True)
    cols = st.columns(len(items))
    clicked = None
    for i, (key, label) in enumerate(items):
        with cols[i]:
            if st.button(label, key=f"topnav_{key}", use_container_width=True, disabled=(active == key)):
                clicked = key
    return clicked

def handle_menu(clicked: str):
    if clicked == "logout":
        do_logout()
    elif clicked == "home":
        st.session_state["hub_page"] = "home"
        st.rerun()
    elif clicked == "word":
        st.session_state["hub_page"] = "word"
        st.session_state["entry_target"] = "quiz"
        st.rerun()
    elif clicked == "kanji":
        st.session_state["hub_page"] = "kanji"
        st.session_state["entry_target"] = "quiz"
        st.rerun()
    elif clicked == "talk":
        st.session_state["hub_page"] = "talk"
        st.rerun()
    elif clicked == "mypage":
        st.session_state["hub_page"] = "mypage"
        st.rerun()

# ============================================================
# ✅ Embedded original apps (keeps your existing functionality/design)
# ============================================================
# ⚠️ 여기는 "기존 hotena_basic.py / app.py"를 base64로 내장한 것입니다.
# (원본 파일은 레포에 없어도 됩니다 — main.py 하나로 실행되도록 설계)

_WORD_APP_B64 = "REPLACE_WITH_YOUR_EMBEDDED_WORD_B64"
_KANJI_APP_B64 = "REPLACE_WITH_YOUR_EMBEDDED_KANJI_B64"

def exec_embedded_app(src_b64: str, entry: str = "quiz"):
    orig_button = st.button
    orig_set_page_config = st.set_page_config

    # Patch cookie manager inside embedded code (avoid duplicate components; share tokens)
    import streamlit_cookies_manager as scm
    orig_ecm = getattr(scm, "EncryptedCookieManager", None)

    class HubCookies(dict):
        def ready(self) -> bool:
            return True

        def get(self, key, default=None):
            store = st.session_state.setdefault("_hub_cookie_store", {})
            if key in store:
                return store.get(key) or default
            if key in st.session_state:
                return st.session_state.get(key) or default
            return default

        def __setitem__(self, key, value):
            store = st.session_state.setdefault("_hub_cookie_store", {})
            store[key] = value
            if key == "access_token":
                hub_set_tokens(str(value), None)
            if key == "refresh_token":
                hub_set_tokens(None, str(value))
            return dict.__setitem__(self, key, value)

        def save(self):
            return None

    def patched_ecm(*args, **kwargs):
        return HubCookies()

    scm.EncryptedCookieManager = patched_ecm

    # prevent embedded apps from changing shell
    st.set_page_config = lambda *a, **k: None

    # hide duplicate buttons inside embedded apps (mypage/logout + their internal hub buttons)
    HIDE_SUBSTR = (
        "마이페이지", "로그아웃", "로그아웃하기",
        "단어 훈련", "한자 훈련", "회화 훈련",
        "단어훈련", "한자훈련", "회화훈련",
        "My Page", "Logout", "ログアウト", "マイページ",
    )

    def wrapped_button(label, *args, **kwargs):
        try:
            if isinstance(label, str) and any(s in label for s in HIDE_SUBSTR):
                return False
        except Exception:
            pass
        return orig_button(label, *args, **kwargs)

    st.button = wrapped_button

    hub_restore_tokens()

    # Many apps use session_state["page"] for routing – do NOT touch hub_page.
    st.session_state["page"] = entry
    st.session_state["entry_target"] = entry
    st.session_state["quiz_entry"] = True

    try:
        src = base64.b64decode(src_b64.encode("ascii")).decode("utf-8", errors="ignore")
        g = {"__name__": "__main__", "__file__": "<embedded>"}
        exec(compile(src, "<embedded>", "exec"), g, g)
    finally:
        st.button = orig_button
        st.set_page_config = orig_set_page_config
        if orig_ecm is not None:
            scm.EncryptedCookieManager = orig_ecm
        hub_restore_tokens()
        apply_global_styles()

# ============================================================
# ✅ Screens
# ============================================================
def render_login():
    hub_header()
    if not supabase:
        st.error("Supabase 설정이 없습니다. secrets에 SUPABASE_URL / SUPABASE_ANON_KEY를 설정해주세요.")
        return

    st.session_state.setdefault("auth_mode", "login")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("로그인", use_container_width=True):
            st.session_state["auth_mode"] = "login"
    with c2:
        if st.button("회원가입", use_container_width=True):
            st.session_state["auth_mode"] = "signup"

    hr()
    email = st.text_input("이메일", key="auth_email")
    pw = st.text_input("비밀번호", type="password", key="auth_pw")

    if st.session_state["auth_mode"] == "login":
        if st.button("로그인하기", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                session = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)
                user = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
                if not session or not getattr(session, "access_token", None):
                    st.error("로그인에 실패했습니다.")
                    return

                st.session_state["user"] = user or {"email": email}
                hub_set_tokens(session.access_token, session.refresh_token)

                cookies["access_token"] = session.access_token
                cookies["refresh_token"] = session.refresh_token
                cookies["user_email"] = email
                cookies.save()

                st.session_state["hub_page"] = "home"
                st.rerun()
            except Exception as e:
                st.error(f"로그인 오류: {e}")
    else:
        if st.button("회원가입하기", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.success("회원가입 요청이 처리되었습니다. 이메일 인증이 필요한 경우 메일을 확인해주세요.")
            except Exception as e:
                st.error(f"회원가입 오류: {e}")

def render_home():
    hub_header()

    clicked = top_menu(active="home")
    if clicked:
        handle_menu(clicked)
        return

    if st.button("📘 단어 훈련", use_container_width=True):
        st.session_state["hub_page"] = "word"
        st.session_state["entry_target"] = "quiz"
        st.rerun()

    if st.button("✍️ 한자 훈련", use_container_width=True):
        st.session_state["hub_page"] = "kanji"
        st.session_state["entry_target"] = "quiz"
        st.rerun()

    if st.button("🗣 회화 훈련", use_container_width=True):
        st.session_state["hub_page"] = "talk"
        st.rerun()

def render_talk():
    clicked = top_menu(active="talk")
    if clicked:
        handle_menu(clicked)
        return
    slim_header("회화 훈련", "준비중")
    st.info("회화 기능은 준비 중입니다.")

def render_mypage():
    clicked = top_menu(active="mypage")
    if clicked:
        handle_menu(clicked)
        return
    slim_header("마이페이지", "")
    st.info("마이페이지는 준비 중입니다.")

def render_router():
    hub_page = st.session_state.get("hub_page", "home")

    if hub_page == "home":
        render_home()
        return

    clicked = top_menu(active=hub_page)
    if clicked:
        handle_menu(clicked)
        return

    entry = st.session_state.get("entry_target", "quiz")

    if hub_page == "word":
        slim_header("단어 훈련", "")
        exec_embedded_app(_WORD_APP_B64, entry=entry)
        return

    if hub_page == "kanji":
        slim_header("한자 훈련", "")
        exec_embedded_app(_KANJI_APP_B64, entry=entry)
        return

    if hub_page == "talk":
        render_talk()
        return

    if hub_page == "mypage":
        render_mypage()
        return

    st.session_state["hub_page"] = "home"
    st.rerun()

# ============================================================
# ✅ Entry
# ============================================================
try:
    restore_session_from_cookies()
    if not is_logged_in():
        render_login()
    else:
        render_router()
except Exception:
    st.error("예상치 못한 오류가 발생했습니다.")
    st.code(traceback.format_exc())
