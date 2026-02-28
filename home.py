# home.py
from __future__ import annotations

BUILD_STAMP = 'home-clean-no-spacer-v3 (fix run_module reload) 2026-02-22 KST (+09:00)'
from pathlib import Path
import os
import runpy
import importlib
import json
import hashlib
import base64
from cryptography.fernet import Fernet
from datetime import date, datetime, timedelta, timezone
import streamlit as st
import core
import streamlit.components.v1 as components

# ============================================================
# ✅ Font: 일본식 한자(글리프) 우선 적용
# ============================================================
def _inject_jp_font_once():
    if st.session_state.get("_jp_font_injected", False):
        return
    st.session_state["_jp_font_injected"] = True
    st.markdown(
        """
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"]  {
  font-family: 'Noto Sans JP','Noto Sans KR','Yu Gothic','Hiragino Kaku Gothic ProN','Meiryo','Apple SD Gothic Neo',sans-serif !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

_inject_jp_font_once()


# ============================================================
# ✅ Module runner (NO runpy/run_path)
# - Import (or reload) a module by name so it renders in the SAME Streamlit flow
# ============================================================
def run_module(module_name: str):
    """Import (or reload) a module by name so it renders in the SAME Streamlit flow.

    Additionally performs a compile-time syntax/indentation check so Streamlit's
    redaction doesn't hide the real line number.
    """
    try:
        import sys
        import importlib.util
        from pathlib import Path

        # --- Preflight compile to reveal exact SyntaxError/IndentationError line ---
        spec = importlib.util.find_spec(module_name)
        origin = getattr(spec, "origin", None) if spec else None
        if origin and origin.endswith(".py") and Path(origin).exists():
            src = Path(origin).read_text(encoding="utf-8")
            try:
                compile(src, origin, "exec")
            except (SyntaxError, IndentationError) as se:
                lineno = getattr(se, "lineno", None) or 0
                msg = getattr(se, "msg", str(se))
                text = (getattr(se, "text", "") or "").rstrip("\n")
                st.error(f"❌ {module_name}.py 문법/들여쓰기 오류: {msg} (line {lineno})")
                if text:
                    st.code(f"{text}", language="python")
                # show context
                try:
                    lines = src.splitlines()
                    start = max(lineno - 5, 1)
                    end = min(lineno + 4, len(lines))
                    ctx = "\n".join([f"{i:>4}: {lines[i-1]}" for i in range(start, end+1)])
                    st.code(ctx, language="python")
                except Exception:
                    pass
                st.stop()

        # --- Import / reload ---
        if module_name in sys.modules:
            mod = importlib.reload(sys.modules[module_name])
        else:
            mod = importlib.import_module(module_name)

        if hasattr(mod, "render") and callable(getattr(mod, "render")):
            mod.render()

    except Exception as e:
        st.exception(e)
        raise

# ============================================================
# ✅ LocalStorage / QueryParam persistence helpers
# ============================================================
def _js_bridge_localstorage_to_queryparam(ls_key: str, qp_key: str):
    # (Helper) Mirror localStorage value into a URL queryparam without a full page reload.
    # Uses history.replaceState (NOT location.replace) to avoid full reload/new-tab behavior.
    try:
        components.html(
            f"""<script>
(function(){{
  try {{
    const lsKey = {json.dumps(ls_key)};
    const qpKey = {json.dumps(qp_key)};
    const url = new URL(window.location.href);
    if (!url.searchParams.get(qpKey)) {{
      const v = localStorage.getItem(lsKey);
      if (v) {{
        url.searchParams.set(qpKey, v);
        window.history.replaceState({{}}, document.title, url.toString());
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
import html as html_module  # ✅ for html escaping in admin cards

# ============================================================
# ✅ Page Config (Hub only)
# ============================================================
st.set_page_config(page_title="Hotena Hub", layout="centered")

# ✅ Anchor for bottom-right '맨 위로' button
st.markdown('<div id="hotena-top"></div>', unsafe_allow_html=True)


# ✅ Kill component iframe placeholders ASAP (before any other output)
try:
    core.hide_component_iframe_placeholders()
except Exception:
    pass



# ============================================================
# ✅ TOP SPACING FIX (PC + Mobile)
# - Remove Streamlit's default top padding/space
# - Applied once per session
# ============================================================
if not st.session_state.get("_top_compact_css_applied"):
    st.markdown("""<style>
/* === Hotena: ultra-compact top spacing (mobile + desktop) === */
/* 핵심: block-container의 기본 top padding 제거 + 첫 요소 여백 제거 */
section.main > div.block-container,
div[data-testid="stAppViewContainer"] > div.block-container {
  padding-top: 0rem !important;
  margin-top: 0rem !important;
}

/* 첫 요소(메뉴/버튼 래퍼) 상단 여백 제거 */
div.block-container > div:first-child {
  margin-top: 0rem !important;
  padding-top: 0rem !important;
}

/* Streamlit 헤더가 만드는 공간 최소화 */
header[data-testid="stHeader"]{
  display:none !important;
  height:0 !important;
  min-height:0 !important;
}
div[data-testid="stToolbar"]{
  display:none !important;
  height:0 !important;
  visibility:hidden !important;
}
footer{display:none !important;}

/* Container spacing: pull content to the very top */
div[data-testid="stAppViewContainer"]{
  padding-top: 0 !important;
  margin-top: 0 !important;
}
div[data-testid="stAppViewContainer"] .block-container{
  padding-top: 0 !important;
  margin-top: 0 !important;
  padding-bottom: 1.25rem !important; /* keep breathing room for bottom nav */
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
    padding-bottom: 1.5rem !important;
  }

  /* Slightly larger tap targets on phones */
  div[data-testid="stAppViewContainer"] .stButton > button,
  div[data-testid="stAppViewContainer"] button[kind]{
    min-height: 48px !important;
    font-size: 16px !important;
    border-radius: 14px !important;
  }
}

/* ✅ Goal settings (inline, modern) */
.goal-settings-wrap{
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 14px;
  background: rgba(245,247,251,0.85);
}
.goal-settings-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin-bottom: 10px;
}
.goal-settings-head .ttl{
  font-weight:700;
  font-size: 14px;
}
.goal-settings-head .meta{
  font-size: 12px;
  color: rgba(0,0,0,0.55);
  white-space: nowrap;
}
.goal-bar{
  width:100%;
  height: 10px;
  border-radius: 999px;
  background: rgba(0,0,0,0.08);
  overflow:hidden;
  margin: 8px 0 12px;
}
.goal-bar > div{
  height:100%;
  width: var(--w, 0%);
  border-radius: 999px;
  background: rgba(0,0,0,0.55);
  transition: width 420ms ease;
}
.goal-help{
  margin-top: 6px;
  font-size: 12px;
  color: rgba(0,0,0,0.55);
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
    # ✅ If a page explicitly set auth keys to None (logout intent),
    #    do NOT restore session from cookies/query/localStorage.
    #    Instead, hard-clear all persistence once.
    if (not force
        and ("access_token" in st.session_state and st.session_state.get("access_token") is None)
        and ("user" in st.session_state and st.session_state.get("user") is None)
    ):
        try:
            cookies["access_token"] = ""
            cookies["refresh_token"] = ""
            _cookies_save_once_per_run()
        except Exception:
            pass
        try:
            st.query_params.clear()
        except Exception:
            pass
        try:
            _js_remove_localstorage("hotena_rt")
            _js_remove_localstorage("hotena_at")
        except Exception:
            pass
        # Clean a minimal set of keys; keep the rest of UI state intact.
        for k in ["access_token", "refresh_token", "user", "sb_authed", "sb_authed_token"]:
            st.session_state.pop(k, None)
        return False

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
        st.session_state["user_id"] = user_id
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

    # ---- 오늘의 한마디 (한국어, 날짜 기반 고정) ----
    HUB_QUOTES = [
        "오늘 20분이면 충분합니다.",
        "꾸준함은 재능을 이깁니다.",
        "작은 차이가 1년을 바꿉니다.",
        "루틴은 의지를 대신합니다.",
        "느려도 괜찮습니다. 계속하면 됩니다.",
        "매일 조금씩이 가장 빠른 길입니다.",
        "오늘을 채우면 내일이 편해집니다.",
        "공부는 감정이 아니라 구조입니다.",
        "포기하지 않는 사람이 결국 이깁니다.",
        "하테나는 루틴을 만듭니다.",
        "어제보다 1%만 나아지면 됩니다.",
        "오늘 한 문제라도 의미 있습니다.",
        "멈추지 않으면 쌓입니다.",
        "실력은 조용히 올라갑니다.",
        "반복이 결국 차이를 만듭니다.",
        "몰아서 하지 말고, 매일 하세요.",
        "오늘의 기록이 내일의 자신감입니다.",
        "성장은 보이지 않게 진행됩니다.",
        "공부는 자신과의 약속입니다.",
        "매일 하는 사람이 강합니다.",
        "완벽하지 않아도 괜찮습니다.",
        "오늘을 넘기지 마세요.",
        "시작이 가장 쉽습니다.",
        "루틴은 배신하지 않습니다.",
        "하루는 짧지만, 1년은 깁니다.",
        "꾸준함이 가장 큰 무기입니다.",
        "오늘을 버티면 실력이 됩니다.",
        "계속하는 사람이 결국 남습니다.",
        "지금 시작하는 것이 가장 빠릅니다.",
        "하테나는 오늘도 쌓입니다.",
    ]
    today_quote = HUB_QUOTES[kst_today.toordinal() % len(HUB_QUOTES)]

    

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

  /* ✅ Smart CTA (A안): message+CTA fused card */
  .cta_box{
    margin-top: .20rem;
    margin-bottom: 0;
    padding: 12px 14px;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 14px;
    background: rgba(255,255,255,0.70);
    backdrop-filter: blur(2px);
  }
  .cta_box b{font-size:1.0rem;}
  .cta_box_top{
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    border-bottom: 0;
  }

  /* CTA button: match cards and fuse with message box */
  .st-key-hub_cta_primary button{
    width:100% !important;
    border-top-left-radius:0 !important;
    border-top-right-radius:0 !important;
    margin-top:0 !important;
    min-height: 46px !important;
    font-size: 1.02rem !important;
  }
  .st-key-hub_cta_primary{ margin-top:0 !important; }

  /* ✅ goal gear: icon-only + overlay on level progress card */
  .st-key-hub_goal_gear_icon{display:flex;justify-content:flex-end;margin-top:-44px;margin-bottom:10px;}
  .st-key-hub_goal_gear_icon button{
    background:transparent !important;border:0 !important;outline:none !important;box-shadow:none !important;
    padding:0 !important;min-height:auto !important;height:auto !important;line-height:1 !important;
  }
  .st-key-hub_goal_gear_icon button:focus,
  .st-key-hub_goal_gear_icon button:focus-visible,
  .st-key-hub_goal_gear_icon button:active{outline:none !important;box-shadow:none !important;}
  .st-key-hub_goal_gear_icon button p{font-size:18px !important;margin:0 !important;}




/* Quote (오늘의 한마디) */
.h-quote-card{
  display:flex;
  align-items:center;
  gap:8px;
  margin: 0.25rem 0 0.1rem 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(244,247,251,0.95);
  border: 1px solid rgba(227,232,240,1);
}
.h-quote-dot{
  width:6px;height:6px;border-radius:50%;
  background: rgba(74,108,247,1);
  flex-shrink:0;
}
.h-quote-t{
  font-size: 0.98rem;
  font-weight: 600;
  color: rgba(44,62,80,1);
}

/* First-visit guide card (Hub only) */
.h-guide-wrap{margin:.25rem 0 .55rem 0;}
.h-guidebox{
  background: rgba(255,255,255,1);
  border: 1px solid rgba(226,232,240,1);
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(15,23,42,.06);
  padding: .85rem .95rem .85rem;
}
.h-guide-top{display:flex;align-items:flex-start;justify-content:space-between;gap:.75rem;}
.h-guide-title{font-size:1.02rem;font-weight:800;color:rgba(15,23,42,1);margin:0;line-height:1.25;}
.h-guide-sub{margin:.15rem 0 0;font-size:.88rem;color:rgba(51,65,85,1);opacity:.82;line-height:1.45;}
.h-guide-steps{margin:.55rem 0 .15rem;padding:0;list-style:none;display:flex;flex-direction:column;gap:.35rem;}
.h-step{display:flex;gap:.55rem;align-items:flex-start;}
.h-step-badge{
  width:22px;height:22px;border-radius:999px;
  display:inline-flex;align-items:center;justify-content:center;
  font-size:.8rem;font-weight:800;
  border:1px solid rgba(74,108,247,.25);
  background: rgba(74,108,247,.08);
  color: rgba(34,61,214,1);
  flex-shrink:0;
  margin-top:.05rem;
}
.h-step-t{font-size:.92rem;color:rgba(30,41,59,1);line-height:1.45;}
.h-guide-mini{
  display:flex;align-items:center;justify-content:space-between;gap:.7rem;
  padding:.55rem .7rem;border-radius:16px;
  border:1px solid rgba(226,232,240,1);
  background: rgba(248,250,252,1);
}
.h-guide-actions{
  display:flex;align-items:center;justify-content:space-between;gap:.6rem;
  margin-top:.65rem;padding-top:.65rem;
  border-top:1px solid rgba(226,232,240,1);
}
.h-guide-mini-actions{
  display:flex;align-items:center;justify-content:flex-end;gap:.5rem;
}
.h-guide-btn{
  display:inline-flex;align-items:center;justify-content:center;
  padding:.48rem .78rem;border-radius:999px;
  font-size:.86rem;font-weight:800;
  text-decoration:none !important;
  border:1px solid rgba(226,232,240,1);
  background: rgba(255,255,255,1);
  color: rgba(51,65,85,1);
  white-space:nowrap;
}
.h-guide-btn.primary{
  background: rgba(74,108,247,1);
  border-color: rgba(74,108,247,1);
  color: rgba(255,255,255,1);
}
.h-guide-btn.ghost{
  background: rgba(255,255,255,1);
}
.h-guide-btn:hover{filter:brightness(.98);}
.h-guide-mini-t{font-size:.92rem;font-weight:800;color:rgba(15,23,42,1);margin:0;}

</style>
        """,
        unsafe_allow_html=True,
    )


    # ---- first-visit guide (Hub only) ----
    try:
        progress_all = st.session_state.get("progress_all", {}) or {}
        _collapsed = bool(progress_all.get("hub_flow_guide_collapsed", False))

        _flow_action = st.query_params.get("flow")
        if _flow_action in ("hide", "open"):
            # apply once then clear param
            try:
                _set_val = True if _flow_action == "hide" else False
                progress_all["hub_flow_guide_collapsed"] = bool(_set_val)
                st.session_state["progress_all"] = progress_all
                try:
                    save_progress(sb_authed, user.id, progress_all)  # type: ignore[name-defined]
                except Exception:
                    pass
            except Exception:
                pass
            try:
                del st.query_params["flow"]
            except Exception:
                st.query_params.update({})
            st.rerun()

        def _set_collapsed(v: bool):
            progress_all["hub_flow_guide_collapsed"] = bool(v)
            st.session_state["progress_all"] = progress_all
            try:
                save_progress(sb_authed, user.id, progress_all)  # type: ignore[name-defined]
            except Exception:
                pass
            st.rerun()

        st.markdown('<div class="h-guide-wrap">', unsafe_allow_html=True)
        if _collapsed:
            base = _hub_build_base_qs()
            open_href = "?" + base + "flow=open"
            hide_href = "?" + base + "flow=hide"
            start_href = "?" + base + "p=word"

            st.markdown(
                f'''<div class="h-guidebox">
              <div class="h-guide-mini">
                <p class="h-guide-mini-t">📘 하테나일본어 앱 사용 흐름</p>
                <div class="h-guide-mini-actions">
                    <a class="h-guide-btn ghost" href="{open_href}" target="_self">사용 흐름 보기 ▼</a>
                    <a class="h-guide-btn primary" href="{start_href}" target="_self">바로 시작하기</a>
                    <a class="h-guide-btn ghost" href="{hide_href}" target="_self">이 안내 접기</a>
                </div>
              </div>
            </div>''',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
    except Exception:
        pass

    # ---- header ----
    st.markdown(
        f"""
<div class="h-wrap">
  <div class="h-top">
    <div>
      <p class="h-title">하테나일본어</p>
      <div class="h-quote-card"><span class="h-quote-dot"></span><span class="h-quote-t">{today_quote}</span></div>
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

    # ---- goal gear (on level progress card, top-right) ----
    if "show_goal_settings" not in st.session_state:
        st.session_state["show_goal_settings"] = False

    _gl, _gr = st.columns([1, 0.08], gap="small")
    with _gr:
        if st.button("⚙️", key="hub_goal_gear_icon", help="루틴 목표 수정"):
            st.session_state["show_goal_settings"] = not st.session_state["show_goal_settings"]

    # ---- goal settings (inline panel, opens right under gear) ----
    if st.session_state.get("show_goal_settings", False):
        # progress percent for the small animated bar
        _pct = 0.0
        try:
            _pct = 0.0 if int(goal_sets) <= 0 else min(1.0, float(done_total) / float(goal_sets))
        except Exception:
            _pct = 0.0

        st.markdown(
            f"""
<div class="goal-settings-wrap">
  <div class="goal-settings-head">
    <div class="ttl">루틴 목표</div>
    <div class="meta">오늘 {int(done_total)}/{int(goal_sets)} 세트</div>
  </div>
  <div class="goal-bar" style="--w:{_pct*100:.0f}%"><div></div></div>
</div>
""",
            unsafe_allow_html=True,
        )

        # slider (reasonable max, but keep compatibility with existing data)
        _max_goal = max(20, int(goal_sets) * 2)
        _max_goal = min(100, _max_goal)
        new_goal = st.slider(
            "하루 목표 세트 수 (1세트=10문항)",
            min_value=0,
            max_value=int(_max_goal),
            value=int(goal_sets),
            step=1,
            key="hub_goal_slider",
            label_visibility="collapsed",
        )
        st.markdown(
            f"<div class='goal-help'>하루 목표: <b>{int(new_goal)}</b> 세트 (1세트=10문항)</div>",
            unsafe_allow_html=True,
        )

        csave, cclose = st.columns([1, 1], gap="small")
        with csave:
            if st.button("저장", use_container_width=True, key="hub_daily_goal_save"):
                progress_all["daily_goal_sets"] = int(new_goal)
                st.session_state["progress_all"] = progress_all
                save_progress(sb_authed, user.id, progress_all)
                st.session_state["show_goal_settings"] = False
                st.rerun()
        with cclose:
            if st.button("닫기", use_container_width=True, key="hub_goal_close"):
                st.session_state["show_goal_settings"] = False
                st.rerun()


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

    # ---- Smart CTA (button set) ----
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

    st.markdown(f"<div class='cta_box cta_box_top'><b>{msg}</b></div>", unsafe_allow_html=True)

    if st.button(f"{rec_emoji} {rec_label} 시작", use_container_width=True, key="hub_cta_primary"):
        st.session_state["p"] = rec_kind
        st.query_params["p"] = rec_kind
        st.rerun()

    # ---- Wrong routine CTA (compact) ----
    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
    c_wr1, c_wr2 = st.columns([2, 1])
    with c_wr1:
        st.markdown("<div class='h-sub' style='margin-top:.10rem'>오답 루틴(반복오답)으로 복습까지 마무리해요.</div>", unsafe_allow_html=True)
    with c_wr2:
        if st.button("🔁 반복오답 루틴", use_container_width=True, key="hub_cta_wrongs"):
            st.query_params["p"] = "my"
            st.session_state["p"] = "my"
            st.session_state["hub_page"] = "my"
            # mypage 쪽에서 사용하면 자동 반영 (없어도 무해)
            st.session_state["mypage_tab"] = "wrongs"
            st.session_state["wrongs_repeat_only"] = True
            st.rerun()


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

# ✅ show unread message popup once per session
try:
    uid_now = st.session_state.get("user_id") or getattr(user, "id", None)
    if uid_now and sb_authed:
        um_popup_unread_once(sb_authed, str(uid_now))
except Exception:
    pass

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
  background: rgba(17,17,17,0.43);
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

    is_admin = bool(st.session_state.get("is_admin", False))
    base = _hub_build_base_qs()
    href_admin = "?" + base + "p=admin"

    gear = f'<a class="hub-admin-gear" href="{href_admin}" target="_self" title="관리자">⚙️</a>' if is_admin else ""

    st.markdown(
        f"""
<style>
.hub-plan-wrap{{display:flex;justify-content:flex-start;margin-top:0.05rem;margin-bottom:-0.55rem;}}
.hub-plan-pill{{display:inline-flex;align-items:center;gap:.45rem;padding:.28rem .55rem;border-radius:999px;
  border:1px solid rgba(0,0,0,.10);font-size:.86rem;opacity:.92;background:rgba(0,0,0,.02);}}
.hub-admin-gear{{display:inline-flex;align-items:center;justify-content:center;margin-left:8px;width:28px;height:28px;border-radius:999px;
  text-decoration:none !important;border:1px solid rgba(0,0,0,.10);background:rgba(0,0,0,.02);font-size:16px;line-height:1;}}
.hub-admin-gear:hover{{background:rgba(0,0,0,.04);}}
.hub-plan-pill a{{text-decoration:none !important;}}
</style>
<div class="hub-plan-wrap">
  <div class="hub-plan-pill">{txt}{gear}</div>
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

    # ----------------------------
    # 💬 NAVER Talk FAB (default OFF) — saved in profiles.progress
    # ----------------------------
    naver_default = bool(progress_all.get('naver_talk_fab_enabled', False))
    st.markdown('---')
    st.markdown('### 💬 NAVER Talk 버튼')
    yn = st.radio('표시 여부', options=['N', 'Y'], index=(1 if naver_default else 0), horizontal=True, key='hub_naver_talk_yn')

    if st.button("저장", use_container_width=True, key="hub_rem_save"):
        try:
            hh, mm = [int(x) for x in time_str.split(":")]
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            st.error("시간 형식이 올바르지 않습니다. 예) 09:00")
            st.stop()

        progress_all["reminder"] = {"enabled": bool(enabled), "time": f"{hh:02d}:{mm:02d}"}
        progress_all['naver_talk_fab_enabled'] = (yn == 'Y')
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

    # --- Pretty login card (Hub) ---
    st.markdown(
        """
<style>
/* === Hotena Login (pretty card) === */
.ha-login-bg{
  margin-top: .10rem;
  padding: .25rem 0 .70rem;
}
.ha-login-card{
  border: 1px solid rgba(49,51,63,0.14);
  border-radius: 18px;
  padding: 18px 16px 14px;
  background: rgba(255,255,255,0.85);
  box-shadow: 0 14px 38px rgba(0,0,0,0.08);
}
.ha-login-head{
  display:flex; align-items:center; gap:10px;
  margin-bottom: 10px;
}
.ha-login-logo{
  width: 40px; height: 40px; border-radius: 14px;
  display:flex; align-items:center; justify-content:center;
  border: 1px solid rgba(0,0,0,0.08);
  background: linear-gradient(135deg, rgba(46,124,246,0.16), rgba(0,0,0,0.02));
  font-weight: 900;
  font-size: 18px;
}
.ha-login-ttl{margin:0; line-height:1.05;}
.ha-login-ttl b{font-size:1.18rem; font-weight: 900;}
.ha-login-ttl div{font-size:.90rem; opacity:.72; margin-top:.10rem;}
.ha-login-note{
  font-size: .86rem;
  opacity: .74;
  margin: .10rem 0 .55rem;
}
.ha-login-foot{
  font-size: .82rem;
  opacity: .70;
  margin-top: .55rem;
}
</style>
<div class="ha-login-bg">
  <div class="ha-login-card">
    <div class="ha-login-head">
      <div class="ha-login-logo">は</div>
      <div class="ha-login-ttl">
        <b>하테나</b>
        <div>단어 · 한자 · 회화 루틴을 한 곳에서</div>
      </div>
    </div>
    <div class="ha-login-note">계정을 만들면 학습 기록이 저장되고, 기기/브라우저가 달라도 이어서 할 수 있어요.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    def _auth_success(res):
        st.session_state["user"] = res.user
        st.session_state["access_token"] = res.session.access_token
        st.session_state["refresh_token"] = res.session.refresh_token

        # cookies
        try:
            cookies["access_token"] = res.session.access_token
            cookies["refresh_token"] = res.session.refresh_token
            _cookies_save_once_per_run()
        except Exception:
            pass

        # ✅ persist encrypted tokens for refresh-proof login
        try:
            st.query_params["rt"] = _enc(res.session.refresh_token)
            st.query_params["at"] = _enc(res.session.access_token)
            _js_set_localstorage("hotena_rt", st.query_params.get("rt", ""))
            _js_set_localstorage("hotena_at", st.query_params.get("at", ""))
        except Exception:
            pass

        st.rerun()

    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

    with tab_login:
        with st.form("login_form_pretty", clear_on_submit=False):
            email = st.text_input("이메일", key="hub_email", placeholder="example@email.com")
            pw = st.text_input("비밀번호", type="password", key="hub_pw", placeholder="비밀번호")
            submit = st.form_submit_button("로그인", use_container_width=True)

        if submit:
            if not email or not pw:
                st.error("이메일/비밀번호를 입력해 주세요.")
                st.stop()
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                if getattr(res, "session", None) and getattr(res.session, "access_token", None):
                    _auth_success(res)
                else:
                    st.error("로그인에 실패했습니다. 이메일/비밀번호를 확인해 주세요.")
            except Exception:
                st.error("로그인에 실패했습니다. 이메일/비밀번호를 확인해 주세요.")

        st.markdown('<div class="ha-login-foot">※ 처음 이용이라면 <b>회원가입</b> 탭에서 계정을 만들어 주세요.</div>', unsafe_allow_html=True)

    with tab_signup:
        with st.form("signup_form_pretty", clear_on_submit=False):
            email2 = st.text_input("이메일", key="hub_email2", placeholder="example@email.com")
            pw2 = st.text_input("비밀번호", type="password", key="hub_pw2", placeholder="비밀번호 (6자 이상 권장)")
            submit2 = st.form_submit_button("회원가입", use_container_width=True)

        if submit2:
            if not email2 or not pw2:
                st.error("이메일/비밀번호를 입력해 주세요.")
                st.stop()
            try:
                res = sb.auth.sign_up({"email": email2, "password": pw2})
                if getattr(res, "session", None) and getattr(res.session, "access_token", None):
                    _auth_success(res)
                else:
                    # Some Supabase setups require email confirmation and may not return a session.
                    st.success("회원가입 요청이 완료되었습니다. 이메일 인증이 필요할 수 있어요.")
            except Exception:
                st.error("회원가입에 실패했습니다. 이미 가입된 이메일이거나 비밀번호 조건이 맞지 않을 수 있어요.")
else:
    # ✅ Fallback: unknown page -> go home
    st.session_state["hub_page"] = "home"
    render_home_dashboard(sb_authed, user)


# ✅ Always render bottom-right '맨 위로' shortcut
try:
    render_float_top_anchor_button()
except Exception:
    pass
