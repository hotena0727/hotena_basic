from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, date
import hashlib
import json
import runpy

import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Home (single shared login + router)
# - Buttons: words / kanji / talk
# - Single login handled here
# - Global reminder (in-tab notification) handled here
# ============================================================

st.set_page_config(page_title="Hatena", layout="centered")
st.session_state["_page_config_set"] = True

# ============================================================
# 🔐 Supabase + Cookies
# ============================================================

COOKIE_PREFIX = "hotena_beginner_"
cookies = EncryptedCookieManager(prefix=COOKIE_PREFIX, password=st.secrets.get("COOKIE_PASSWORD", "change-me"))
if not cookies.ready():
    st.stop()

SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("SUPABASE_URL / SUPABASE_ANON_KEY 가 설정되어 있지 않습니다. Streamlit secrets를 확인해 주세요.")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================================
# 🔔 Mixed reminder messages (50) + daily stable pick
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
  "시작이 반이 아니라, 시작이 전부예요.",
  "지금 한 번만 열어도, 내일이 쉬워져요.",
  "몸이 아니라 ‘손’이 먼저 움직이면 됩니다.",
  "오늘의 승리는 ‘접속’입니다.",
  "부담 0, 실행 1.",
  "하루 5분이 30일이면 150분이에요.",
  "공부는 기분이 아니라, 습관이에요.",
  "오늘은 ‘복습’만 해도 충분합니다.",
  "틀려도 괜찮아요. 맞힐 때까지 가요.",
  "지금의 한 문제는 미래의 자신을 돕습니다.",
  "오늘 한 번만 하면, 내일 덜 힘들어요.",
  "길게 말고, 짧게라도 꾸준히!",
  "손풀기 1문제만 하고 끝내도 OK.",
  "오늘은 ‘듣기’ 한 번만 해도 좋아요.",
  "오늘은 ‘읽기’ 한 줄만 읽어도 됩니다.",
  "오늘의 미션: ‘새 문제’ 눌러보기",
  "지금 시작하면, 뇌가 깨어나요.",
  "작은 성취가 큰 자신감을 만듭니다.",
  "어제 쉬었어도 괜찮아요. 오늘 다시!",
  "오늘은 ‘내 페이스’로 가요.",
  "꾸준함이 결국 실력입니다.",
  "한 번이라도 하면, 루틴이 살아납니다.",
  "오늘의 목표: ‘0을 1로 만들기’",
  "문제 한 개로도 충분히 공부입니다.",
  "지금 2분만 투자해요.",
  "오늘은 ‘가볍게 시작’이 정답.",
  "내일의 내가 고마워할 선택: 지금 시작하기",
  "공부는 길게가 아니라, 자주가 이깁니다.",
  "지금은 연습 시간. 실수해도 괜찮아요.",
  "오늘도 연결해 둡시다. 끊기지만 않으면 돼요.",
  "딱 한 세트만. 그 다음은 보너스.",
  "오늘은 단어, 내일은 한자. 번갈아도 좋아요.",
  "오늘의 승부는 ‘시작 버튼’입니다.",
  "기세는 ‘첫 클릭’에서 나옵니다.",
  "오늘도 한 번 열면, 이미 반은 했어요.",
  "지금은 준비운동. 가볍게!",
  "무리하지 말고, 멈추지만 말자.",
  "하루 한 번, 공부의 방향만 확인해요.",
  "오늘의 목표: ‘짧게라도 끝내기’",
]

def _pick_daily_message(user_id: str) -> str:
    seed = f"{user_id}:{date.today().isoformat()}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(h[:8], 16) % len(REMINDER_MESSAGES)
    return REMINDER_MESSAGES[idx]

# ============================================================
# 🧠 Progress helpers (namespaced)
# ============================================================

def _safe_dict(x):
    return x if isinstance(x, dict) else {}

def load_profile(user_id: str) -> dict:
    try:
        res = sb.table("profiles").select("progress, is_admin").eq("id", user_id).single().execute()
        data = res.data or {}
        progress = _safe_dict(data.get("progress"))
        is_admin = bool(data.get("is_admin", False))
        return {"progress": progress, "is_admin": is_admin}
    except Exception:
        return {"progress": {}, "is_admin": False}

def save_progress(user_id: str, progress: dict):
    sb.table("profiles").update({"progress": progress}).eq("id", user_id).execute()

# ============================================================
# 🔐 Session restore from cookies
# ============================================================

def restore_session_from_cookies() -> bool:
    access = cookies.get("access_token")
    refresh = cookies.get("refresh_token")
    if not access or not refresh:
        return False
    try:
        sb.auth.set_session(access, refresh)
        u = sb.auth.get_user()
        if getattr(u, "user", None) is None:
            return False
        st.session_state["user"] = u.user
        st.session_state["access_token"] = access
        st.session_state["refresh_token"] = refresh
        return True
    except Exception:
        return False

def persist_tokens(session):
    try:
        cookies["access_token"] = session.access_token
        cookies["refresh_token"] = session.refresh_token
        cookies.save()
    except Exception:
        pass

# ============================================================
# 🔐 Login UI (single)
# ============================================================

def render_login():
    st.title("하테나 일본어")
    st.caption("로그인 후 단어/한자/회화 훈련을 이용할 수 있어요.")

    # Try restore
    if restore_session_from_cookies():
        st.success("세션을 복원했습니다.")
        st.rerun()

    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        email = st.text_input("이메일", key="login_email")
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", use_container_width=True):
            try:
                res = sb.auth.sign_in_with_password({"email": email.strip(), "password": pw})
                if not res or not getattr(res, "session", None):
                    st.error("로그인 실패: 이메일/비밀번호 또는 이메일 인증 상태를 확인해주세요.")
                    st.stop()
                st.session_state["user"] = res.user
                st.session_state["access_token"] = res.session.access_token
                st.session_state["refresh_token"] = res.session.refresh_token
                persist_tokens(res.session)
                st.success("로그인 완료!")
                st.rerun()
            except Exception as e:
                st.error("로그인 실패:")
                st.exception(e)

    with tab2:
        email = st.text_input("이메일", key="signup_email")
        pw = st.text_input("비밀번호(8자 이상)", type="password", key="signup_pw")
        if st.button("회원가입", use_container_width=True):
            try:
                sb.auth.sign_up({"email": email.strip(), "password": pw})
                st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요. 메일함을 확인한 뒤 로그인해 주세요.")
            except Exception as e:
                st.error("회원가입 실패:")
                st.exception(e)

# ============================================================
# 🧭 Router
# ============================================================

def go(page: str):
    st.session_state["page"] = page
    st.rerun()

def run_script(filename: str):
    path = (BASE_DIR / filename).resolve()

    if not path.exists():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.caption("✅ 확인: home.py와 hotena_basic.py / app.py / talk.py가 '같은 폴더'에 있어야 합니다.")
        st.caption(f"현재 BASE_DIR: {BASE_DIR}")
        st.caption("BASE_DIR 안의 파일 목록:")
        st.code("\n".join(sorted([p.name for p in BASE_DIR.glob('*')])) or "(비어있음)")
        st.stop()

    # ✅ 실행
    runpy.run_path(str(path), run_name="__main__")

# ============================================================
# 🔔 Global reminder UI + in-tab scheduling
# ============================================================

def reminder_ui(user_id: str, progress: dict):
    st.markdown("---")
    st.subheader("🔔 오늘도 공부 알림 (가볍게)")

    reminder = _safe_dict(progress.get("reminder"))
    enabled_default = bool(reminder.get("enabled", False))
    time_default = str(reminder.get("time", "21:00"))

    try:
        t_def = datetime.strptime(time_default, "%H:%M").time()
    except Exception:
        t_def = datetime.strptime("21:00", "%H:%M").time()

    enabled = st.toggle("알림 사용", value=enabled_default)
    remind_time = st.time_input("알림 시간", value=t_def)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("알림 설정 저장", use_container_width=True):
            progress["reminder"] = {
                "enabled": enabled,
                "time": remind_time.strftime("%H:%M"),
                "updated_at": datetime.now().isoformat(),
            }
            save_progress(user_id, progress)
            st.success("저장되었습니다.")
            st.rerun()

    with c2:
        components.html("""
        <script>
        async function reqPerm(){
          if (!("Notification" in window)) { alert("이 브라우저는 알림을 지원하지 않습니다."); return; }
          const p = await Notification.requestPermission();
          alert("알림 권한: " + p);
        }
        window.reqPerm = reqPerm;
        </script>
        <button onclick="reqPerm()" style="padding:10px 12px;border-radius:12px;width:100%;">
          알림 권한 허용
        </button>
        """, height=60)

def schedule_in_tab_notification(user_id: str, progress: dict):
    reminder = _safe_dict(progress.get("reminder"))
    if not reminder.get("enabled"):
        return

    time_str = str(reminder.get("time", "21:00"))
    try:
        hh, mm = map(int, time_str.split(":"))
    except Exception:
        hh, mm = 21, 0

    now = datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    delay_ms = int((target - now).total_seconds() * 1000)

    daily_msg = _pick_daily_message(user_id)
    body_js = json.dumps(daily_msg, ensure_ascii=False)

    # prevent re-scheduling too often (per day)
    stamp = f"{date.today().isoformat()}_{hh:02d}{mm:02d}"
    if st.session_state.get("_reminder_scheduled") == stamp:
        return
    st.session_state["_reminder_scheduled"] = stamp

    components.html(f"""
    <script>
      const delay = {delay_ms};
      function fireNotif() {{
        if (!("Notification" in window)) return;
        if (Notification.permission === "granted") {{
          new Notification("하테나 일본어", {{ body: {body_js} }});
        }}
      }}
      setTimeout(fireNotif, delay);
    </script>
    """, height=0)

# ============================================================
# ✅ Main
# ============================================================

if "user" not in st.session_state:
    render_login()
    st.stop()

user = st.session_state["user"]
user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)
if not user_id:
    st.error("로그인 사용자 정보를 확인할 수 없습니다. 다시 로그인해 주세요.")
    st.session_state.pop("user", None)
    st.stop()

profile = load_profile(str(user_id))
progress_all = _safe_dict(profile.get("progress"))
st.session_state["progress_all"] = progress_all
st.session_state["is_admin"] = profile.get("is_admin", False)

# schedule notification silently
schedule_in_tab_notification(str(user_id), progress_all)

page = st.session_state.get("page", "home")

if page == "home":
    st.title("훈련 선택")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("단어 훈련", use_container_width=True):
            go("word")
    with c2:
        if st.button("한자 훈련", use_container_width=True):
            go("kanji")
    with c3:
        if st.button("회화 훈련", use_container_width=True):
            go("talk")

    reminder_ui(str(user_id), progress_all)

elif page == "word":
    if st.button("← 홈으로", use_container_width=True):
        go("home")
    run_script("hotena_basic.py")

elif page == "kanji":
    if st.button("← 홈으로", use_container_width=True):
        go("home")
    run_script("app.py")

elif page == "talk":
    if st.button("← 홈으로", use_container_width=True):
        go("home")
    run_script("talk.py")
