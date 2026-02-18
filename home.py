# home.py
from __future__ import annotations

from pathlib import Path
import os
import runpy
import json
import hashlib
import random
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Page Config (Hub only)
# ============================================================
st.set_page_config(page_title="왕초보 탈출 하테나일본어", layout="centered")
st.session_state["_page_config_set"] = True  # children should not call set

# ✅ Hub version
HUB_VERSION = "v23"
# ============================================================
# ✅ 오늘의 말 (공통)
# ============================================================
def render_today_quote():
    quotes = [
        "오늘은 10문제만! 그걸로 충분합니다.",
        "루틴은 작게, 지속은 길게.",
        "정답보다 중요한 건 ‘계속’입니다.",
        "단어가 쌓이면 문장이 열립니다.",
        "오늘의 한 번이 내일의 자신감이에요.",
    ]
    q = random.choice(quotes)
    st.markdown(
        f"""<div style="padding:12px 14px;border:1px solid rgba(49,51,63,.12);border-radius:14px;margin:8px 0 14px 0;">
        <div style="font-weight:900;">오늘의 말</div>
        <div style="margin-top:6px;opacity:.9;">{q}</div>
        </div>""",
        unsafe_allow_html=True,
    )


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
            cookies.save()
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


# ============================================================
# ✅ 10문제 완주 보상/연속학습 (공통)
# - child scripts can call: st.session_state["hub_record_completion"](...)
# ============================================================
def _kst_today() -> date:
    # 서버 TZ와 무관하게 KST 기준으로 계산
    return (datetime.utcnow() + timedelta(hours=9)).date()


def record_completion(mode: str, score: int, quiz_len: int):
    """10문제 세트 완료를 기록하고, streak/오늘 학습량을 업데이트합니다."""
    sb_authed = st.session_state.get("supabase")
    u = st.session_state.get("user")
    if not sb_authed or not u:
        return None

    prog = st.session_state.get("progress_all") or {}
    meta = prog.get("_meta") or {}

    today = _kst_today().isoformat()
    yesterday = (_kst_today() - timedelta(days=1)).isoformat()

    last = str(meta.get("last_study_date") or "")
    streak = int(meta.get("streak") or 0)

    if last != today:
        if last == yesterday:
            streak += 1
        else:
            streak = 1
        meta["last_study_date"] = today
        meta["streak"] = streak
        meta["today_sets"] = 0

    meta["today_sets"] = int(meta.get("today_sets") or 0) + 1
    meta["last_mode"] = mode
    meta["last_score"] = int(score)
    meta["last_quiz_len"] = int(quiz_len)
    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"

    prog["_meta"] = meta
    st.session_state["progress_all"] = prog
    try:
        sb_authed.table("profiles").update({"progress": prog}).eq("id", u.id).execute()
    except Exception:
        pass

    # reward message for UI
    st.session_state["hub_reward"] = {
        "mode": mode,
        "streak": streak,
        "today_sets": int(meta.get("today_sets") or 0),
        "score": int(score),
        "quiz_len": int(quiz_len),
    }
    return st.session_state["hub_reward"]


st.session_state["hub_record_completion"] = record_completion


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
                cookies.save()
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
    # ✅ 페이지 전환 토큰(각 훈련 앱에서 진입 시 상태 초기화에 사용)
    st.session_state["_hub_nav_token"] = str(uuid.uuid4())
    st.session_state["hub_page"] = page
    st.rerun()

def _plan_label() -> str:
    plan = (st.session_state.get("user_plan") or "free").lower()
    return "PRO" if plan == "pro" else "FREE"

def render_top_bar():
    """상단은 '홈으로' + 플랜(공통, 동일 위치)만."""
    plan = _plan_label()
    if st.session_state.get("hub_page") == "home":
        st.markdown("### 왕초보 탈출 하테나일본어")
    else:
        if st.button("← 홈으로", use_container_width=True, key="hub_btn_home_top"):
            go("home")
    st.markdown(
        f"""
<div style="margin:6px 0 12px 0;">
  <span style="display:inline-block;padding:6px 10px;border-radius:999px;
               border:1px solid rgba(49,51,63,.18);
               background:rgba(49,51,63,.04);
               font-weight:700;font-size:13px;">
    플랜: {plan}
  </span>
</div>
""",
        unsafe_allow_html=True,
    )

# ============================================================
# ✅ Hub UI
# ============================================================
render_top_bar()

# ✅ Runner
# ============================================================
def run_script(filename: str):
    path = (BASE_DIR / filename).resolve()
    if not path.exists() or not path.is_file():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()
    # ✅ 자식 앱이 허브 실행 중임을 알 수 있게 표시
    st.session_state["_hub_child"] = filename
    try:
        runpy.run_path(str(path), run_name="__main__")
    finally:
        # 다음 렌더에서 혼선 방지
        st.session_state.pop("_hub_child", None)


def render_guide_block(page: str):
    with st.expander("이용 가이드", expanded=False):
        if page == "word":
            st.markdown("- **단어 훈련**: 한 번에 10문제씩 풀어주세요.")
            st.markdown("- 보기 선택 후 **정답 제출** → 채점 결과 확인.")
        elif page == "kanji":
            st.markdown("- **한자 훈련**: N5~N3 (왕초보용).")
            st.markdown("- 보기 선택 후 **정답 제출** → 채점 결과 확인.")
        elif page == "talk":
            st.markdown("- **회화 훈련**: 상황 + 상대 발화 + 보기 선택.")
            st.markdown("- **발음 듣기(🔊)** 는 PRO에서 제공됩니다.")
        st.markdown("- 홈으로 돌아가려면 상단 **← 홈으로** 버튼을 누르세요.")

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def render_mypage_block(page: str):
    # 페이지별로도 보여주지만, 내용은 '전체 요약' 중심으로 깔끔하게
    with st.expander("마이페이지", expanded=False):
        u = st.session_state.get("user")
        email = getattr(u, "email", "") if u else ""
        plan = _plan_label()
        st.markdown(f"**이메일:** {email}")
        st.markdown(f"**플랜:** {plan}")

        prog = st.session_state.get("progress_all") or {}

        def summarize(key: str):
            d = prog.get(key) or {}
            attempts = _safe_int(d.get("attempts"))
            correct  = _safe_int(d.get("correct"))
            wrong    = _safe_int(d.get("wrong"))
            mastered = d.get("mastered_ids") or d.get("mastered") or []
            wrong_ids = d.get("wrong_ids") or d.get("wrongs") or []
            acc = (correct / attempts * 100.0) if attempts else 0.0
            return {
                "attempts": attempts,
                "correct": correct,
                "wrong": wrong,
                "acc": acc,
                "mastered": len(mastered) if isinstance(mastered, (list, tuple, set)) else 0,
                "wrong_saved": len(wrong_ids) if isinstance(wrong_ids, (list, tuple, set)) else 0,
            }

        w = summarize("word")
        k = summarize("kanji")
        t = summarize("talk")

        st.markdown("#### 학습 요약")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**단어**")
            st.metric("정답률", f"{w['acc']:.0f}%")
            st.caption(f"시도 {w['attempts']} · 정답 {w['correct']} · 오답 {w['wrong']}")
            st.caption(f"정복 {w['mastered']} · 오답저장 {w['wrong_saved']}")
        with c2:
            st.markdown("**한자**")
            st.metric("정답률", f"{k['acc']:.0f}%")
            st.caption(f"시도 {k['attempts']} · 정답 {k['correct']} · 오답 {k['wrong']}")
            st.caption(f"정복 {k['mastered']} · 오답저장 {k['wrong_saved']}")
        with c3:
            st.markdown("**회화**")
            st.metric("정답률", f"{t['acc']:.0f}%")
            st.caption(f"시도 {t['attempts']} · 정답 {t['correct']} · 오답 {t['wrong']}")
            st.caption(f"정복 {t['mastered']} · 오답저장 {t['wrong_saved']}")


        # ----------------------------
        # ✅ 최근 7일 학습(간단 그래프)
        # - quiz_attempts 테이블이 있으면 일자별 시도/정답률을 보여줍니다.
        # - 없거나 권한/컬럼 문제가 있으면 조용히 스킵합니다.
        # ----------------------------
        try:
            sb = st.session_state.get("supabase")
            u2 = st.session_state.get("user")
            uid = getattr(u2, "id", None) if u2 else None
            if sb and uid:
                since = (datetime.utcnow() - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
                resp = (
                    sb.table("quiz_attempts")
                      .select("created_at,score,quiz_len,level")
                      .eq("user_id", uid)
                      .gte("created_at", since)
                      .order("created_at", desc=False)
                      .execute()
                )
                rows = getattr(resp, "data", None) or []
                if rows:
                    df7 = pd.DataFrame(rows)
                    df7["created_at"] = pd.to_datetime(df7["created_at"], errors="coerce", utc=True)
                    df7 = df7.dropna(subset=["created_at"])
                    df7["date"] = df7["created_at"].dt.tz_convert("Asia/Seoul").dt.date.astype(str)

                    # 숫자 안전 변환
                    for c in ["score", "quiz_len"]:
                        if c in df7.columns:
                            df7[c] = pd.to_numeric(df7[c], errors="coerce").fillna(0).astype(int)
                        else:
                            df7[c] = 0

                    g = df7.groupby("date", as_index=False).agg(
                        quizzes=("date", "count"),
                        correct=("score", "sum"),
                        total=("quiz_len", "sum"),
                    )
                    g["acc"] = g.apply(lambda r: (r["correct"] / r["total"] * 100.0) if r["total"] else 0.0, axis=1)

                    # 최근 7일 빈 날짜 채우기
                    today = date.today()
                    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
                    base = pd.DataFrame({"date": [d.isoformat() for d in dates]})
                    g = base.merge(g, on="date", how="left").fillna(0)
                    g["quizzes"] = g["quizzes"].astype(int)
                    g["acc"] = g["acc"].astype(float)

                    st.markdown("#### 최근 7일")
                    st.caption("일자별 ‘세트(퀴즈) 시도 횟수’와 ‘정답률(%)’입니다.")
                    st.bar_chart(g.set_index("date")["quizzes"])
                    st.line_chart(g.set_index("date")["acc"])
        except Exception:
            pass

        st.divider()
        st.markdown("#### 상세 기록")

        # 최근 기록 테이블(가능하면 quiz_attempts에서)
        try:
            sb = st.session_state.get("supabase")
            u2 = st.session_state.get("user")
            uid = getattr(u2, "id", None) if u2 else None
            if sb and uid:
                resp2 = (
                    sb.table("quiz_attempts")
                      .select("created_at,score,quiz_len,level,pos_mode")
                      .eq("user_id", uid)
                      .order("created_at", desc=True)
                      .limit(30)
                      .execute()
                )
                rows2 = getattr(resp2, "data", None) or []
                if rows2:
                    df = pd.DataFrame(rows2)
                    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
                    df = df.dropna(subset=["created_at"])
                    df["날짜"] = df["created_at"].dt.tz_convert("Asia/Seoul").dt.strftime("%m-%d %H:%M")
                    df["훈련"] = df.get("level").astype(str)
                    # 단어/한자/회화 구분이 pos_mode/level에 섞여 있을 수 있어, 안전하게 가공
                    if "pos_mode" in df.columns:
                        df["모드"] = df["pos_mode"].astype(str)
                    else:
                        df["모드"] = ""
                    df["점수"] = pd.to_numeric(df.get("score"), errors="coerce").fillna(0).astype(int)
                    df["문항"] = pd.to_numeric(df.get("quiz_len"), errors="coerce").fillna(0).astype(int)
                    show = df[["날짜", "훈련", "모드", "점수", "문항"]].copy()
                    with st.expander("최근 30개 기록 보기", expanded=False):
                        st.dataframe(show, use_container_width=True, hide_index=True)
                else:
                    st.caption("최근 기록이 아직 없습니다.")
        except Exception:
            st.caption("최근 기록을 불러오지 못했습니다.")

        # 원본은 관리자 전용으로 숨김
        if bool(st.session_state.get("is_admin")):
            with st.expander("(관리자) 원본 progress JSON", expanded=False):
                st.json(prog)


page = st.session_state.get("hub_page", "home")

if page == "home":
    # ✅ 정체성 강화: 홈 메시지 + 오늘의 말 + 오늘 목표
    st.markdown("# 왕초보 탈출 하테나일본어")
    st.caption("오늘도 **10문제만**. 작은 루틴이 실력을 만듭니다.")
    render_today_quote()

    # ✅ 보상/연속학습 배너
    reward = st.session_state.pop("hub_reward", None)
    if reward:
        st.balloons()
        st.success(
            f"10문제 완주! (점수 {reward['score']}/{reward['quiz_len']}) · 연속 {reward['streak']}일 · 오늘 {reward['today_sets']}세트",
            icon="🎉",
        )

    meta = (st.session_state.get("progress_all") or {}).get("_meta") or {}
    streak = int(meta.get("streak") or 0)
    today_sets = int(meta.get("today_sets") or 0)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("연속 학습", f"{streak}일")
    with c2:
        st.metric("오늘 완료", f"{today_sets}세트")

    st.markdown("## 훈련 선택")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("단어 훈련", use_container_width=True, key="hub_btn_word"):
            go("word")
    with b2:
        if st.button("한자 훈련", use_container_width=True, key="hub_btn_kanji"):
            go("kanji")
    with b3:
        if st.button("회화 훈련", use_container_width=True, key="hub_btn_talk"):
            go("talk")

    st.divider()
    st.caption(f"로그인: {getattr(user, 'email', '')}")

else:
    # 허브 공통 헤더가 렌더링됨(각 훈련 스크립트는 page_config/상단메뉴를 최소화)
    st.session_state["_hub_common_header"] = True

    render_guide_block(page)
    render_mypage_block(page)
    st.divider()

    st.session_state["hub_mode"] = True
    st.session_state["page"] = "quiz"  # 단어/한자: 바로 시험으로

    if page == "word":
        run_script("hotena_basic.py")
    elif page == "kanji":
        run_script("app.py")
    elif page == "talk":
        run_script("talk.py")
    else:
        st.info("원하는 훈련을 선택하세요.")
