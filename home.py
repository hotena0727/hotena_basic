# home.py
from __future__ import annotations

from pathlib import Path
import os
import runpy
import json
import hashlib
from datetime import date, datetime, timedelta, timezone
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Page Config (Hub only)
# ============================================================
st.set_page_config(page_title="Hotena Hub", layout="centered")

# ✅ CSS reset (child pages may hide Streamlit header; keep top UI from being clipped)
st.markdown(
    """
<style>
/* ==========================================================
   ✅ HUB Global CSS (Mobile-first polish)
   - Keep header visible (child pages may hide)
   - Make tap targets big enough
   - Normalize spacing/typography for "app-like" feel
   ========================================================== */

header[data-testid="stHeader"]{
  height: auto !important;
  min-height: 3.25rem !important;
}

/* Container spacing */
div[data-testid="stAppViewContainer"] .block-container{
  padding-top: 0.25rem !important;
  padding-bottom: 5.25rem !important; /* bottom breathing room for mobile */
}

/* Headlines: tighter */
div[data-testid="stAppViewContainer"] h1,
div[data-testid="stAppViewContainer"] h2{
  margin-top: 0.15rem !important;
  margin-bottom: 0.55rem !important;
}

/* Defensive: if a child adds negative margins / weird offsets */
div[data-testid="stAppViewContainer"] .main,
div[data-testid="stAppViewContainer"]{
  margin-top: 0 !important;
}

/* Tighten very top whitespace */
.block-container > div:first-child { margin-top: 0 !important; }

/* Buttons: minimum tap size + readable text */
div[data-testid="stAppViewContainer"] .stButton > button,
div[data-testid="stAppViewContainer"] button[kind]{
  min-height: 44px !important;
  padding-top: 0.55rem !important;
  padding-bottom: 0.55rem !important;
  font-size: 16px !important;
  border-radius: 12px !important;
}

/* Inputs: readable */
div[data-testid="stAppViewContainer"] input,
div[data-testid="stAppViewContainer"] textarea{
  font-size: 16px !important; /* prevent iOS zoom */
}

/* Selectbox / multiselect */
div[data-testid="stAppViewContainer"] div[role="combobox"]{
  min-height: 44px !important;
}

/* Radio/checkbox label spacing: thumb friendly */
div[data-testid="stAppViewContainer"] div[role="radiogroup"] label,
div[data-testid="stAppViewContainer"] label[data-baseweb="checkbox"]{
  padding: 0.35rem 0.25rem !important;
}

/* Expander: make summary easier to tap */
div[data-testid="stExpander"] summary{
  padding-top: 0.35rem !important;
  padding-bottom: 0.35rem !important;
}

/* Card-like blocks (metrics/containers) slightly tighter */
div[data-testid="stMetric"]{
  padding: 0.15rem 0 !important;
}

/* Mobile-only tuning */
@media (max-width: 640px){
  div[data-testid="stAppViewContainer"] .block-container{
    padding-left: 1.0rem !important;
    padding-right: 1.0rem !important;
    padding-top: 0.15rem !important;
    padding-bottom: 6.0rem !important;
  }

  /* Slightly larger tap targets on phones */
  div[data-testid="stAppViewContainer"] .stButton > button,
  div[data-testid="stAppViewContainer"] button[kind]{
    min-height: 48px !important;
    font-size: 16px !important;
    border-radius: 14px !important;
  }
}
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

# ✅ 첫 로드에서 쿠키 기반 자동 로그인 복원(메뉴 링크는 전체 리로드이므로 필수)
refresh_session_from_cookie_if_needed(force=True)


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

    def _norm_token(v):
        # cookies가 dict/json 형태로 저장된 적이 있으면 복원
        try:
            if isinstance(v, str) and v.strip().startswith("{") and v.strip().endswith("}"):
                return json.loads(v)
        except Exception:
            pass
        return v

    rt = _norm_token(cookies.get("refresh_token"))
    at = _norm_token(cookies.get("access_token"))

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
# 🎯 Daily goal (Home) - aggregate across Word/Kanji/Talk via quiz_attempts
# ============================================================
KST = timezone(timedelta(hours=9))

def _today_kst_range_utc():
    """Return (start_utc_iso, end_utc_iso) for today's KST 00:00~24:00."""
    today_kst = datetime.now(KST).date()
    start_kst = datetime(today_kst.year, today_kst.month, today_kst.day, 0, 0, 0, tzinfo=KST)
    end_kst = start_kst + timedelta(days=1)
    start_utc = start_kst.astimezone(timezone.utc)
    end_utc = end_kst.astimezone(timezone.utc)
    # Supabase accepts RFC3339/ISO; keep timezone info
    return start_utc.isoformat(), end_utc.isoformat()

def _infer_kind(level: str, pos_mode: str) -> str:
    lv = (level or "").strip().lower()
    pm = (pos_mode or "").strip().lower()
    if pm.endswith(":situation") or ":situation" in pm:
        return "talk"
    if lv in {"noun", "verb", "adj_i", "adj_na", "other", "adverb", "particle", "conjunction", "interjection"}:
        return "word"
    # default: kanji
    return "kanji"

def fetch_today_attempts(sb_authed, user_id: str) -> list[dict]:
    start_utc, end_utc = _today_kst_range_utc()
    try:
        res = (
            sb_authed.table("quiz_attempts")
            .select("created_at, level, pos_mode, quiz_len, score")
            .eq("user_id", user_id)
            .gte("created_at", start_utc)
            .lt("created_at", end_utc)
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def fetch_recent_attempts(sb_authed, user_id: str, limit: int = 500) -> list[dict]:
    """Fetch recent attempts for dashboard analytics (capped for speed)."""
    try:
        res = (
            sb_authed.table("quiz_attempts")
            .select("created_at, quiz_len, score, level, pos_mode")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(int(limit))
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def _kst_date_from_created_at(created_at: str) -> date | None:
    """Parse created_at (ISO) into KST date."""
    if not created_at:
        return None
    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        kst = timezone(timedelta(hours=9))
        return dt.astimezone(kst).date()
    except Exception:
        return None


def build_daily_sets_map(attempts: list[dict]) -> dict[date, int]:
    """Return {date: sets} map (1 attempt == 1 set)."""
    m: dict[date, int] = {}
    for a in attempts:
        d = _kst_date_from_created_at(str(a.get("created_at") or ""))
        if not d:
            continue
        m[d] = m.get(d, 0) + 1
    return m


def calc_streak(daily_sets: dict[date, int], today: date | None = None) -> int:
    """Consecutive days streak where sets >= 1 (including today)."""
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    streak = 0
    cur = today
    while daily_sets.get(cur, 0) >= 1:
        streak += 1
        cur = cur - timedelta(days=1)
        if streak > 3650:
            break
    return streak


def render_home_dashboard(sb_authed, user):
    """Home Hub dashboard (game-like + mobile-friendly)."""
    attempts_recent = fetch_recent_attempts(sb_authed, user.id, limit=500)
    sm_recent = summarize_attempts(attempts_recent)

    attempts_today = fetch_today_attempts(sb_authed, user.id)
    sm_today = summarize_attempts(attempts_today)

    daily_map = build_daily_sets_map(attempts_recent)
    kst_today = datetime.now(timezone(timedelta(hours=9))).date()
    streak = calc_streak(daily_map, today=kst_today)

    st.markdown(
        f"""
<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:0.75rem;margin-top:0.2rem;margin-bottom:0.6rem;">
  <div>
    <div style="font-size:1.35rem;font-weight:800;line-height:1.2;">하테나 학습 허브</div>
    <div style="opacity:0.72;font-size:0.95rem; margin-top:0.15rem;">오늘도 1세트만 더 해볼까요?</div>
  </div>
  <div style="text-align:right;">
    <div style="display:inline-flex;align-items:center;gap:.35rem;padding:.22rem .55rem;border-radius:999px;border:1px solid rgba(0,0,0,.10);background:rgba(0,0,0,.02);font-size:.92rem;">
      🔥 <b>{streak}</b>일 연속
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Daily goal block (sets-based)
    render_daily_goal_home(sb_authed, user.id)

    st.markdown("---")

    st.markdown("## 📊 이번 주 학습")
    days = [kst_today - timedelta(days=i) for i in range(6, -1, -1)]
    sets = [int(daily_map.get(d, 0)) for d in days]
    try:
        import pandas as pd

        chart_df = pd.DataFrame({"날짜": [d.strftime("%m/%d") for d in days], "세트": sets}).set_index("날짜")
        st.bar_chart(chart_df)
    except Exception:
        st.caption("그래프를 표시할 수 없습니다.")

    c1, c2, c3 = st.columns(3)
    c1.metric("오늘 세트", f"{sm_today['total_sets']}세트")
    acc_today = 0
    if sm_today["total_q"] > 0:
        acc_today = int(round(sm_today["total_score"] / sm_today["total_q"] * 100))
    c2.metric("오늘 정답률", f"{acc_today}%")
    c3.metric("최근 500회 누적", f"{sm_recent['total_sets']}세트")

    st.markdown("---")

    st.markdown("## 🚀 훈련 바로가기")

    def _card(href: str, title: str, subtitle: str, foot: str):
        st.markdown(
            f"""
<a href="{href}" target="_self" style="text-decoration:none;">
  <div style="border:1px solid rgba(0,0,0,.10);border-radius:18px;padding:0.9rem 0.95rem;margin:0.55rem 0;background:rgba(0,0,0,.015);">
    <div style="font-weight:800;font-size:1.05rem;">{title}</div>
    <div style="opacity:0.72;margin-top:0.18rem;">{subtitle}</div>
    <div style="opacity:0.75;font-size:0.9rem;margin-top:0.55rem;">{foot}</div>
  </div>
</a>
""",
            unsafe_allow_html=True,
        )

    t_word = sm_today["by_kind"]["word"]["sets"]
    t_kanji = sm_today["by_kind"]["kanji"]["sets"]
    t_talk = sm_today["by_kind"]["talk"]["sets"]
    r_word = sm_recent["by_kind"]["word"]["sets"]
    r_kanji = sm_recent["by_kind"]["kanji"]["sets"]
    r_talk = sm_recent["by_kind"]["talk"]["sets"]

    _card("?p=word", "📘 단어 훈련", f"오늘 {t_word}세트 완료", f"누적(최근 500회): {r_word}세트")
    _card("?p=kanji", "🈶 한자 훈련", f"오늘 {t_kanji}세트 완료", f"누적(최근 500회): {r_kanji}세트")
    _card("?p=talk", "💬 회화 훈련", f"오늘 {t_talk}세트 완료", f"누적(최근 500회): {r_talk}세트")

    st.caption("※ 누적 수치는 최근 기록(최대 500회) 기준으로 빠르게 표시됩니다.")

def summarize_attempts(attempts: list[dict]) -> dict:
    out = {
        "total_sets": 0,
        "total_q": 0,
        "total_score": 0,
        "by_kind": {
            "word": {"sets": 0, "q": 0, "score": 0},
            "kanji": {"sets": 0, "q": 0, "score": 0},
            "talk": {"sets": 0, "q": 0, "score": 0},
        },
    }
    for a in attempts:
        q = int(a.get("quiz_len") or 0)
        s = int(a.get("score") or 0)
        kind = _infer_kind(str(a.get("level") or ""), str(a.get("pos_mode") or ""))
        out["total_sets"] += 1
        out["total_q"] += q
        out["total_score"] += s
        out["by_kind"][kind]["sets"] += 1
        out["by_kind"][kind]["q"] += q
        out["by_kind"][kind]["score"] += s
    return out

def render_plan_pill():
    plan = (st.session_state.get("user_plan") or "free").lower()
    txt = "✨ PRO 이용 중입니다" if plan == "pro" else "🆓 FREE 이용 중"
    st.markdown(
        f"""
<div style="display:flex;justify-content:flex-start;margin-top:0.15rem;margin-bottom:0.2rem;">
  <div style="
    display:inline-flex;align-items:center;gap:.45rem;
    padding:.28rem .55rem;border-radius:999px;
    border:1px solid rgba(0,0,0,.10);
    font-size:.86rem;opacity:.92;background:rgba(0,0,0,.02);
  ">{txt}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_daily_goal_home(sb_authed, user_id: str):
    """Home dashboard: daily goal (sets-based). 1 set == 10 questions (quiz_len)."""
    progress_all = st.session_state.get("progress_all", {}) or {}

    # ✅ 세트 목표(기본 3세트). 기존 '문항 목표'를 쓰고 있었다면, 일단 세트 목표로 전환합니다.
    goal_sets = int((progress_all.get("daily_goal_sets") or 3))

    attempts = fetch_today_attempts(sb_authed, user_id)
    sm = summarize_attempts(attempts)

    done_sets = int(sm.get("total_sets", 0))
    done_q = int(sm.get("total_q", 0))

    pct = 0 if goal_sets <= 0 else min(100, int(round(done_sets / goal_sets * 100)))

    st.markdown("## 🎯 오늘의 목표 (세트 기준)")
    st.progress(pct / 100 if goal_sets > 0 else 0.0)

    c1, c2, c3 = st.columns(3)
    c1.metric("오늘 완료 세트", f"{done_sets}/{goal_sets}")
    acc = 0 if done_q <= 0 else int(round(sm.get("total_score", 0) / done_q * 100))
    c2.metric("정답률", f"{acc}%")
    c3.metric("문항 수", f"{done_q}문항")

    b1, b2, b3 = st.columns(3)
    b1.caption(f"단어: {sm['by_kind']['word']['sets']}세트 · {sm['by_kind']['word']['q']}문항")
    b2.caption(f"한자: {sm['by_kind']['kanji']['sets']}세트 · {sm['by_kind']['kanji']['q']}문항")
    b3.caption(f"회화: {sm['by_kind']['talk']['sets']}세트 · {sm['by_kind']['talk']['q']}문항")

    with st.expander("목표 수정", expanded=False):
        new_goal = st.number_input("하루 목표 세트 수 (1세트=10문항)", min_value=0, max_value=100, value=goal_sets, step=1)
        if st.button("저장", use_container_width=True, key="hub_daily_goal_save"):
            progress_all["daily_goal_sets"] = int(new_goal)
            st.session_state["progress_all"] = progress_all
            save_progress(sb_authed, user_id, progress_all)
            st.success("저장했습니다.")

def render_reminder_settings(sb_authed, user):
    """Render reminder settings UI (toggle + time) and persist to profiles.progress.reminder."""
    progress_all = st.session_state.get("progress_all", {}) or {}
    rem = progress_all.get("reminder") or {}
    enabled_default = bool(rem.get("enabled", True))
    time_default = rem.get("time", "09:00")

    st.markdown("## 🔔 홈 알림 설정")
    c1, c2 = st.columns([1, 1])
    with c1:
        enabled = st.toggle("알림 사용", value=enabled_default, key="hub_rem_enabled")
    with c2:
        time_str = st.text_input("알림 시간(HH:MM)", value=time_default, key="hub_rem_time")

    if st.button("저장", use_container_width=True, key="hub_rem_save"):
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


def fire_in_app_reminder_if_enabled(user):
    """If reminder is enabled, schedule an in-app notification when the app is open."""
    progress_all = st.session_state.get("progress_all", {}) or {}
    rem = progress_all.get("reminder") or {}
    enabled = bool(rem.get("enabled", True))
    time_str = rem.get("time", "09:00")

    if not enabled:
        return

    try:
        hh, mm = [int(x) for x in time_str.split(":")]
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            # next day
            target = target.replace(day=now.day)  # keep structure; safe fallback
            target = target + (datetime(now.year, now.month, now.day) - datetime(now.year, now.month, now.day))
        delay_ms = max(1000, int((target - now).total_seconds() * 1000))
    except Exception:
        delay_ms = 0

    msg = json.dumps(daily_message(str(user.id)))
    components.html(
        f"""
<script>
  (function(){{
    try {{
      const delay = {delay_ms};
      const message = {msg};
      if (delay <= 0) return;
      setTimeout(() => {{
        try {{
          if (typeof Notification !== 'undefined') {{
            if (Notification.permission === 'granted') {{
              new Notification('하테나일본어', {{ body: message }});
            }}
          }}
          // Fallback: simple alert-like toast
          const t = document.createElement('div');
          t.textContent = message;
          t.style.cssText = 'position:fixed;left:50%;bottom:16px;transform:translateX(-50%);padding:10px 14px;background:rgba(20,20,20,0.92);color:#fff;border-radius:12px;font-size:14px;z-index:2147483647;';
          document.body.appendChild(t);
          setTimeout(()=>t.remove(), 4500);
        }} catch(e) {{}}
      }}, delay);
    }} catch(e) {{}}
  }})();
</script>
""",
        height=0,
    )


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
# 🔔 In-app reminder (no inline UI; settings live in menu -> Reminder page)
# ============================================================
fire_in_app_reminder_if_enabled(user)

# ============================================================
# ✅ Navigation (hub_page)
# ============================================================
if "hub_page" not in st.session_state:
    st.session_state["hub_page"] = "home"

def go(page: str):
    st.session_state["hub_page"] = page
    st.rerun()


def _clear_training_ui_state():
    """Clear only training-related UI/session keys so menu navigation always feels fresh.
    IMPORTANT: Do NOT clear auth/progress tokens or user info.
    """
    prefixes = (
        "q_",          # quiz option widgets (word/kanji)
        "talk_",       # talk widgets
        "talk_submit_",
        "talk_next_",
        "talk_to_wrongs_",
    )
    exact_keys = {
        # common quiz flags
        "submitted", "is_graded",
        # word/kanji pools
        "_pool", "pool_ready", "_patterns", "_patterns_ready",
        # quiz state
        "quiz", "answers", "history", "wrong_list",
        "wrong_counter", "total_counter",
        "saved_this_attempt", "stats_saved_this_attempt", "session_stats_applied_this_attempt",
        "quiz_version",
        # misc per-run UI helpers
        "_scroll_top_once", "_scroll_top_nonce",
        "excluded_wrong_words",
        "target_questions",
        "counted_qids",
        "combo_last_notice",
        "_counted_today",
        "today_done",
        "today_goal_done",
    }

    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (k in exact_keys or k.startswith(prefixes)):
            st.session_state.pop(k, None)

def nav_to(page: str):
    _clear_training_ui_state()
    st.session_state["hub_page"] = page
    st.rerun()


def hub_logout():
    cookies["access_token"] = ""
    cookies["refresh_token"] = ""
    _cookies_save_once_per_run()
    for k in ["user","access_token","refresh_token","sb_authed","sb_authed_token","progress_all","hub_page","HUB_MODE"]:
        st.session_state.pop(k, None)

    # ✅ prevent infinite loop when URL has ?action=logout
    try:
        st.query_params.clear()
    except Exception:
        pass

    st.rerun()

def render_floating_menu():
    """
    ✅ Mobile-friendly floating hamburger menu (no sidebar)
    - Pure HTML/CSS toggle so it always renders.
    - Navigation via query params (?p=word etc.)
    """
    st.markdown(
        """
<style>
/* ===== Floating Menu (Hub) ===== */
.hub-float-wrap{
  position: fixed;
  top: 3.1rem;
  left: 0.65rem;
  z-index: 2147483647;
  font-family: inherit;
}
#hub_menu_toggle{ display:none; }
.hub-menu-btn{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width: 48px; height: 48px;
  border-radius: 12px;
  background: rgba(20,20,20,0.92);
  color: #fff;
  font-size: 22px;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(0,0,0,0.18);
  user-select:none;
}
.hub-menu-panel{
  position: fixed;
  top: 0; left: 0;
  height: 100vh;
  width: min(78vw, 320px);
  background: rgba(255,255,255,0.98);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0,0,0,0.08);
  transform: translateX(-110%);
  transition: transform 180ms ease;
  z-index: 99999;
  padding: 0.9rem 0.9rem 1.2rem;
}
.hub-menu-panel .hub-menu-title{
  font-weight: 700;
  font-size: 1.05rem;
  margin: 0.2rem 0 0.8rem;
}
.hub-menu-panel a{
  display:block;
  padding: 0.85rem 0.85rem;
  margin: 0.25rem 0;
  border-radius: 12px;
  text-decoration: none;
  color: rgba(10,10,10,0.92);
  border: 1px solid rgba(0,0,0,0.06);
}
.hub-menu-overlay{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease;
  z-index: 99998;
}
#hub_menu_toggle:checked ~ .hub-menu-panel{ transform: translateX(0); }
#hub_menu_toggle:checked ~ .hub-menu-overlay{
  opacity: 1;
  pointer-events: auto;
}
</style>

<div class="hub-float-wrap">
  <input type="checkbox" id="hub_menu_toggle" />
  <label class="hub-menu-btn" for="hub_menu_toggle" aria-label="menu">☰</label>

  <div class="hub-menu-panel">
    <div class="hub-menu-title">메뉴</div>
    <a href="?p=home" target="_self">🏠 홈</a>
    <a href="?p=word" target="_self">📘 단어</a>
    <a href="?p=kanji" target="_self">🈶 한자</a>
    <a href="?p=talk" target="_self">💬 회화</a>
    <a href="?p=my" target="_self">👤 마이페이지</a>
    <a href="?p=reminder" target="_self">🔔 알림 설정</a>
    <a href="?action=logout" target="_self">🚪 로그아웃</a>
    <div style="height:0.6rem"></div>
    <div style="font-size:0.85rem; opacity:0.7;">Tip: 바깥을 누르면 닫힙니다.</div>
  </div>

  <label class="hub-menu-overlay" for="hub_menu_toggle"></label>
</div>
""",
        unsafe_allow_html=True,
    )


render_floating_menu()
render_plan_pill()

# ============================================================
# ✅ URL navigation (for floating menu links)
# ============================================================
try:
    qp = st.query_params
    q_action = qp.get("action")
    q_page = qp.get("p")
except Exception:
    q_action = None
    q_page = None

if q_action == "logout":
    hub_logout()

if q_page in {"home","word","kanji","talk","my","reminder"}:
    if st.session_state.get("hub_page") != q_page:
        _clear_training_ui_state()
        st.session_state["hub_page"] = q_page

# ============================================================
# ✅ Runner

# ============================================================
def run_script(filename: str):
    path = (BASE_DIR / filename).resolve()
    if not path.exists() or not path.is_file():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()

    # ✅ 메뉴 클릭(전체 리로드)에서도 쿠키 → 세션 복원 보장
    refresh_session_from_cookie_if_needed(force=True)

    # talk.py/app.py 호환: supabase client 공유
    if "supabase" not in st.session_state and st.session_state.get("sb") is not None:
        st.session_state["supabase"] = st.session_state["sb"]

    if "user" not in st.session_state or not st.session_state.get("user"):
        st.warning("세션이 만료되었습니다. 다시 로그인해 주세요.")
        st.stop()

    st.session_state["HUB_MODE"] = True
    runpy.run_path(str(path), run_name="__main__")

page = st.session_state.get("hub_page", "home")

if page == "home":
    # ✅ Home Hub: dashboard view
    render_home_dashboard(sb_authed, user)
    st.info("☰ 메뉴에서 단어/한자/회화 훈련을 선택하세요.")

elif page == "my":
    # ✅ 독립 마이페이지: 한자(app.py) 안에 있던 대시보드를 그대로 분리한 mypage.py를 실행
    run_script("mypage.py")
    st.stop()

elif page == "reminder":
    render_reminder_settings(sb_authed, user)
    st.stop()

elif page == "word":
    st.session_state["hub_target"] = "word"
    run_script("hotena_basic.py")
elif page == "kanji":
    st.session_state["hub_target"] = "kanji"
    run_script("app.py")
elif page == "talk":
    st.session_state["hub_target"] = "talk"
    run_script("talk.py")
else:
    st.info("상단 메뉴에서 원하는 항목을 선택하세요.")
