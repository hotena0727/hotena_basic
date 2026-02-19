# home.py
from __future__ import annotations

from pathlib import Path
import os
import runpy
import json
import hashlib
from datetime import date, datetime

import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Page Config (Hub only)
# ============================================================
st.set_page_config(page_title="Hatena Hub", layout="centered")

# ✅ CSS reset (child pages may hide Streamlit header; keep top UI from being clipped)
st.markdown(
    """
<style>
header[data-testid="stHeader"]{ height: 3rem !important; }
div[data-testid="stAppViewContainer"] .block-container{ padding-top: 2.2rem !important; }
</style>
""",
    unsafe_allow_html=True,
)
st.session_state["_page_config_set"] = True  # children should not call set_page_config

BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# ✅ Config helper (env -> secrets)
# ============================================================
def get_cfg(key: str) -> str:
    v = os.getenv(key)
    if v:
        return v
    try:
        return st.secrets[key]
    except Exception:
        return ""

CFG = {
    "COOKIE_PASSWORD": get_cfg("COOKIE_PASSWORD"),
    "SUPABASE_URL": get_cfg("SUPABASE_URL"),
    "SUPABASE_ANON_KEY": get_cfg("SUPABASE_ANON_KEY"),
}
st.session_state["cfg"] = CFG

missing = [k for k, v in CFG.items() if not v]
if missing:
    st.error(f"설정값이 없습니다: {', '.join(missing)} (Cloud Run env 또는 Streamlit secrets 확인)")
    st.stop()

# ============================================================
# ✅ Cookies (MUST be created only once per app run)
# ============================================================
cookies = st.session_state.get("cookies")
if cookies is None:
    cookies = EncryptedCookieManager(prefix="hotena_beginner_", password=CFG["COOKIE_PASSWORD"])
    if not cookies.ready():
        st.info("잠깐만요! 곧 시작할게요🙂")
        st.stop()
    st.session_state["cookies"] = cookies

# ✅ 쿠키 컴포넌트는 같은 run에서 같은 key로 두 번 렌더링되면
#    StreamlitDuplicateElementKey가 발생할 수 있습니다.
#    (특히 cookies.save()를 한 run 안에서 여러 번 호출할 때)
#    따라서 '이번 run에서 save는 1번만' 보장합니다.
st.session_state["_cookie_save_lock"] = False

def _cookies_save_once_per_run():
    if st.session_state.get("_cookie_save_lock"):
        return
    st.session_state["_cookie_save_lock"] = True
    try:
        cookies.save()
    except Exception:
        # 쿠키 저장 실패는 치명적이지 않으므로 조용히 무시
        pass

# ============================================================
# ✅ Supabase client (anon)
# ============================================================
sb = st.session_state.get("sb")
if sb is None:
    sb = create_client(CFG["SUPABASE_URL"], CFG["SUPABASE_ANON_KEY"])
    st.session_state["sb"] = sb

# ============================================================
# ✅ Auth helpers (restore from cookies + authed client)
# ============================================================
def refresh_session_from_cookie_if_needed(force: bool = False) -> bool:
    if not force and st.session_state.get("user") and st.session_state.get("access_token"):
        return True

    rt = cookies.get("refresh_token")
    at = cookies.get("access_token")

    if rt:
        refreshed = None
        try:
            refreshed = sb.auth.refresh_session(rt)
        except Exception:
            try:
                refreshed = sb.auth.refresh_session({"refresh_token": rt})
            except Exception:
                refreshed = None

        if refreshed and getattr(refreshed, "session", None) and getattr(refreshed.session, "access_token", None):
            st.session_state["user"] = refreshed.user
            st.session_state["access_token"] = refreshed.session.access_token
            st.session_state["refresh_token"] = refreshed.session.refresh_token
            cookies["access_token"] = refreshed.session.access_token
            cookies["refresh_token"] = refreshed.session.refresh_token
            _cookies_save_once_per_run()
            return True

    if at:
        try:
            u = sb.auth.get_user(at)
            user_obj = getattr(u, "user", None) or getattr(u, "data", None)
            if user_obj:
                st.session_state["user"] = user_obj
                st.session_state["access_token"] = at
                if rt:
                    st.session_state["refresh_token"] = rt
                return True
        except Exception:
            pass

    return False


def get_authed_sb():
    refresh_session_from_cookie_if_needed(force=True)
    token = st.session_state.get("access_token")
    if not token:
        return None
    cached = st.session_state.get("sb_authed")
    cached_token = st.session_state.get("sb_authed_token")
    if cached is not None and cached_token == token:
        return cached
    sb2 = create_client(CFG["SUPABASE_URL"], CFG["SUPABASE_ANON_KEY"])
    sb2.postgrest.auth(token)
    st.session_state["sb_authed"] = sb2
    st.session_state["sb_authed_token"] = token
    return sb2


def ensure_profile(sb_authed, user):
    try:
        sb_authed.table("profiles").upsert(
            {"id": user.id, "email": getattr(user, "email", None)},
            on_conflict="id",
        ).execute()
    except Exception:
        pass


def load_profile(sb_authed, user_id: str):
    try:
        res = sb_authed.table("profiles").select("progress, plan, is_admin").eq("id", user_id).single().execute()
        data = res.data if res and res.data else {}
        progress = data.get("progress") or {}
        plan = data.get("plan") or "free"
        is_admin = bool(data.get("is_admin")) if "is_admin" in data else False
        st.session_state["progress_all"] = progress
        st.session_state["user_plan"] = plan
        st.session_state["is_admin"] = is_admin
    except Exception:
        st.session_state["progress_all"] = st.session_state.get("progress_all", {}) or {}
        st.session_state["user_plan"] = st.session_state.get("user_plan", "free")


def save_progress(sb_authed, user_id: str, progress: dict):
    try:
        sb_authed.table("profiles").update({"progress": progress}).eq("id", user_id).execute()
    except Exception:
        pass


def daily_message(user_id: str) -> str:
    messages = st.session_state.get("REMINDER_MESSAGES", [])
    if not messages:
        return "오늘도 5분만, 시작해볼까요?"
    seed = f"{user_id}:{date.today().isoformat()}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(messages)
    return messages[idx]


# ============================================================
# 🔔 Reminder messages (혼합 50)
# ============================================================
REMINDER_MESSAGES = [
  "오늘도 5분만, 시작해볼까요?",
  "딱 한 문제만 풀면, 흐름이 살아나요.",
  "어제보다 1%만 앞으로 가면 됩니다.",
  "완벽 말고, 실행. 오늘도 한 걸음!",
  "지금 시작하면, 오늘은 이긴 겁니다.",
  "짧아도 괜찮아요. 루틴만 지켜요.",
  "단어 10개면 충분합니다. 가볍게 가요.",
  "한자 1개만 써도, 실력은 쌓입니다.",
  "회화는 30초만 말해도 효과 있어요.",
  "오늘의 목표: ‘안 끊기기’",
  "시작이 전부예요. 딱 지금!",
  "지금 한 번만 열어도, 내일이 쉬워져요.",
  "오늘의 승리는 ‘접속’입니다.",
  "부담 0, 실행 1.",
  "틀려도 괜찮아요. 맞힐 때까지 가요.",
  "오늘 한 번만 하면, 내일 덜 힘들어요.",
  "지금 2분만 투자해요.",
  "오늘은 ‘가볍게 시작’이 정답.",
  "내일의 내가 고마워할 선택: 지금 시작하기",
  "문제 한 개로도 충분히 공부입니다.",
  "오늘도 한 번 열면, 이미 반은 했어요.",
  "무리하지 말고, 멈추지만 말자.",
  "딱 한 세트만. 그 다음은 보너스.",
  "오늘은 복습만 해도 충분합니다.",
  "오늘의 목표: ‘0을 1로 만들기’",
  "기세는 ‘첫 클릭’에서 나옵니다.",
  "지금은 준비운동. 가볍게!",
  "꾸준함이 결국 실력입니다.",
  "오늘은 단어, 내일은 한자. 번갈아도 좋아요.",
  "오늘의 승부는 ‘시작 버튼’입니다.",
  "오늘은 내 페이스로.",
  "지금 시작하면, 뇌가 깨어나요.",
  "작은 성취가 큰 자신감을 만듭니다.",
  "어제 쉬었어도 괜찮아요. 오늘 다시!",
  "길게 말고, 짧게라도 꾸준히!",
  "손풀기 1문제만 하고 끝내도 OK.",
  "오늘의 미션: ‘새 문제’ 눌러보기",
  "오늘도 연결해 둡시다.",
  "지금의 한 문제는 미래의 자신을 돕습니다.",
  "오늘은 ‘짧게라도 끝내기’",
  "지금 한 번만, 진짜로.",
  "공부는 기분이 아니라 습관.",
  "오늘은 ‘듣기’ 한 번만 해도 좋아요.",
  "오늘은 ‘읽기’ 한 줄만 읽어도 됩니다.",
  "오늘의 목표: ‘시작하고 종료하기’",
  "지금은 연습 시간. 실수해도 괜찮아요.",
  "딱 한 번만 열어봅시다.",
  "오늘도 한 번만!",
  "시작하면 끝은 따라옵니다.",
]
st.session_state["REMINDER_MESSAGES"] = REMINDER_MESSAGES

# ============================================================
# ✅ UI: Login (single)
# ============================================================
refresh_session_from_cookie_if_needed(force=False)

user = st.session_state.get("user")
sb_authed = st.session_state.get("sb_authed")

if not user:
    st.subheader("로그인")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("이메일", key="hub_email")
        pw = st.text_input("비밀번호", type="password", key="hub_pw")
        mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True)
        submit = st.form_submit_button("확인", use_container_width=True)

    if submit:
        if not email or not pw:
            st.error("이메일/비밀번호를 입력해 주세요.")
            st.stop()
        try:
            if mode == "로그인":
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
            else:
                res = sb.auth.sign_up({"email": email, "password": pw})

            if getattr(res, "session", None) and getattr(res.session, "access_token", None):
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                st.session_state["refresh_token"] = res.session.refresh_token
                cookies["access_token"] = res.session.access_token
                cookies["refresh_token"] = res.session.refresh_token
                _cookies_save_once_per_run()
                st.success("로그인 완료!")
                st.rerun()
            else:
                st.warning("이메일 인증이 필요할 수 있습니다. (Supabase 설정에 따라 다름)")
        except Exception as e:
            st.error("로그인/가입 실패")
            st.code(str(e))
    st.stop()

# logged in
sb_authed = get_authed_sb()
user = st.session_state.get("user")
ensure_profile(sb_authed, user)
load_profile(sb_authed, user.id)

# ============================================================
# 🔔 Reminder settings (stored in profiles.progress.reminder)
# ============================================================
progress_all = st.session_state.get("progress_all", {}) or {}
rem = progress_all.get("reminder") or {}
enabled = bool(rem.get("enabled", True))
time_str = rem.get("time", "09:00")

with st.expander("🔔 홈 알림 설정", expanded=False):
    c1, c2 = st.columns([1,1])
    with c1:
        enabled = st.toggle("알림 사용", value=enabled, key="hub_rem_enabled")
    with c2:
        time_str = st.text_input("알림 시간(HH:MM)", value=time_str, key="hub_rem_time")
    if st.button("저장", use_container_width=True, key="hub_rem_save"):
        # basic validate
        try:
            hh, mm = [int(x) for x in time_str.split(":")]
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            st.error("시간 형식이 올바르지 않습니다. 예) 09:00")
            st.stop()
        progress_all["reminder"] = {"enabled": bool(enabled), "time": f"{hh:02d}:{mm:02d}"}
        st.session_state["progress_all"] = progress_all
        save_progress(sb_authed, user.id, progress_all)
        st.success("저장했습니다.")

# Fire in-app notification when app is open
if enabled:
    try:
        hh, mm = [int(x) for x in time_str.split(":")]
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target = target.replace(day=now.day)  # same day; if passed, schedule for next day
            target = target + (datetime(now.year, now.month, now.day) - datetime(now.year, now.month, now.day))  # no-op
        delay_ms = max(1000, int((target - now).total_seconds() * 1000))
    except Exception:
        delay_ms = 0

    msg = json.dumps(daily_message(str(user.id)))
    components.html(f"""
<script>
(async () => {{
  try {{
    if (!("Notification" in window)) return;
    if (Notification.permission !== "granted") {{
      await Notification.requestPermission();
    }}
    const delay = {delay_ms};
    const fire = () => {{
      if (Notification.permission === "granted") {{
        new Notification("하테나 일본어", {{ body: {msg} }});
      }}
    }};
    if (delay > 0) setTimeout(fire, delay);
  }} catch(e) {{}}
}})();
</script>
""", height=0)

# ============================================================
# ✅ Navigation (hub_page)
# ============================================================
if "hub_page" not in st.session_state:
    st.session_state["hub_page"] = "home"

def go(page: str):
    st.session_state["hub_page"] = page
    st.rerun()

def hub_logout():
    cookies["access_token"] = ""
    cookies["refresh_token"] = ""
    _cookies_save_once_per_run()
    for k in ["user","access_token","refresh_token","sb_authed","sb_authed_token","progress_all","hub_page","HUB_MODE"]:
        st.session_state.pop(k, None)
    st.rerun()

def render_top_menu():
    # ✅ 항상 같은 상단 메뉴(사이드바 없이)
    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,1], vertical_alignment="center")

    with c1:
        st.button("홈", use_container_width=True, key="hub_nav_home", on_click=go, args=("home",))
    with c2:
        st.button("단어", use_container_width=True, key="hub_nav_word", on_click=go, args=("word",))
    with c3:
        st.button("한자", use_container_width=True, key="hub_nav_kanji", on_click=go, args=("kanji",))
    with c4:
        st.button("회화", use_container_width=True, key="hub_nav_talk", on_click=go, args=("talk",))
    with c5:
        st.button("마이페이지", use_container_width=True, key="hub_nav_my", on_click=go, args=("my",))
    with c6:
        st.button("로그아웃", use_container_width=True, key="hub_nav_logout", on_click=hub_logout)

    st.divider()

render_top_menu()

# ============================================================
# ✅ Runner

# ============================================================
def run_script(filename: str):
    path = (BASE_DIR / filename).resolve()
    if not path.exists() or not path.is_file():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()
    # ✅ Hub mode flag so child scripts can adjust UI/CSS
    st.session_state["HUB_MODE"] = True
    runpy.run_path(str(path), run_name="__main__")

page = st.session_state.get("hub_page", "home")

if page == "home":
    st.caption(f"로그인: {getattr(user, 'email', '')}")
    st.info("상단 메뉴에서 원하는 항목을 선택하세요.")

elif page == "my":
    # ✅ 마이페이지는 "한자 훈련(app.py)"에 있던 대시보드 UI/기능을 그대로 재사용합니다.
    # - HUB 상단 메뉴는 home.py가 담당
    # - app.py의 render_my_dashboard() 디자인/기능을 그대로 보여줌
    st.session_state["page"] = "my"
    run_script(Path(__file__).parent / "app.py")
    st.stop()

elif page == "word":
    st.session_state["HUB_MODE"] = True
    run_script("hotena_basic.py")
elif page == "kanji":
    st.session_state["HUB_MODE"] = True
    run_script("app.py")
elif page == "talk":
    st.session_state["HUB_MODE"] = True
    run_script("talk.py")
else:
    st.info("상단 메뉴에서 원하는 항목을 선택하세요.")
