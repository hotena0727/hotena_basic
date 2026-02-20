# home.py
from __future__ import annotations

BUILD_STAMP = 'home-min-clean-v2 (replace dashboard) 2026-02-20 KST (+09:00)'

from pathlib import Path
import os
import runpy
import json
import hashlib
import base64
from cryptography.fernet import Fernet
from datetime import date, datetime, timedelta, timezone
import streamlit as st
import streamlit.components.v1 as components
# ============================================================
# ✅ LocalStorage / QueryParam persistence helpers
# ============================================================
def _js_bridge_localstorage_to_queryparam(ls_key: str, qp_key: str):
    try:
        components.html(
            f"""<script>
(function(){{
  try {{
    const lsKey = {json.dumps("LS_KEY")};
    const qpKey = {json.dumps("QP_KEY")};
    const url = new URL(window.location.href);
    if (!url.searchParams.get(qpKey)) {{
      const v = localStorage.getItem(lsKey);
      if (v) {{
        url.searchParams.set(qpKey, v);
        window.location.replace(url.toString());
      }}
    }}
  }} catch(e) {{}}
}})();
</script>""".replace("LS_KEY", ls_key).replace("QP_KEY", qp_key),
            height=0,
        )
    except Exception:
        pass

def _js_set_localstorage(key: str, value: str):
    try:
        components.html(
            f"""<script>
try {{
  localStorage.setItem({json.dumps("K")}, {json.dumps("V")});
}} catch(e) {{}}
</script>""".replace("K", key).replace("V", value),
            height=0,
        )
    except Exception:
        pass

def _js_remove_localstorage(key: str):
    try:
        components.html(
            f"""<script>
try {{
  localStorage.removeItem({json.dumps("K")});
}} catch(e) {{}}
</script>""".replace("K", key),
            height=0,
        )
    except Exception:
        pass


from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# ============================================================
# ✅ Page Config (Hub only)
# ============================================================
st.set_page_config(page_title="Hotena Hub", layout="centered")
# ✅ TOP anchor for floating button (no-JS)
st.markdown('<div id="hotena-top"></div>', unsafe_allow_html=True)

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
# ✅ If COOKIE_PASSWORD is not set, derive a STABLE key from SUPABASE_ANON_KEY.
#    This prevents 'logout on refresh' caused by missing/rotating cookie password across instances.
COOKIE_PASSWORD_FALLBACK = hashlib.sha256(CFG["SUPABASE_ANON_KEY"].encode("utf-8")).hexdigest()
if not CFG.get("COOKIE_PASSWORD"):
    CFG["COOKIE_PASSWORD"] = COOKIE_PASSWORD_FALLBACK

st.session_state["cfg"] = CFG

missing = [k for k, v in CFG.items() if not v]
if missing:
    st.error(f"설정값이 없습니다: {', '.join(missing)} (Cloud Run env 또는 Streamlit secrets 확인)")
    st.stop()


# ============================================================
# ✅ Encrypted token helpers (defined early)
# ============================================================
def _fernet():
    pw = CFG.get("COOKIE_PASSWORD", "")
    key = base64.urlsafe_b64encode(hashlib.sha256(pw.encode("utf-8")).digest())
    return Fernet(key)

def _enc(s: str) -> str:
    return _fernet().encrypt(s.encode("utf-8")).decode("utf-8")

def _dec(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None

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

    # Bridge localStorage -> query params once
    _js_bridge_localstorage_to_queryparam("hotena_rt", "rt")
    _js_bridge_localstorage_to_queryparam("hotena_at", "at")

    rt = None
    at = None
    try:
        rt_enc = st.query_params.get("rt")
        at_enc = st.query_params.get("at")
        rt = _dec(rt_enc) if isinstance(rt_enc, str) and rt_enc else None
        at = _dec(at_enc) if isinstance(at_enc, str) and at_enc else None
    except Exception:
        rt = None
        at = None

    if not rt:
        try:
            rt = cookies.get("refresh_token")
        except Exception:
            rt = None
    if not at:
        try:
            at = cookies.get("access_token")
        except Exception:
            at = None

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

            try:
                cookies["access_token"] = refreshed.session.access_token
                cookies["refresh_token"] = refreshed.session.refresh_token
                _cookies_save_once_per_run()
            except Exception:
                pass

            try:
                st.query_params["rt"] = _enc(refreshed.session.refresh_token)
                st.query_params["at"] = _enc(refreshed.session.access_token)
                _js_set_localstorage("hotena_rt", st.query_params.get("rt", ""))
                _js_set_localstorage("hotena_at", st.query_params.get("at", ""))
            except Exception:
                pass

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



# ============================================================
# ✅ UI helper: fixed 3-dot progress (home dashboard)
# ============================================================
def _dots_3(done_sets: int, goal_sets: int) -> str:
    # Always show 3 dots for a clean dashboard look.
    if goal_sets <= 0:
        filled = 0
    else:
        ratio = done_sets / float(goal_sets)
        if ratio <= 0:
            filled = 0
        elif ratio >= 1:
            filled = 3
        else:
            filled = int(round(ratio * 3))
            filled = max(0, min(3, filled))
    return " ".join(["●"] * filled + ["○"] * (3 - filled))


def render_home_dashboard(sb_authed, user):
    """Home Hub dashboard (A++): donut + weekly heatmap + level mini bars + rows + smart CTA + compact goal gear."""
    from datetime import datetime, timezone, timedelta

    # ---- data ----
    attempts_recent = fetch_recent_attempts(sb_authed, user.id, limit=500)
    sm_recent = summarize_attempts(attempts_recent)

    attempts_today = fetch_today_attempts(sb_authed, user.id)
    sm_today = summarize_attempts(attempts_today)

    daily_map = build_daily_sets_map(attempts_recent)

    kst_today = datetime.now(timezone(timedelta(hours=9))).date()

    # ---- goal settings toggle ----
    if "show_goal_settings" not in st.session_state:
        st.session_state["show_goal_settings"] = False

    streak = calc_streak(daily_map, today=kst_today)

    progress_all = st.session_state.get("progress_all", {}) or {}
    goal_sets = int((progress_all.get("daily_goal_sets") or 3))

    done_total = int(sm_today.get("total_sets", 0))
    pct = 0 if goal_sets <= 0 else int(round(min(1.0, done_total / float(goal_sets)) * 100))

    w = sm_today["by_kind"]["word"]
    k = sm_today["by_kind"]["kanji"]
    t = sm_today["by_kind"]["talk"]

    # ---- daily auto reset marker (KST) ----
    last_seen = (progress_all.get("last_seen_date") or "")
    today_str = str(kst_today)
    if last_seen != today_str:
        progress_all["last_seen_date"] = today_str
        st.session_state["progress_all"] = progress_all
        # close any open settings panel on day change
        st.session_state["show_goal_settings"] = False
        try:
            save_progress(sb_authed, user.id, progress_all)
        except Exception:
            pass

    # ---- one-line motivation (stable per day) ----
    remaining_sets = max(0, goal_sets - done_total)
    messages = [
        "오늘도 10문제면 충분해요. 가볍게 한 세트만.",
        "완벽 말고, 이어가기. 오늘도 한 번만 눌러보세요.",
        "하루 한 세트가 쌓이면, 실력이 됩니다.",
        "짧게라도 괜찮아요. 지금 시작이 제일 쉬워요.",
        "어제보다 1문제만 더. 그게 루틴이에요.",
        "오늘의 성취는 ‘시작’에서 결정돼요.",
    ]
    idx = (kst_today.toordinal() + (streak * 3) + remaining_sets) % len(messages)
    motivation = messages[idx]

    # ---- local helper ----
    def _dots_3(done_sets: int, goal_sets_: int) -> str:
        if goal_sets_ <= 0:
            filled = 0
        else:
            ratio = done_sets / float(goal_sets_)
            if ratio <= 0:
                filled = 0
            elif ratio >= 1:
                filled = 3
            else:
                filled = int(round(ratio * 3))
                filled = max(0, min(3, filled))
        return " ".join(["●"] * filled + ["○"] * (3 - filled))

    # ---- CSS ----
    st.markdown(
        """
<style>
  .h-wrap{margin-top:.10rem;}
  .h-top{display:flex;align-items:flex-end;justify-content:space-between;gap:.75rem;margin:.15rem 0 .45rem;}
  .h-title{font-size:1.28rem;font-weight:850;line-height:1.15;margin:0;}
  .h-sub{opacity:.70;font-size:.92rem;margin:.18rem 0 0;}
  .h-pill{display:inline-flex;align-items:center;gap:.35rem;padding:.20rem .55rem;border-radius:999px;border:1px solid rgba(0,0,0,.10);background:rgba(0,0,0,.02);font-size:.92rem;white-space:nowrap;}

  /* gear */
  .h-gear-wrap{display:flex;justify-content:flex-end;margin:.10rem 0 .05rem;}
  div[data-testid="column"] .stButton button{border-radius:14px;}

  /* donut */
  @property --p { syntax: '<number>'; inherits: false; initial-value: 0; }
  .h-center{display:flex;align-items:center;justify-content:center;margin:.52rem 0 .20rem;position:relative;}
  .donut{
    --p: 0;
    width: 150px; height: 150px; border-radius: 50%;
    background:
      conic-gradient(
        from -90deg,
        rgba(46,124,246,0.95) calc(var(--p) * 1%),
        rgba(0,0,0,.08) 0
      );
    display:flex;align-items:center;justify-content:center;
    box-shadow: 0 12px 34px rgba(0,0,0,0.10);
    border: 1px solid rgba(49,51,63,0.14);
    position:relative;
    animation: donutFill 650ms ease-out forwards;
  }
  .donut::after{
    content:"";
    position:absolute; inset: 6px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 25%, rgba(255,255,255,0.70), rgba(255,255,255,0.0) 55%);
    pointer-events:none;
    mix-blend-mode: soft-light;
  }
  .donut::before{
    content:"";
    width: 110px; height: 110px; border-radius: 50%;
    background: rgba(255,255,255,0.98);
    border: 1px solid rgba(0,0,0,.06);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
    position:relative;
    z-index: 1;
  }
  .donut-inner{
    position:absolute;
    width: 150px; height: 150px;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    text-align:center;
    pointer-events:none;
    z-index: 2;
  }
  .donut-pct{font-size:1.62rem;font-weight:900;line-height:1.0;margin-bottom:.15rem;}
  .donut-label{font-size:.86rem;opacity:.72;}
  @keyframes donutFill{ from { --p: 0; } to { --p: var(--target); } }

  /* weekly heatmap */
  .hm-wrap{margin:.05rem 0 .40rem;}
  .hm-title{display:flex;align-items:center;justify-content:space-between;margin:.06rem 0 .22rem;}
  .hm-title b{font-size:.92rem;}
  .hm-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:.30rem;}
  .hm-cell{
    height: 20px;
    border-radius: 7px;
    border: 1px solid rgba(49,51,63,0.12);
    background: rgba(0,0,0,0.05);
    display:flex;align-items:center;justify-content:center;
    font-size:.80rem;
    opacity:.92;
  }
  .hm-on{background: rgba(46,124,246,0.16); border-color: rgba(46,124,246,0.20);}
  .hm-mid{background: rgba(46,124,246,0.26); border-color: rgba(46,124,246,0.24);}
  .hm-hi{background: rgba(46,124,246,0.36); border-color: rgba(46,124,246,0.28);}
  .hm-lab{font-size:.78rem; opacity:.68; margin-top:.16rem;}

  /* level bars */
  .lv-wrap{
    margin:.10rem 0 .42rem;
    padding:.58rem .70rem;
    border-radius:16px;
    border:1px solid rgba(49,51,63,0.14);
    background: rgba(255,255,255,0.06);
    box-shadow: 0 9px 24px rgba(0,0,0,0.06);
  }
  .lv-title{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:.42rem;}
  .lv-title b{font-size:.92rem;}
  .lv-title span{font-size:.82rem;opacity:.68;}
  .lv-row{display:grid;grid-template-columns:38px 1fr 30px;gap:.45rem;align-items:center;margin:.22rem 0;}
  .lv-lab{font-size:.86rem;font-weight:800;opacity:.78;}
  .lv-track{height:10px;border-radius:999px;background:rgba(0,0,0,0.07);overflow:hidden;border:1px solid rgba(0,0,0,0.05);}
  .lv-fill{height:100%;border-radius:999px;background:rgba(46,124,246,0.55);}
  .lv-val{font-size:.82rem;opacity:.70;text-align:right;}

  /* rows */
  .h-rows{display:flex;flex-direction:column;gap:.46rem;margin:.05rem 0 .55rem;}
  .row{
    display:flex;align-items:center;justify-content:space-between;gap:.6rem;
    padding: .62rem .72rem;
    border-radius: 16px;
    border: 1px solid rgba(49,51,63,0.14);
    background: rgba(255,255,255,0.02);
    box-shadow: 0 9px 24px rgba(0,0,0,0.07);
    transition: transform 120ms ease, box-shadow 120ms ease;
  }
  .row:hover{transform: translateY(-1px); box-shadow: 0 12px 30px rgba(0,0,0,0.10);}
  .row-left{display:flex;flex-direction:column;gap:.12rem;min-width:0;}
  .row-title{font-size:1.00rem;font-weight:820;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .row-meta{font-size:.82rem;opacity:.72;margin:0;}
  .row-right{text-align:right;white-space:nowrap;}
  .row-dots{font-size:1.05rem;letter-spacing:1px;margin:0;}
  .row-goal{font-size:.82rem;opacity:.72;margin-top:.05rem;}

  .row-word{background: linear-gradient(90deg, rgba(46,124,246,0.09), rgba(255,255,255,0.02) 55%); border-color: rgba(46,124,246,0.18);}
  .row-kanji{background: linear-gradient(90deg, rgba(76,175,80,0.09), rgba(255,255,255,0.02) 55%); border-color: rgba(76,175,80,0.18);}
  .row-talk{background: linear-gradient(90deg, rgba(156,39,176,0.09), rgba(255,255,255,0.02) 55%); border-color: rgba(156,39,176,0.18);}

  .h-cta{margin-top:.20rem;margin-bottom:.20rem;}
  .h-cta b{font-size:1.0rem;}

  .hub-cta-wrap{ margin-top:.35rem; }

.hub-cta-card{
  margin-top:0;
  padding: .62rem .72rem;
  border-radius: 16px;
  border: 1px solid rgba(49,51,63,0.14);
  background: rgba(255,255,255,0.02);
  box-shadow: 0 9px 24px rgba(0,0,0,0.07);
}

.hub-msgbox{
  margin:0 0 .55rem 0;
  padding:0;
  border:none;
  background:transparent;
  font-weight:820;
  font-size:1.00rem;
  line-height:1.35;
}
@media (prefers-color-scheme: dark){
  .hub-cta-card{
    border:1px solid rgba(255,255,255,0.12);
    background:rgba(255,255,255,0.05);
    box-shadow:0 10px 24px rgba(0,0,0,0.35);
  }
}

  /* gear icon-only + CTA link button */
  .hub-gear-row{display:flex;justify-content:flex-end;line-height:1;margin:.05rem 0 .35rem;}
  .hub-gear,
  .hub-gear:visited,
  .hub-gear:hover,
  .hub-gear:active{
    display:inline-flex;align-items:center;justify-content:center;
    width:2.0rem;height:2.0rem;
    text-decoration:none !important;
    border:none !important;
    outline:none !important;
    font-size:1.15rem;
    background:transparent !important;
    color:inherit;
  }
  .hub-gear:hover{opacity:0.85;}

  .hub-cta-btn,
.hub-cta-btn:visited,
.hub-cta-btn:hover,
.hub-cta-btn:active{
  display:flex;align-items:center;justify-content:center;gap:.45rem;
  width:100%;
  padding:0.78rem 0.95rem;
  border-radius:1.05rem;
  text-decoration:none !important;
  border:1px solid rgba(0,0,0,0.10);
  background:rgba(255,255,255,0.92);
  font-weight:800;
  font-size:1.03rem;
  color:rgba(0,0,0,0.88);
  transition:transform .06s ease, box-shadow .12s ease, background .12s ease;
}
.hub-cta-btn:hover{ transform: translateY(-1px); box-shadow:0 10px 22px rgba(0,0,0,0.10); }
.hub-cta-emoji{ font-size:1.05rem; line-height:1; }
.hub-cta-text{ line-height:1; }
@media (prefers-color-scheme: dark){
  .hub-cta-btn,
  .hub-cta-btn:visited,
  .hub-cta-btn:hover,
  .hub-cta-btn:active{
    border:1px solid rgba(255,255,255,0.16);
    background:rgba(255,255,255,0.08);
    color:rgba(255,255,255,0.92);
  }
  .hub-cta-btn:hover{ box-shadow:0 10px 22px rgba(0,0,0,0.45); }
}
  .hub-cta-btn:hover{background:rgba(255,255,255,0.08);}


  /* ✅ gear icon (visual only icon, no box) */
  #hub_gear_anchor + div[data-testid="stButton"]{
    padding:0 !important;
    margin:0 !important;
    width:auto !important;
    display:flex !important;
    justify-content:flex-end !important;
  }
  #hub_gear_anchor + div[data-testid="stButton"] button{
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    min-height: 0 !important;
    min-width: 0 !important;
    width: auto !important;
    border-radius: 0 !important;
    line-height: 1 !important;
    font-size: 18px !important;
  }
  #hub_gear_anchor + div[data-testid="stButton"] button:hover{
    background: transparent !important;
    opacity: 0.72;
  }
  #hub_gear_anchor + div[data-testid="stButton"] button:focus,
  #hub_gear_anchor + div[data-testid="stButton"] button:active{
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
  }

</style>
        """,
        unsafe_allow_html=True,
    )

    # ---- header ----
    st.markdown(
        f"""
<div class="h-wrap">
  <div class="h-top">
    <div>
      <p class="h-title">하테나 학습 허브</p>
      <p class="h-sub">{motivation}</p>
      <p class="h-sub" style="opacity:.58;font-size:.86rem;margin:.10rem 0 0;">오늘의 성취율을 확인하고, 바로 이어가세요.</p>
    </div>
    <div class="h-pill">🔥 <b>{streak}</b>일</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---- donut ----
    st.markdown(
        f"""
<div class="h-center">
  <div class="donut" style="--target:{pct};"></div>
  <div class="donut-inner">
    <div class="donut-pct">{pct}%</div>
    <div class="donut-label">오늘 목표</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---- weekly heatmap ----
    days = []
    for i in range(6, -1, -1):
        d = kst_today - timedelta(days=i)
        s = int(daily_map.get(d, 0))
        days.append((d, s))

    def _hm_class(sets_: int) -> str:
        if sets_ <= 0:
            return "hm-cell"
        if sets_ == 1:
            return "hm-cell hm-on"
        if sets_ == 2:
            return "hm-cell hm-mid"
        return "hm-cell hm-hi"

    hm_cells = ""
    for d, s in days:
        cls = _hm_class(s)
        mark = "●" if s > 0 else "○"
        hm_cells += f"<div class='{cls}' title='{d.isoformat()} · {s}세트'>{mark}</div>"

    st.markdown(
        f"""
<div class="hm-wrap">
  <div class="hm-title">
    <b>이번 주 루틴</b>
    <div style="font-size:.86rem;opacity:.72;">{sum(1 for _,s in days if s>0)}/7일</div>
  </div>
  <div class="hm-grid">{hm_cells}</div>
  <div class="hm-lab">최근 7일 (오늘 포함)</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---- level mini progress (recent 30 days, sets) ----
    kst_now = datetime.now(timezone(timedelta(hours=9)))
    cutoff = kst_now - timedelta(days=30)

    lvl_sets = {"N5": 0, "N4": 0, "N3": 0, "N2": 0, "N1": 0}
    for a in attempts_recent:
        try:
            lv = str(a.get("level") or "").strip().upper()
            created_at = a.get("created_at")
            if isinstance(created_at, str):
                s = created_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
            else:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
            if lv in lvl_sets:
                lvl_sets[lv] += 1
        except Exception:
            continue

    max_v = max(lvl_sets.values()) if lvl_sets else 0
    def _bar_pct(v: int) -> int:
        if max_v <= 0:
            return 0
        return int(round((v / max_v) * 100))

    level_rows = ""
    for lv in ["N5","N4","N3","N2","N1"]:
        v = int(lvl_sets.get(lv, 0))
        p = _bar_pct(v)
        level_rows += f"""
<div class="lv-row">
  <div class="lv-lab">{lv}</div>
  <div class="lv-track"><div class="lv-fill" style="width:{p}%"></div></div>
  <div class="lv-val">{v}</div>
</div>
"""

    st.markdown(
        f"""
<div class="lv-wrap">
  <div class="lv-title"><b>📊 레벨 진행</b><span>최근 30일 · 세트 수</span></div>
  {level_rows}
</div>
""",
        unsafe_allow_html=True,
    )

    # ---- rows (clickable) ----
    def _row(href: str, title: str, done: int, q: int, kind: str):
        dots = _dots_3(int(done), int(goal_sets))
        return f"""<a href='{href}' style='text-decoration:none;color:inherit;'>
  <div class='row row-{kind}'>
    <div class='row-left'>
      <p class='row-title'>{title}</p>
      <p class='row-meta'>{q} 문항</p>
    </div>
    <div class='row-right'>
      <p class='row-dots'>{dots}</p>
      <div class='row-goal'>{done}/{goal_sets} 세트</div>
    </div>
  </div>
</a>"""

    rows_html = """<div class='h-rows'>""" + \
        _row("?p=word", "📘 단어", int(w["sets"]), int(w["q"]), "word") + \
        _row("?p=kanji", "🈶 한자", int(k["sets"]), int(k["q"]), "kanji") + \
        _row("?p=talk", "💬 회화", int(t["sets"]), int(t["q"]), "talk") + \
        """</div>"""
    st.markdown(rows_html, unsafe_allow_html=True)

        # ---- Smart CTA (message + CTA stacked, gear icon only) ----
    remaining = max(0, goal_sets - done_total)
    kinds = [
        ("word", "📘", "단어", int(w["sets"])),
        ("kanji", "🈶", "한자", int(k["sets"])),
        ("talk", "💬", "회화", int(t["sets"])),
    ]
    order = {"talk": 0, "kanji": 1, "word": 2}
    kinds.sort(key=lambda x: (x[3], order.get(x[0], 9)))
    rec_kind, rec_emoji, rec_label, _ = kinds[0]

    if remaining == 0:
        msg = "오늘 목표 달성! 내일도 1세트부터 가볍게 이어가요."
    elif remaining == 1:
        msg = f"오늘 1세트만 더 하면 목표 달성! ({rec_label} 추천)"
    else:
        msg = f"오늘 {remaining}세트만 더 하면 목표 달성! ({rec_label} 추천)"

    if "show_goal_settings" not in st.session_state:
        st.session_state["show_goal_settings"] = False

    # ✅ 기어(우측 정렬) → 그 아래 CTA 블록(다른 카드들과 같은 폭)
    from urllib.parse import urlencode

    # --- CTA link query (p=rec_kind) ---
    _qp2 = {}
    try:
        _qp2 = dict(st.query_params)
    except Exception:
        _qp2 = {}
    try:
        _qp2.pop("togg
# ---- goal settings (compact expander) ----
    if st.session_state.get("show_goal_settings", False):
        with st.expander("루틴 목표 수정", expanded=True):
            new_goal = st.number_input(
                "하루 목표 세트 수 (1세트=10문항)",
                min_value=0,
                max_value=100,
                value=int(goal_sets),
                step=1,
            )
            csave, cclose = st.columns([1, 1], gap="small")
            with csave:
                if st.button("저장", use_container_width=True, key="hub_daily_goal_save"):
                    progress_all["daily_goal_sets"] = int(new_goal)
                    st.session_state["progress_all"] = progress_all
                    save_progress(sb_authed, user.id, progress_all)
                    st.success("저장했습니다.")
            with cclose:
                if st.button("닫기", use_container_width=True, key="hub_goal_close"):
                    st.session_state["show_goal_settings"] = False


le_goal", None)
    except Exception:
        pass
    _qp2["p"] = rec_kind
    _qs2 = urlencode(_qp2, doseq=True)

    # ✅ gear icon (same page) + CTA card
    _gsp, _gcol = st.columns([1, 0.08], gap="small")
    with _gcol:
        st.markdown("<div id='hub_gear_anchor'></div>", unsafe_allow_html=True)
        if st.button("⚙️", key="hub_goal_gear_icon", help="루틴 목표 수정"):
            st.session_state["show_goal_settings"] = not st.session_state.get("show_goal_settings", False)

    st.markdown(
        f"""
        <div class='hub-cta-wrap'>
          <div class='hub-cta-card'>
            <div class='hub-msgbox'>{msg}</div>
            <a class='hub-cta-btn' href='?{_qs2}' title='{rec_label} 시작'>
              <span class='hub-cta-emoji'>{rec_emoji}</span>
              <span class='hub-cta-text'>{rec_label} 시작</span>
            </a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    

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

def render_floating_menu():
    """✅ Floating hamburger menu (Hub)
    - Uses pure HTML/CSS toggle.
    - Navigation keeps encrypted rt/at query params (so login persists when cookies are blocked).
    - No f-string inside CSS (avoids { } parsing issues) and no inline JS (CSP-safe).
    """
    try:
        rt_enc = st.query_params.get("rt", "")
        at_enc = st.query_params.get("at", "")
    except Exception:
        rt_enc, at_enc = "", ""

    def _q(s: str) -> str:
        try:
            import urllib.parse
            return urllib.parse.quote(s, safe="") if s else ""
        except Exception:
            return s or ""

    base = ""
    if rt_enc:
        base += "rt=" + _q(rt_enc) + "&"
    if at_enc:
        base += "at=" + _q(at_enc) + "&"

    href_home = "?" + base + "p=home"
    href_word = "?" + base + "p=word"
    href_kanji = "?" + base + "p=kanji"
    href_talk = "?" + base + "p=talk"
    href_my   = "?" + base + "p=my"
    href_rem  = "?" + base + "p=reminder"
    href_out  = "?" + base + "action=logout"

    html = """<style>
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
.hub-menu-panel a:active{
  transform: scale(0.99);
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
    <a href="__HREF_HOME__" target="_self">🏠 홈</a>
    <a href="__HREF_WORD__" target="_self">📘 단어</a>
    <a href="__HREF_KANJI__" target="_self">🈶 한자</a>
    <a href="__HREF_TALK__" target="_self">💬 회화</a>
    <a href="__HREF_MY__" target="_self">👤 마이페이지</a>
    <a href="__HREF_REM__" target="_self">🔔 알림 설정</a>
    <a href="__HREF_OUT__" target="_self">🚪 로그아웃</a>
    <div style="height:0.6rem"></div>
    <div style="font-size:0.85rem; opacity:0.7;">Tip: 바깥을 누르면 닫힙니다.</div>
  </div>

  <label class="hub-menu-overlay" for="hub_menu_toggle"></label>
</div>
"""

    html = (html.replace("__HREF_HOME__", href_home)
                .replace("__HREF_WORD__", href_word)
                .replace("__HREF_KANJI__", href_kanji)
                .replace("__HREF_TALK__", href_talk)
                .replace("__HREF_MY__", href_my)
                .replace("__HREF_REM__", href_rem)
                .replace("__HREF_OUT__", href_out))

    st.markdown(html, unsafe_allow_html=True)



def render_float_top_anchor_button():
    """✅ Bottom-right '맨 위로' button using anchor (CSP/No-JS safe)"""
    st.markdown(
        """
<style>
.hotena-float-top{
  position: fixed;
  right: 14px;
  bottom: 88px;
  z-index: 2147483646;
  width: 50px;
  height: 50px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none !important;
  background: rgba(17,17,17,0.86);
  color: #fff !important;
  font-size: 18px;
  box-shadow: 0 12px 26px rgba(0,0,0,0.22);
}
</style>
<a class="hotena-float-top" href="#hotena-top" aria-label="맨 위로">⬆︎</a>
        """,
        unsafe_allow_html=True,
    )


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

                # ✅ persist encrypted tokens for refresh-proof login
                try:
                    st.query_params["rt"] = _enc(res.session.refresh_token)
                    st.query_params["at"] = _enc(res.session.access_token)
                    _js_set_localstorage("hotena_rt", st.query_params.get("rt",""))
                    _js_set_localstorage("hotena_at", st.query_params.get("at",""))
                except Exception:
                    pass

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
    # ✅ clear cookie/local persistence + session state
    try:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        _cookies_save_once_per_run()
    except Exception:
        pass

    # clear query params (e.g., rt/at/p)
    try:
        st.query_params.clear()
    except Exception:
        pass

    # clear localStorage persistence
    try:
        _js_remove_localstorage("hotena_rt")
        _js_remove_localstorage("hotena_at")
    except Exception:
        pass

    for k in [
        "user","access_token","refresh_token","sb_authed","sb_authed_token",
        "progress_all","hub_page","HUB_MODE"
    ]:
        st.session_state.pop(k, None)

    st.rerun()
def render_floating_menu():
    """✅ Floating hamburger menu (Hub)
    - Uses pure HTML/CSS toggle.
    - Navigation keeps encrypted rt/at query params (so login persists when cookies are blocked).
    - No f-string inside CSS (avoids { } parsing issues) and no inline JS (CSP-safe).
    """
    try:
        rt_enc = st.query_params.get("rt", "")
        at_enc = st.query_params.get("at", "")
    except Exception:
        rt_enc, at_enc = "", ""

    def _q(s: str) -> str:
        try:
            import urllib.parse
            return urllib.parse.quote(s, safe="") if s else ""
        except Exception:
            return s or ""

    base = ""
    if rt_enc:
        base += "rt=" + _q(rt_enc) + "&"
    if at_enc:
        base += "at=" + _q(at_enc) + "&"

    href_home = "?" + base + "p=home"
    href_word = "?" + base + "p=word"
    href_kanji = "?" + base + "p=kanji"
    href_talk = "?" + base + "p=talk"
    href_my   = "?" + base + "p=my"
    href_rem  = "?" + base + "p=reminder"
    href_out  = "?" + base + "action=logout"

    html = """<style>
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
.hub-menu-panel a:active{
  transform: scale(0.99);
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
    <a href="__HREF_HOME__" target="_self">🏠 홈</a>
    <a href="__HREF_WORD__" target="_self">📘 단어</a>
    <a href="__HREF_KANJI__" target="_self">🈶 한자</a>
    <a href="__HREF_TALK__" target="_self">💬 회화</a>
    <a href="__HREF_MY__" target="_self">👤 마이페이지</a>
    <a href="__HREF_REM__" target="_self">🔔 알림 설정</a>
    <a href="__HREF_OUT__" target="_self">🚪 로그아웃</a>
    <div style="height:0.6rem"></div>
    <div style="font-size:0.85rem; opacity:0.7;">Tip: 바깥을 누르면 닫힙니다.</div>
  </div>

  <label class="hub-menu-overlay" for="hub_menu_toggle"></label>
</div>
"""

    html = (html.replace("__HREF_HOME__", href_home)
                .replace("__HREF_WORD__", href_word)
                .replace("__HREF_KANJI__", href_kanji)
                .replace("__HREF_TALK__", href_talk)
                .replace("__HREF_MY__", href_my)
                .replace("__HREF_REM__", href_rem)
                .replace("__HREF_OUT__", href_out))

    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# ✅ Bottom Nav (Mobile) + Training Header (A/B)
# - A: top progress strip for training pages
# - B: fixed bottom navigation bar (Home/Word/Kanji/Talk/My)
# ============================================================

def _hub_build_base_qs() -> str:
    """Build querystring base that preserves encrypted rt/at for login persistence."""
    try:
        rt_enc = st.query_params.get("rt", "")
        at_enc = st.query_params.get("at", "")
    except Exception:
        rt_enc, at_enc = "", ""

    def _q(s: str) -> str:
        try:
            import urllib.parse
            return urllib.parse.quote(s, safe="") if s else ""
        except Exception:
            return s or ""

    parts = []
    if rt_enc:
        parts.append("rt=" + _q(rt_enc))
    if at_enc:
        parts.append("at=" + _q(at_enc))
    return ("&".join(parts) + "&") if parts else ""

def render_bottom_nav(active: str = "home"):
    """Mobile-only bottom nav. Hidden on wide screens."""
    base = _hub_build_base_qs()
    def href(p: str) -> str:
        return "?" + base + "p=" + p

    # Mobile only: hide on >= 801px
    html = f"""<style>
.hub-bottom-nav {{
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 2147483000;
  padding: 10px 12px 12px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(0,0,0,0.08);
}}
.hub-bottom-nav .row {{
  display:flex; gap: 10px; justify-content:space-between;
  max-width: 840px; margin: 0 auto;
}}
.hub-bottom-nav a {{
  flex: 1 1 0;
  text-decoration:none;
  color: rgba(20,20,20,0.92);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 14px;
  padding: 10px 8px;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  font-size: 12px;
  background: rgba(0,0,0,0.02);
}}
.hub-bottom-nav a .ic {{ font-size: 18px; line-height: 1; margin-bottom: 4px; }}
.hub-bottom-nav a.active {{
  background: rgba(0,0,0,0.88);
  color: #fff;
  border-color: rgba(0,0,0,0.88);
}}
@media (min-width: 801px) {{
  .hub-bottom-nav {{ display:none !important; }}
}}
</style>
<div class="hub-bottom-nav">
  <div class="row">
    <a href="{href('home')}" target="_self" class="{ 'active' if active=='home' else '' }"><div class="ic">🏠</div><div>홈</div></a>
    <a href="{href('word')}" target="_self" class="{ 'active' if active=='word' else '' }"><div class="ic">📘</div><div>단어</div></a>
    <a href="{href('kanji')}" target="_self" class="{ 'active' if active=='kanji' else '' }"><div class="ic">🈶</div><div>한자</div></a>
    <a href="{href('talk')}" target="_self" class="{ 'active' if active=='talk' else '' }"><div class="ic">💬</div><div>회화</div></a>
    <a href="{href('my')}" target="_self" class="{ 'active' if active=='my' else '' }"><div class="ic">👤</div><div>MY</div></a>
  </div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_training_header(sb_authed, user, kind: str, title: str, subtitle: str):
    """A) Unified title + compact daily goal progress strip on training pages."""
    progress_all = st.session_state.get("progress_all", {}) or {}
    goal_sets = int((progress_all.get("daily_goal_sets") or 3))

    attempts = fetch_today_attempts(sb_authed, user.id)
    sm = summarize_attempts(attempts)
    done_sets_total = int(sm.get("total_sets", 0))
    done_sets_kind = int(sm.get("by_kind", {}).get(kind, {}).get("sets", 0))

    pct = 0.0
    if goal_sets > 0:
        pct = min(1.0, done_sets_total / float(goal_sets))

    st.markdown(
        f"""
<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:0.75rem;margin-top:0.25rem;margin-bottom:0.45rem;">
  <div>
    <div style="font-size:1.35rem;font-weight:800;line-height:1.2;">{title}</div>
    <div style="opacity:0.72;font-size:0.95rem; margin-top:0.15rem;">{subtitle}</div>
  </div>
  <div style="text-align:right;">
    <div style="display:inline-flex;align-items:center;gap:.35rem;padding:.22rem .55rem;border-radius:999px;border:1px solid rgba(0,0,0,.10);background:rgba(0,0,0,.02);font-size:.88rem;">
      오늘 {done_sets_kind}세트
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # compact progress
    st.progress(pct)
    st.caption(f"오늘 완료: {done_sets_total}/{goal_sets}세트 · 현재 페이지: {kind}")
    st.markdown("---")

def run_script(filename: str):
    path = (BASE_DIR / filename).resolve()
    if not path.exists() or not path.is_file():
        st.error(f"파일을 찾을 수 없습니다: {path}")
        st.stop()
    # ✅ Hub mode flag so child scripts can adjust UI/CSS
    st.session_state["HUB_MODE"] = True
    runpy.run_path(str(path), run_name="__main__")


# ============================================================
# ✅ Floating-menu query routing (CSP-safe, preserves rt/at)
# ============================================================
try:
    action = st.query_params.get("action")
    p = st.query_params.get("p")
except Exception:
    action, p = None, None

if action == "logout":
    hub_logout()

if isinstance(p, str) and p:
    if p in {"home", "word", "kanji", "talk", "my", "reminder"}:
        st.session_state["hub_page"] = p

# ✅ Always render floating menu + plan pill in hub mode (after auth)
render_floating_menu()
render_plan_pill()

page = st.session_state.get("hub_page", "home")
render_bottom_nav(active=page)

if page == "home":
    # ✅ Home Hub: dashboard view
    render_home_dashboard(sb_authed, user)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
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
    render_training_header(sb_authed, user, kind="word", title="📘 단어 훈련", subtitle="뜻/발음/한→일 · 10문제 1세트")
    run_script("hotena_basic.py")
elif page == "kanji":
    st.session_state["hub_target"] = "kanji"
    render_training_header(sb_authed, user, kind="kanji", title="🈶 한자 훈련", subtitle="읽기/뜻/복습 · 10문제 1세트")
    run_script("app.py")
elif page == "talk":
    st.session_state["hub_target"] = "talk"
    render_training_header(sb_authed, user, kind="talk", title="💬 회화 훈련", subtitle="상황 판단 · 정답 선택 · 발음 연습")
    run_script("talk.py")
else:
    st.info("상단 메뉴에서 원하는 항목을 선택하세요.")
