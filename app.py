# ============================================================
# OK [A] Imports + Page Config (파일 최상단, st.* 호출보다 먼저)
# ============================================================
from pathlib import Path
import random
import pandas as pd
import streamlit as st

import core
# -------------------------------
# OK 한자 헤더 중복 방지 플래그
# -------------------------------
if "KANJI_HEADER_RENDERED" not in st.session_state:
    st.session_state["KANJI_HEADER_RENDERED"] = False

import unicodedata
from streamlit_cookies_manager import EncryptedCookieManager
import streamlit.components.v1 as components
from collections import Counter
import time
import traceback
import base64
import io
import textwrap

# NOTE: page config is handled by home.py
if not st.session_state.get("_page_config_set"):
    st.set_page_config(page_title="Hotena", layout="centered")
# HN_RADIO_COMPACT_V4
st.markdown("""<style>

/* ===========================
   HN RADIO COMPACT (v4)
   목표: "선택 후"의 촘촘한 느낌을 기본값으로 고정
   - Streamlit 기본 폰트/색상 유지
   - 선택 전/후 간격 동일
   =========================== */
div[data-testid="stRadio"] div[role="radiogroup"]{
  gap: 0px !important;
}

/* 각 보기(라디오 1개)의 기본 간격을 '촘촘하게' */
div[data-testid="stRadio"] div[data-baseweb="radio"]{
  margin: 0 0 0.28rem 0 !important;   /* ✅ 기본 간격을 선택 후 느낌으로 */
  padding: 0 !important;
}

/* 내부 래퍼 여백 제거(브라우저/선택상태에 따른 흔들림 방지) */
div[data-testid="stRadio"] div[data-baseweb="radio"] > div{
  padding: 0 !important;
}

/* 글줄 높이도 살짝 컴팩트하게(선택 전/후 동일) */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] span{
  font-weight: inherit !important;
  line-height: 1.32 !important;
}

</style>""", unsafe_allow_html=True)


if not st.session_state.get("_headbar_css_injected"):
    # Inject into *parent* document head so CSS affects the whole app.
    components.html(
        """
<script>
(function(){
  const doc = (window.parent && window.parent.document) ? window.parent.document : document;

  // 1) Fonts (once)
  if (!doc.getElementById("ha-font-preconnect-1")) {
    const l1 = doc.createElement("link");
    l1.id = "ha-font-preconnect-1";
    l1.rel = "preconnect";
    l1.href = "https://fonts.googleapis.com";
    doc.head.appendChild(l1);
  }
  if (!doc.getElementById("ha-font-preconnect-2")) {
    const l2 = doc.createElement("link");
    l2.id = "ha-font-preconnect-2";
    l2.rel = "preconnect";
    l2.href = "https://fonts.gstatic.com";
    l2.crossOrigin = "anonymous";
    doc.head.appendChild(l2);
  }
  if (!doc.getElementById("ha-font-css")) {
    const l3 = doc.createElement("link");
    l3.id = "ha-font-css";
    l3.rel = "stylesheet";
    l3.href = "https://fonts.googleapis.com/css2?family=Kosugi+Maru&family=Noto+Sans+JP:wght@400;500;700;800&display=swap";
    doc.head.appendChild(l3);
  }

  // 2) CSS (once)
  if (!doc.getElementById("ha-headbar-css")) {
    const style = doc.createElement("style");
    style.id = "ha-headbar-css";
    style.textContent = `
:root{
  --jp-rounded: "Noto Sans JP","Kosugi Maru","Hiragino Sans","Yu Gothic","Meiryo",sans-serif;
}
.jp, .jp *{
  font-family: var(--jp-rounded) !important;
  line-height:1.7;
  letter-spacing:.2px;
}

/* 상단 환영바 (hotena_basic 동일) */
.headbar{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  margin: 0px 0 12px 0;
}
.headtitle{
  font-size:32px;
  font-weight:900;
  line-height:1.15;
  white-space: nowrap;
}
.headhello{
  font-size: 13px;
  font-weight:700;
  opacity:.88;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 52%;
}
.headhello .mail{
  font-weight:600;
  opacity:.75;
  margin-left:8px;
}

@media (max-width: 760px){
  .headhello .mail{ display:none !important; }
  .headhello{ font-size:11px; }
  .headtitle{ font-size:22px; }
}
`;
    doc.head.appendChild(style);
  }
})();
</script>
""",
        height=0,
    )
    st.session_state["_headbar_css_injected"] = True
st.session_state["_top_compact_css_applied"] = True

st.session_state["_page_config_set"] = True
# ============================================================
# OK [SOUND] 사운드 유틸 (모바일 자동재생 정책 대응)
# ============================================================
# ============================================================
# ✅ SFX (효과음) — 중앙 통제: core.py
# - 토글: st.session_state.sfx_enabled (기본 ON)
# - 재생: core.play_sfx("correct"|"wrong"|"reward"|"click")
# - 제출 후 1회: core.play_sfx_once(key, name)
# ============================================================

def render_sound_toggle():
    # Hub mode: sound toggle is rendered in home.py (plan pill)
    if st.session_state.get("HUB_MODE", False):
        return

    # 기존 호환: sound_enabled 유지(다른 코드가 참조할 수 있음)
    if "sound_enabled" not in st.session_state:
        st.session_state.sound_enabled = core.is_sfx_enabled(True)

    c1, c2, c3 = st.columns([1.4, 4.6, 4.0], vertical_alignment="center")
    with c1:
        v = st.toggle("🔊", value=bool(st.session_state.sound_enabled), label_visibility="collapsed")
        st.session_state.sound_enabled = bool(v)
        core.set_sfx_enabled(bool(v))
    with c2:
        st.caption("소리 " + ("ON" if core.is_sfx_enabled(True) else "OFF"))
    with c3:
        # 사용자 클릭으로 한 번 재생(권한/허용 트리거)
        if core.is_sfx_enabled(True):
            if st.button("🔈 테스트", use_container_width=True, key="btn_sound_test"):
                core.play_sfx("click")

def sfx(event: str):
    """Backward-compat wrapper (perfect/correct/wrong)."""
    mp = {"perfect": "reward", "correct": "correct", "wrong": "wrong"}
    core.play_sfx(mp.get(str(event).strip().lower(), "click"))


def scroll_to_top(nonce: int = 0):
    components.html(
        f"""
        <script>
        (function () {{
          const doc = window.parent.document;
          const targets = [
            doc.querySelector('[data-testid="stAppViewContainer"]'),
            doc.querySelector('[data-testid="stMain"]'),
            doc.querySelector('section.main'),
            doc.documentElement,
            doc.body
          ].filter(Boolean);

          const go = () => {{
            try {{
              const top = doc.getElementById("__TOP__");
              if (top) top.scrollIntoView({{behavior: "auto", block: "start"}});

              targets.forEach(t => {{
                if (t && typeof t.scrollTo === "function") t.scrollTo({{top: 0, left: 0, behavior: "auto"}});
                if (t) t.scrollTop = 0;
              }});
              window.parent.scrollTo(0, 0);
              window.scrollTo(0, 0);
            }} catch(e) {{}}
          }};

          go();
          requestAnimationFrame(go);
          setTimeout(go, 50);
          setTimeout(go, 150);
          setTimeout(go, 350);
          setTimeout(go, 800);
        }})();
        </script>
        <!-- nonce:{nonce} -->
        """,
        height=0,
        scrolling=False,
    )

def render_floating_scroll_top():
    components.html(
        """
<script>
(function(){
  const doc = window.parent.document;
  if (doc.getElementById("__FAB_TOP__")) return;

  const btn = doc.createElement("button");
  btn.id = "__FAB_TOP__";
  btn.textContent = "↑";

  btn.style.position = "fixed";
  btn.style.right = "14px";
  btn.style.zIndex = "2147483647";
  btn.style.width = "46px";
  btn.style.height = "46px";
  btn.style.borderRadius = "999px";
  btn.style.border = "1px solid rgba(120,120,120,0.25)";
  btn.style.background = "rgba(0,0,0,0.55)";
  btn.style.color = "#fff";
  btn.style.fontSize = "18px";
  btn.style.fontWeight = "900";
  btn.style.boxShadow = "0 10px 22px rgba(0,0,0,0.25)";
  btn.style.cursor = "pointer";
  btn.style.userSelect = "none";
  btn.style.display = "flex";
  btn.style.alignItems = "center";
  btn.style.justifyContent = "center";
  btn.style.opacity = "0";

  const applyDeviceVisibility = () => {
    try {
      const w = window.parent.innerWidth || window.innerWidth;
      if (w >= 801) btn.style.display = "none";
      else btn.style.display = "flex";
    } catch(e) {}
  };

  const goTop = () => {
    try {
      const top = doc.getElementById("__TOP__");
      if (top) top.scrollIntoView({behavior:"smooth", block:"start"});

      const targets = [
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.querySelector('[data-testid="stMain"]'),
        doc.querySelector('section.main'),
        doc.documentElement,
        doc.body
      ].filter(Boolean);

      targets.forEach(t => {
        if (t && typeof t.scrollTo === "function") t.scrollTo({top:0, left:0, behavior:"smooth"});
        if (t) t.scrollTop = 0;
      });

      window.parent.scrollTo(0,0);
      window.scrollTo(0,0);
    } catch(e) {}
  };

  btn.addEventListener("click", goTop);

  const mount = () => doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;

  const BASE = 18;
  const EXTRA = 34;

  const reposition = () => {
    try {
      const vv = window.parent.visualViewport || window.visualViewport;
      const innerH = window.parent.innerHeight || window.innerHeight;
      const hiddenBottom = vv ? Math.max(0, innerH - vv.height - (vv.offsetTop || 0)) : 0;
      btn.style.bottom = (BASE + EXTRA + hiddenBottom) + "px";
      btn.style.opacity = "1";
    } catch(e) {
      btn.style.bottom = "220px";
      btn.style.opacity = "1";
    }
    applyDeviceVisibility();
  };

  const tryAttach = (n=0) => {
    const root = mount();
    if (!root) {
      if (n < 30) return setTimeout(() => tryAttach(n+1), 50);
      return;
    }
    root.appendChild(btn);
    reposition();
    setTimeout(reposition, 50);
    setTimeout(reposition, 200);
    setTimeout(reposition, 600);
  };

  tryAttach();
  window.parent.addEventListener("resize", reposition, {passive:true});

  const vv = window.parent.visualViewport || window.visualViewport;
  if (vv) {
    vv.addEventListener("resize", reposition, {passive:true});
    vv.addEventListener("scroll", reposition, {passive:true});
  }
})();
</script>
        """,
        height=0,
        scrolling=False,
    )
if not st.session_state.get("HUB_MODE", False):
    if not st.session_state.get("_fab_top_injected", False):
        render_floating_scroll_top()
        st.session_state["_fab_top_injected"] = True
if st.session_state.get("_scroll_top_once"):
    st.session_state["_scroll_top_once"] = False
    st.session_state["_scroll_top_nonce"] = st.session_state.get("_scroll_top_nonce", 0) + 1
    scroll_to_top(nonce=st.session_state["_scroll_top_nonce"])

# ============================================================
# OK Cookies / Supabase (통합: core.ensure_core)
# ============================================================
core.ensure_core(cookie_prefix="hotena_beginner_", localstorage_keys=("hotena_rt","hotena_at"))
cookies = st.session_state.get("cookies")
sb = st.session_state.get("sb")

# ============================================================
# OK Supabase 연결
# ============================================================
# Supabase client is provided by hub (home.py)
# ============================================================
# OK 상수/설정
# ============================================================
SHOW_POST_SUBMIT_UI = "N"
SHOW_NAVER_TALK = "Y"
NAVER_TALK_URL = "https://talk.naver.com/W45141"
APP_URL = "https://hotenaquiztestapp-5wiha4zfuvtnq4qgxdhq72.streamlit.app/"
KST_TZ = "Asia/Seoul"

N = 10
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_kanji.csv"

quiz_label_map = {
    "reading": "발음",
    "meaning": "뜻",
    "kr2jp": "한→일",
}
quiz_label_for_table = quiz_label_map.copy()

QUIZ_TYPES_USER = ["reading", "meaning", "kr2jp"]
QUIZ_TYPES_ADMIN = ["reading", "meaning", "kr2jp"]

LEVEL_OPTIONS = ["N5", "N4", "N3", "N2", "N1"]
LEVEL_LABEL_MAP = {lv: lv for lv in LEVEL_OPTIONS}

# OK 세션 기본값(가장 중요)
if "quiz_type" not in st.session_state:
    st.session_state.quiz_type = "reading"
if "level" not in st.session_state:
    st.session_state.level = "N5"

# (혹시 이상값이 들어올 때 안전장치)
if st.session_state.level not in LEVEL_OPTIONS:
    st.session_state.level = "N5"
if st.session_state.quiz_type not in QUIZ_TYPES_USER:
    st.session_state.quiz_type = "reading"
  
# ============================================================
# OK Utils: 위젯 잔상(q_...) 제거
# ============================================================
def clear_question_widget_keys():
    keys_to_del = [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith("q_")]
    for k in keys_to_del:
        st.session_state.pop(k, None)

def mastery_key(qtype: str | None = None, level: str | None = None) -> str:
    qt = qtype or st.session_state.get("quiz_type", "reading")
    lv = (level or st.session_state.get("level", "N5")).upper()
    return f"{lv}__{qt}"

def ensure_mastered_words_shape():
    if "mastered_words" not in st.session_state or not isinstance(st.session_state.mastered_words, dict):
        st.session_state.mastered_words = {}
    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        st.session_state.mastered_words.setdefault(mastery_key(qt), set())

def ensure_excluded_wrong_words_shape():
    if "excluded_wrong_words" not in st.session_state or not isinstance(st.session_state.excluded_wrong_words, dict):
        st.session_state.excluded_wrong_words = {}
    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        st.session_state.excluded_wrong_words.setdefault(mastery_key(qt), set())

def ensure_mastery_banner_shape():
    if "mastery_banner_shown" not in st.session_state or not isinstance(st.session_state.mastery_banner_shown, dict):
        st.session_state.mastery_banner_shown = {}
    if "mastery_done" not in st.session_state or not isinstance(st.session_state.mastery_done, dict):
        st.session_state.mastery_done = {}

    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        k = mastery_key(qt)
        st.session_state.mastery_banner_shown.setdefault(k, False)
        st.session_state.mastery_done.setdefault(k, False)

# ============================================================
# OK [G] Answers 동기화 + Progress save helper
# ============================================================
def sync_answers_from_widgets():
    qv = st.session_state.get("quiz_version", 0)
    quiz = st.session_state.get("quiz", [])
    if not isinstance(quiz, list):
        return

    answers = st.session_state.get("answers")
    if not isinstance(answers, list) or len(answers) != len(quiz):
        st.session_state.answers = [None] * len(quiz)

    for idx in range(len(quiz)):
        widget_key = f"q_{qv}_{idx}"
        if widget_key in st.session_state:
            st.session_state.answers[idx] = st.session_state[widget_key]

def mark_progress_dirty():
    st.session_state.progress_dirty = True
    st.session_state._progress_dirty_ts = time.time()

    sb_authed_local = core.get_authed_sb()
    u = st.session_state.get("user")
    if (sb_authed_local is None) or (u is None):
        return

    now = time.time()
    last = st.session_state.get("_last_progress_save_ts", 0.0)
    if now - last < 10.0:
        return

    try:
        save_progress_to_db(sb_authed_local, u.id)
        st.session_state._last_progress_save_ts = now
        st.session_state.progress_dirty = False
    except Exception:
        pass

def start_quiz_state(quiz_list: list, qtype: str, clear_wrongs: bool = True):
    st.session_state.quiz_version = int(st.session_state.get("quiz_version", 0)) + 1
    st.session_state.quiz_type = qtype

    if not isinstance(quiz_list, list):
        quiz_list = []

    st.session_state.quiz = quiz_list
    st.session_state.answers = [None] * len(quiz_list)

    st.session_state.submitted = False
    st.session_state.saved_this_attempt = False
    st.session_state.stats_saved_this_attempt = False
    st.session_state.session_stats_applied_this_attempt = False

    if clear_wrongs:
        st.session_state.wrong_list = []

# ============================================================
# OK JWT 만료 감지 + 세션 갱신 + DB 호출 래퍼
# ============================================================
# ============================================================
# OK [H] Auth: JWT 만료 감지 + refresh + get_authed_sb
# ============================================================
def is_jwt_expired_error(e: Exception) -> bool:
    msg = str(e).lower()
    return ("jwt expired" in msg) or ("pgrst303" in msg)

def clear_auth_everywhere():
    try:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        cookies.save()
    except Exception:
        pass

    for k in [
        "user", "access_token", "refresh_token",
        "login_email", "email_link_notice_shown",
        "auth_mode", "signup_done", "last_signup_ts",
        "page",
        "quiz", "answers", "submitted", "wrong_list",
        "quiz_version", "quiz_type",
        "saved_this_attempt", "stats_saved_this_attempt",
        "history", "wrong_counter", "total_counter",
        "attendance_checked", "streak_count", "did_attend_today",
        "is_admin_cached",
        "session_stats_applied_this_attempt",
        "mastered_words",
        "progress_restored", "pool_ready",
        "_sb_authed", "_sb_authed_token",
        "excluded_wrong_words",
        "mastery_banner_shown", "mastery_done",
    ]:
        st.session_state.pop(k, None)

def run_db(callable_fn):
    try:
        return callable_fn()
    except Exception as e:
        if is_jwt_expired_error(e):
            ok = refresh_session_from_cookie_if_needed(force=True)
            if ok:
                st.rerun()
            st.warning("세션이 만료되었습니다. 다시 로그인해 주세요.")
            # (자동 로그아웃/쿠키 삭제는 사용자가 로그아웃을 눌렀을 때만 수행)
            st.rerun()
        raise

def refresh_session_from_cookie_if_needed(force: bool = False) -> bool:
    if not force and st.session_state.get("user") and st.session_state.get("access_token"):
        return True

    rt = cookies.get("refresh_token")
    at = cookies.get("access_token")

    if rt:
        try:
            refreshed = sb.auth.refresh_session(rt)
            if refreshed and refreshed.session and refreshed.session.access_token:
                st.session_state.user = refreshed.user
                st.session_state.access_token = refreshed.session.access_token
                st.session_state.refresh_token = refreshed.session.refresh_token

                u_email = getattr(refreshed.user, "email", None)
                if u_email:
                    st.session_state["login_email"] = u_email.strip()

                cookies["access_token"] = refreshed.session.access_token
                cookies["refresh_token"] = refreshed.session.refresh_token
                cookies.save()
                return True
        except Exception:
            pass

    if at:
        try:
            u = sb.auth.get_user(at)
            user_obj = getattr(u, "user", None) or getattr(u, "data", None) or None
            if user_obj:
                st.session_state.user = user_obj
                st.session_state.access_token = at
                if rt:
                    st.session_state.refresh_token = rt
                u_email = getattr(user_obj, "email", None)
                if u_email:
                    st.session_state["login_email"] = u_email.strip()
                return True
        except Exception:
            pass

    return False

def to_kst_naive(x):
    ts = pd.to_datetime(x, utc=True, errors="coerce")
    if isinstance(ts, pd.Series):
        return ts.dt.tz_convert(KST_TZ).dt.tz_localize(None)
    if pd.isna(ts):
        return ts
    return ts.tz_convert(KST_TZ).tz_localize(None)

# ============================================================
# OK DB 함수 (기존 그대로 활용)
# ============================================================
def delete_all_learning_records(sb_authed, user_id):
    sb_authed.table("quiz_attempts").delete().eq("user_id", user_id).execute()
    clear_progress_in_db(sb_authed, user_id)

def ensure_profile(sb_authed, user):
    try:
        sb_authed.table("profiles").upsert(
            {"id": user.id, "email": getattr(user, "email", None)},
            on_conflict="id",
        ).execute()
    except Exception:
        pass

def mark_attendance_once(sb_authed):
    if st.session_state.get("attendance_checked"):
        return None
    try:
        res = sb_authed.rpc("mark_attendance_kst", {}).execute()
        st.session_state.attendance_checked = True
        return res.data[0] if res.data else None
    except Exception:
        st.session_state.attendance_checked = True
        return None

def save_attempt_to_db(sb_authed, user_id, user_email, level, quiz_type, quiz_len, score, wrong_list):
    # OK pos_mode 컬럼명은 그대로 두되, 값은 quiz_type 넣어서 테이블 변경 없이 유지
    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "level": level,
        "pos_mode": quiz_type,
        "quiz_len": int(quiz_len),
        "score": int(score),
        "wrong_count": int(len(wrong_list)),
        "wrong_list": wrong_list,
    }
    sb_authed.table("quiz_attempts").insert(payload).execute()

def fetch_recent_attempts(sb_authed, user_id, limit=10):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, level, pos_mode, quiz_len, score, wrong_count, wrong_list")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

def fetch_all_attempts_admin(sb_authed, limit=500):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, user_email, level, pos_mode, quiz_len, score, wrong_count")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

def fetch_is_admin_from_db(sb_authed, user_id):
    try:
        res = sb_authed.table("profiles").select("is_admin").eq("id", user_id).single().execute()
        if res and res.data and "is_admin" in res.data:
            return bool(res.data["is_admin"])
    except Exception:
        pass
    return False

def build_word_results_bulk_payload(quiz: list[dict], answers: list, quiz_type: str, level: str) -> list[dict]:
    items = []
    for idx, q in enumerate(quiz):
        word_key = (str(q.get("jp_word", "")).strip() or str(q.get("reading", "")).strip())
        if not word_key:
            continue

        picked = answers[idx] if idx < len(answers) else None
        is_correct = (picked == q.get("correct_text"))

        items.append(
            {
                "word_key": word_key,
                "level": str(level),
                "pos": "",  # OK 한자퀴즈는 품사 없음 → 빈 값
                "quiz_type": str(quiz_type),
                "is_correct": bool(is_correct),
            }
        )
    return items

# ============================================================
# OK Progress (DB 저장/복원)
# ============================================================
def save_progress_to_db(sb_authed, user_id: str):
    if "quiz" not in st.session_state or "answers" not in st.session_state:
        return

    payload = {
        "quiz_type": st.session_state.get("quiz_type"),
        "quiz_version": int(st.session_state.get("quiz_version", 0) or 0),
        "quiz": st.session_state.get("quiz"),
        "answers": st.session_state.get("answers"),
        "submitted": bool(st.session_state.get("submitted", False)),
    }

    sb_authed.table("profiles").upsert(
        {"id": user_id, "progress": payload},
        on_conflict="id",
    ).execute()

def clear_progress_in_db(sb_authed, user_id: str):
    sb_authed.table("profiles").upsert(
        {"id": user_id, "progress": None},
        on_conflict="id",
    ).execute()

def restore_progress_from_db(sb_authed, user_id: str):
    try:
        res = (
            sb_authed.table("profiles")
            .select("progress")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception:
        return

    if not res or not res.data:
        return

    progress = res.data.get("progress")
    if not progress:
        return

    st.session_state.quiz_type = progress.get("quiz_type", st.session_state.get("quiz_type", "reading"))
    st.session_state.quiz_version = int(progress.get("quiz_version", st.session_state.get("quiz_version", 0) or 0))
    st.session_state.quiz = progress.get("quiz", st.session_state.get("quiz"))
    st.session_state.answers = progress.get("answers", st.session_state.get("answers"))
    st.session_state.submitted = bool(progress.get("submitted", st.session_state.get("submitted", False)))

    if isinstance(st.session_state.quiz, list):
        qlen = len(st.session_state.quiz)
        if not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != qlen:
            st.session_state.answers = [None] * qlen

# ============================================================
# OK Admin 설정 (DB ONLY)
# ============================================================
def is_admin() -> bool:
    cached = st.session_state.get("is_admin_cached")
    if cached is not None:
        return bool(cached)

    u = st.session_state.get("user")
    if u is None:
        st.session_state["is_admin_cached"] = False
        return False

    sb_authed_local = core.get_authed_sb()
    if sb_authed_local is None:
        st.session_state["is_admin_cached"] = False
        return False

    val = fetch_is_admin_from_db(sb_authed_local, u.id)
    st.session_state["is_admin_cached"] = val
    return bool(val)

def get_available_quiz_types() -> list[str]:
    return QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER

# ============================================================
# OK 로그인 UI (원본 유지)
# ============================================================
def auth_box():
    st.markdown("<div style='max-width:520px; margin:0 auto;'>", unsafe_allow_html=True)

    st.markdown(
        '<div class="jp" style="font-weight:900; font-size:16px; margin:6px 0 6px 0;">로그인</div>',
        unsafe_allow_html=True
    )

    qp = st.query_params
    came_from_email_link = any(k in qp for k in ["code", "token", "type", "access_token", "refresh_token"])
    if came_from_email_link and not st.session_state.get("email_link_notice_shown"):
        st.session_state.email_link_notice_shown = True
        st.session_state.auth_mode = "login"
        st.success("이메일 인증(또는 링크 확인)이 완료되었습니다. 이제 로그인해 주세요.")

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    mode = st.radio(
        label="",
        options=["login", "signup"],
        format_func=lambda x: "로그인" if x == "login" else "회원가입",
        horizontal=True,
        key="auth_mode_radio",
        index=0 if st.session_state.auth_mode == "login" else 1,
    )
    st.session_state.auth_mode = mode

    if st.session_state.get("signup_done"):
        st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요. 메일함을 확인한 뒤 로그인해 주세요.")
        st.session_state.signup_done = False

    if mode == "login":
        email = st.text_input("이메일", key="login_email_input")
        pw = st.text_input("비밀번호", type="password", key="login_pw_input")

        st.caption("비밀번호는 **회원가입 때 8자리 이상**으로 설정했을 가능성이 큽니다.")
        if pw and len(pw) < 8:
            st.warning(f"입력하신 비밀번호가 {len(pw)}자리입니다. 회원가입 때 8자리 이상으로 설정하셨다면 더 길게 입력해 주세요.")

        if st.button("로그인", use_container_width=True, key="btn_login"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()

            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})

                st.session_state.user = res.user
                st.session_state["login_email"] = email.strip()

                if res.session and res.session.access_token:
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token

                    cookies["access_token"] = res.session.access_token
                    cookies["refresh_token"] = res.session.refresh_token
                    cookies.save()
                else:
                    st.warning("로그인은 되었지만 세션 토큰이 없습니다. 이메일 인증 상태를 확인해주세요.")
                    st.session_state.access_token = None
                    st.session_state.refresh_token = None

                st.session_state.pop("is_admin_cached", None)
                st.success("로그인 완료!")
                st.rerun()

            except Exception:
                st.error("로그인 실패: 이메일/비밀번호 또는 이메일 인증 상태를 확인해주세요.")
                st.stop()

    else:
        email = st.text_input("이메일", key="signup_email")
        pw = st.text_input("비밀번호", type="password", key="signup_pw")

        pw_len = len(pw) if pw else 0
        pw_ok = pw_len >= 8
        email_ok = bool(email and email.strip())

        st.caption("비밀번호는 **8자리 이상**으로 설정해 주세요.")
        if pw and not pw_ok:
            st.warning(f"비밀번호가 너무 짧습니다. (현재 {pw_len}자) 8자리 이상으로 입력해 주세요.")

        if st.button("회원가입", use_container_width=True, disabled=not (email_ok and pw_ok), key="btn_signup"):
            try:
                last = st.session_state.get("last_signup_ts", 0.0)
                now = time.time()
                if now - last < 8:
                    st.warning("요청이 너무 빠릅니다. 잠시 후 다시 시도해주세요.")
                    st.stop()
                st.session_state.last_signup_ts = now

                sb.auth.sign_up(
                    {
                        "email": email,
                        "password": pw,
                        "options": {"email_redirect_to": APP_URL},
                    }
                )

                st.session_state.signup_done = True
                st.session_state.auth_mode = "login"
                st.session_state["login_email"] = email.strip()
                st.rerun()

            except Exception as e:
                msg = str(e).lower()
                if "rate limit" in msg and "email" in msg:
                    st.session_state.auth_mode = "login"
                    st.session_state["login_email"] = email.strip()
                    st.session_state.signup_done = False
                    st.warning("이메일 발송 제한에 걸렸습니다. 잠시 후 다시 시도해주세요.")
                    st.rerun()

                st.error("회원가입 실패(에러 확인):")
                st.exception(e)
                st.stop()

    st.markdown("</div>", unsafe_allow_html=True)

def require_login():
    if st.session_state.get("user") is None:
        st.markdown(
            """
<div class="jp" style="margin: 8px 0 14px 0;">
  <div style="font-weight:900; font-size:22px; line-height:1.15;">
    ✨ 한자 퀴즈
  </div>
  <div style="margin-top:6px; opacity:.85; font-size:13px; line-height:1.55;">
    하루 10문항으로 가볍게 루틴을 만들어요.<br/>
    정답은 저장되고, 오답은 다시 풀 수 있어요.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        auth_box()
        st.stop()

# ============================================================
# OK 네이버톡 배너 (제출 후만)
# ============================================================
def render_naver_talk():
    st.divider()
    st.markdown(
        f"""
<style>
@keyframes floaty {{
  0% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-6px); }}
  100% {{ transform: translateY(0); }}
}}
@keyframes ping {{
  0% {{ transform: scale(1); opacity: 0.9; }}
  70% {{ transform: scale(2.2); opacity: 0; }}
  100% {{ transform: scale(2.2); opacity: 0; }}
}}
.floating-naver-talk,
.floating-naver-talk:visited,
.floating-naver-talk:hover,
.floating-naver-talk:active {{
  position: fixed;
  right: 18px;
  bottom: 90px;
  z-index: 99999;
  text-decoration: none !important;
  color: inherit !important;
}}
.floating-wrap {{
  position: relative;
  animation: floaty 2.2s ease-in-out infinite;
}}
.talk-btn {{
  background: #03C75A;
  color: #fff;
  border: 0;
  border-radius: 999px;
  padding: 14px 18px;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 12px 28px rgba(0,0,0,0.22);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  line-height: 1.1;
  text-decoration: none !important;
}}
.talk-btn:hover {{ filter: brightness(0.95); }}
.talk-text small {{
  display: block;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.95;
  margin-top: 2px;
}}
.badge {{
  position: absolute;
  top: -6px;
  right: -6px;
  width: 12px;
  height: 12px;
  background: #ff3b30;
  border-radius: 999px;
  box-shadow: 0 6px 14px rgba(0,0,0,0.25);
}}
.badge::after {{
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background: rgba(255,59,48,0.55);
  animation: ping 1.2s ease-out infinite;
}}
@media (max-width: 600px) {{
  .floating-naver-talk {{ bottom: 110px; right: 14px; }}
  .talk-btn {{ padding: 13px 16px; font-size: 14px; }}
  .talk-text small {{ font-size: 11px; }}
}}
</style>

<a class="floating-naver-talk" href="{NAVER_TALK_URL}" target="_blank" rel="noopener noreferrer">
  <div class="floating-wrap">
    <span class="badge"></span>
    <button class="talk-btn" type="button">
      <span>💬</span>
      <span class="talk-text">
        1:1 하테나쌤 상담
        <small>수강신청 문의하기</small>
      </span>
    </button>
  </div>
</a>
""",
        unsafe_allow_html=True,
    )

# ============================================================
# OK 상단 카드(관리자/마이페이지/로그아웃)
# ============================================================
def nav_to(page: str, scroll_top: bool = True):
    st.session_state.page = page
    if scroll_top:
        st.session_state["_scroll_top_once"] = True

def nav_logout():
    clear_auth_everywhere()

def render_topcard():
    # HUB에서는 상단 메뉴를 home.py가 책임집니다.
    if st.session_state.get("HUB_MODE"):
        return

    u = st.session_state.get("user")
    if not u:
        return

    email = getattr(u, "email", None) or st.session_state.get("login_email", "")

    st.markdown('<div class="topcard">', unsafe_allow_html=True)

    left, r_admin, r_my, r_logout = st.columns([6.0, 1.2, 2.4, 2.4], vertical_alignment="center")

    with left:
        # OK 왼쪽 '환영합니다/이메일' 제거 (공간만 유지)
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    with r_admin:
        if is_admin():
            st.button("📊", use_container_width=True, help="관리자 대시보드",
                      key="topcard_btn_nav_admin", on_click=nav_to, args=("admin",))
        else:
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    with r_my:
        st.button("📌 마이페이지", use_container_width=True, help="내 학습 기록/오답 TOP10 보기",
                  key="topcard_btn_nav_my", on_click=nav_to, args=("my",))

    with r_logout:
        st.button("🚪 로그아웃", use_container_width=True, help="로그아웃",
                  key="topcard_btn_logout", on_click=nav_logout)

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# OK 로딩: CSV 풀
# ============================================================
READ_KW = dict(
    dtype=str,
    keep_default_na=False,
    na_values=["nan", "NaN", "NULL", "null", "None", "none"],
)

@st.cache_data(show_spinner=False)
def load_pool(csv_path_str: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path_str, **READ_KW)

    # OK 한자 퀴즈 필수 컬럼 (+pos 추가)
    required_cols = {"level", "jp_word", "reading", "meaning", "pos"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV 필수 컬럼 누락: {sorted(list(missing))}")

    # OK pos 정규화 (필수)
    df["pos"] = df["pos"].astype(str).str.strip().str.lower()


    # OK 1) 유니코드 정규화 (Ｎ５ / ｎ４ / 전각 숫자 등 → N5 / N4로 통일)
    def _nfkc(s):
        return unicodedata.normalize("NFKC", str(s or ""))

    lv = df["level"].apply(_nfkc).astype(str).str.upper().str.strip()
    lv = lv.str.replace(" ", "", regex=False)

    # OK 2) 레벨 안에 N1~N5가 있으면 추출
    extracted = lv.str.extract(r"(N[1-5])", expand=False)

    # OK 3) 없으면 숫자만 있는 케이스 처리 ("1"~"5")
    digit_map = {"1": "N1", "2": "N2", "3": "N3", "4": "N4", "5": "N5"}
    only_digit = lv.where(extracted.isna(), "")  # 추출 성공한 행은 비움
    only_digit = only_digit.str.extract(r"^([1-5])$", expand=False)
    digit_fixed = only_digit.map(digit_map)

    # OK 4) 최종 레벨: extracted 우선, 그 다음 digit_fixed, 그래도 없으면 원본 lv
    final_lv = extracted.fillna(digit_fixed).fillna(lv)

    # OK 5) 안전장치: N1~N5 아닌 값은 빈칸 처리
    final_lv = final_lv.where(final_lv.isin(["N1", "N2", "N3", "N4", "N5"]), "")

    df["level"] = final_lv


    df["jp_word"] = df["jp_word"].astype(str).str.strip()
    df["reading"] = df["reading"].astype(str).str.strip()
    df["meaning"] = df["meaning"].astype(str).str.strip()

    # 비어있는 줄 제거(안전)
    df = df[(df["jp_word"] != "") & (df["reading"] != "") & (df["meaning"] != "")].copy()
    return df.reset_index(drop=True)

def ensure_pool_ready():
    if st.session_state.get("pool_ready") and isinstance(st.session_state.get("_pool"), pd.DataFrame):
        return

    try:
        pool = load_pool(str(CSV_PATH))
    except Exception as e:
        st.error(f"단어 데이터 로드 실패: {e}")
        st.stop()

    if len(pool) < N:
        st.error(f"단어가 부족합니다: pool={len(pool)} (N={N})")
        st.stop()

    st.session_state["_pool"] = pool
    st.session_state["pool_ready"] = True
    
    # OK 디버그(관리자만)
    if is_admin():
        with st.expander("🔎 디버그: 레벨별 단어 수", expanded=False):
            pool = st.session_state.get("_pool")
            if isinstance(pool, pd.DataFrame):
                st.write(pool["level"].value_counts(dropna=False))
                st.write("CSV_PATH =", str(CSV_PATH))

# ============================================================
# OK 퀴즈 로직 (한자용) - 3유형 지원 + reading만 패턴 방지(품사별 강도조절)
# ============================================================

import unicodedata
import random
import pandas as pd
import streamlit as st

# -------------------------------
# OK 한자 헤더 중복 방지 플래그
# -------------------------------
if "KANJI_HEADER_RENDERED" not in st.session_state:
    st.session_state["KANJI_HEADER_RENDERED"] = False


def _nfkc_str(x) -> str:
    return unicodedata.normalize("NFKC", str(x or "")).strip()

def _to_hira(s: str) -> str:
    # 카타카나 → 히라가나 (읽기가 카타카나일 가능성 대비)
    s = _nfkc_str(s)
    out = []
    for ch in s:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:  # ァ-ヶ
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)

def _last_char(x) -> str:
    s = _to_hira(_nfkc_str(x))
    return s[-1] if s else ""

def _vowel_group(kana_or_word: str) -> str:
    """
    마지막 글자를 '단(행)'으로 묶기: a/i/u/e/o/n/other
    """
    ch = _last_char(kana_or_word)
    if not ch:
        return "other"

    if ch == "ん":
        return "n"

    # 작은 글자/장음/촉음 등은 other
    if ch in "ぁぃぅぇぉゃゅょっーゎ":
        return "other"

    A = set("あかさたなはまやらわがざだばぱぁゃゎ")
    I = set("いきしちにひみりぎじぢびぴぃ")
    U = set("うくすつぬふむゆるぐずづぶぷぅゅ")
    E = set("えけせてねへめれげぜでべぺぇ")
    O = set("おこそとのほもよろをごぞどぼぽぉょを")

    if ch in A: return "a"
    if ch in I: return "i"
    if ch in U: return "u"
    if ch in E: return "e"
    if ch in O: return "o"
    return "other"

def _uniq(xs):
    out = []
    seen = set()
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _pick_reading_wrongs(
    candidates: list[str],
    correct: str,
    pos: str,
    jp_word: str = "",
    k: int = 3,
    strict_pos: set[str] | None = None,
) -> list[str]:
    """
    OK reading(발음) 오답 선택
    목표: '모양(끝글자) + 끝 2글자(예: わる/りる/るく/きい)' 힌트로 쉽게 못 맞히게 하기

    동사/형용사(특히 い형용사)는:
      1) 끝 2글자 동일 우선 (예: わる, るく, きい)
      2) 부족하면 끝 1글자 동일 (예: る, く, い)
      3) 부족하면 같은 단(행) (u단/e단 등)
      4) 그래도 부족하면 전체 랜덤 (앱이 멈추지 않게)

    그 외 품사(adv/noun 등)는:
      - 위처럼 '끝 통일'을 강제하면 오히려 이상해질 수 있으니,
        마지막 글자 분산을 우선하고, 필요시 랜덤으로 채움.
    """

    def _suffix(x: str, n: int) -> str:
        s = _to_hira(_nfkc_str(x))
        return s[-n:] if len(s) >= n else s

    if strict_pos is None:
        # OK DB pos 라벨에 맞게 자유롭게 추가 가능
        strict_pos = {"v", "verb", "adj", "adj_i", "adj_na", "i_adj", "adj-i"}

    correct_nf = _nfkc_str(correct)
    cands = _uniq([_nfkc_str(c) for c in candidates if _nfkc_str(c) and _nfkc_str(c) != correct_nf])

    if len(cands) < k:
        return []

    # 끝 1글자 / 끝 2글자(= “끝 모양 + 앞 1글자”)를 힌트 차단용으로 사용
    s1 = _suffix(correct_nf, 1)  # ex) る / く / い
    s2 = _suffix(correct_nf, 2)  # ex) わる / りる / るく / きい

    # OK い형용사 자동 판정(한자표기 자체가 〜い로 끝나고, reading도 〜い로 끝나는 경우)
    jp_h = _to_hira(_nfkc_str(jp_word))
    rd_h = _to_hira(correct_nf)
    force_i_adj = (jp_h.endswith("い") and rd_h.endswith("い"))

    # ---------- (A) 동사/형용사 + い형용사 자동: "끝2 → 끝1" 강제 ----------
    if (pos in strict_pos) or force_i_adj:
        same2 = _uniq([c for c in cands if _suffix(c, 2) == s2])
        if len(same2) >= k:
            return random.sample(same2, k)

        same1 = _uniq([c for c in cands if _suffix(c, 1) == s1])
        if len(same1) >= k:
            # 가능하면 끝2 후보를 섞고, 부족하면 끝1에서 채움
            wrongs = same2[:]
            rest = [c for c in same1 if c not in wrongs]
            need = k - len(wrongs)
            if need > 0:
                if len(rest) >= need:
                    wrongs += random.sample(rest, need)
                else:
                    # 끝1에서도 부족하면 전체에서 채움
                    pool_all = [c for c in cands if c not in wrongs]
                    wrongs += random.sample(pool_all, min(need, len(pool_all)))
            return wrongs[:k]

        # 끝1도 부족하면 같은 단(행)으로 완화
        g = _vowel_group(correct_nf)
        vg = _uniq([c for c in cands if _vowel_group(c) == g])
        if len(vg) >= k:
            return random.sample(vg, k)

        # 그래도 부족하면 전체 랜덤 (절대 멈추지 않게)
        return random.sample(cands, k)

    # ---------- (B) 기타 품사: 끝 통일 강제 X, 마지막 글자 분산 ----------
    base = cands[:]
    random.shuffle(base)

    wrongs = []
    seen_last = set()

    for c in base:
        lc = _last_char(c)
        if lc and lc not in seen_last:
            wrongs.append(c)
            seen_last.add(lc)
            if len(wrongs) == k:
                return wrongs

    # 부족하면 랜덤으로 채움
    rest = [c for c in base if c not in wrongs]
    if len(rest) >= (k - len(wrongs)):
        wrongs += random.sample(rest, k - len(wrongs))
        return wrongs

    # 최후: 가능한 만큼이라도 반환(상위에서 안전장치)
    return wrongs

def make_question(row: pd.Series, qtype: str, pool: pd.DataFrame) -> dict:
    jp = str(row.get("jp_word", "")).strip()
    rd = str(row.get("reading", "")).strip()
    mn = str(row.get("meaning", "")).strip()
    lvl = str(row.get("level", "")).strip().upper()
    pos = str(row.get("pos", "")).strip().lower()

    # OK 같은 품사(pos)만으로 보기 후보 풀 만들기
    pool_pos = pool[pool["pos"].astype(str).str.strip().str.lower() == pos].copy()

    if qtype == "reading":
        prompt = f"{jp}의 발음은?"
        correct = rd
        candidates = (
            pool_pos.loc[pool_pos["reading"] != correct, "reading"]
            .dropna().drop_duplicates().tolist()
        )

        # OK reading만: (동사/형용사는 끝모양 통일 / 그 외는 분산) + 실패 시 자동 완화
        wrongs = _pick_reading_wrongs(candidates, correct, pos=pos, jp_word=jp, k=3)
        if len(wrongs) < 3:
            st.error(f"오답 후보 부족(발음): pos={pos}, 후보={len(candidates)}개")
            st.stop()


    elif qtype == "meaning":
        prompt = f"{jp}의 뜻은?"
        correct = mn
        candidates = (
            pool_pos.loc[pool_pos["meaning"] != correct, "meaning"]
            .dropna().drop_duplicates().tolist()
        )

        if len(candidates) < 3:
            st.error(f"오답 후보 부족(뜻): pos={pos}, 후보={len(candidates)}개")
            st.stop()

        wrongs = random.sample(candidates, 3)

    elif qtype == "kr2jp":
        prompt = f"'{mn}'의 일본어(한자)는?"
        correct = jp
        candidates = (
            pool_pos.loc[pool_pos["jp_word"] != correct, "jp_word"]
            .dropna().astype(str).str.strip().tolist()
        )
        candidates = [x for x in dict.fromkeys(candidates) if x]

        if len(candidates) < 3:
            st.error(f"오답 후보 부족(한→일): pos={pos}, 후보={len(candidates)}개")
            st.stop()

        wrongs = random.sample(candidates, 3)

    else:
        raise ValueError(f"Unknown qtype: {qtype}")

    choices = wrongs + [correct]
    random.shuffle(choices)

    return {
        "prompt": prompt,
        "choices": choices,
        "correct_text": correct,
        "jp_word": jp,
        "reading": rd,
        "meaning": mn,
        "level": lvl,
        "pos": pos,
        "qtype": qtype,
    }


# ============================================================
# OK build_quiz / build_quiz_from_wrongs (당신 원본 유지)
#    ※ 아래 함수들은 그대로 두면 됩니다.
# ============================================================

def build_quiz(qtype: str, level: str) -> list[dict]:
    ensure_pool_ready()
    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()

    pool = st.session_state["_pool"]

    level = str(level).strip().upper()
    base_level = pool[pool["level"].astype(str).str.upper() == level].copy()

    if len(base_level) < N:
        st.warning(f"{level} 단어가 부족합니다. (현재 {len(base_level)}개 / 필요 {N}개)")
        return []

    k = mastery_key(qtype=qtype)
    mastered = st.session_state.get("mastered_words", {}).get(k, set())
    excluded = st.session_state.get("excluded_wrong_words", {}).get(k, set())

    blocked = set()
    if mastered:
        blocked |= set(mastered)
    if excluded:
        blocked |= set(excluded)

    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:
        if not blocked:
            return df
        keys = df["jp_word"].astype(str).str.strip()
        return df[~keys.isin(blocked)].copy()

    base = _filter_blocked(base_level)

    if len(base) < N:
        st.session_state.setdefault("mastery_done", {})
        st.session_state.mastery_done[k] = True
        return []

    sampled = base.sample(n=N, replace=False).reset_index(drop=True)
    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]


def build_quiz_from_wrongs(wrong_list: list, qtype: str) -> list:
    ensure_pool_ready()
    pool = st.session_state["_pool"]

    wrong_words = []
    for w in (wrong_list or []):
        key = str(w.get("단어", "")).strip()
        if key:
            wrong_words.append(key)
    wrong_words = list(dict.fromkeys(wrong_words))

    if not wrong_words:
        st.warning("현재 오답 노트가 비어 있어요. 🙂")
        return []

    retry_df = pool[pool["jp_word"].isin(wrong_words)].copy()
    if len(retry_df) == 0:
        st.error("오답 단어를 풀에서 찾지 못했습니다. (jp_word/reading 매칭 확인)")
        st.stop()

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)
    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]


def build_quiz(qtype: str, level: str) -> list[dict]:
    ensure_pool_ready()
    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()

    pool = st.session_state["_pool"]

    # OK 레벨 필터 (N5~N1)
    level = str(level).strip().upper()
    base_level = pool[pool["level"].astype(str).str.upper() == level].copy()

    # 레벨 데이터가 너무 적을 때 안전장치
    if len(base_level) < N:
        st.warning(f"{level} 단어가 부족합니다. (현재 {len(base_level)}개 / 필요 {N}개)")
        return []

    k = mastery_key(qtype=qtype)
    mastered = st.session_state.get("mastered_words", {}).get(k, set())
    excluded = st.session_state.get("excluded_wrong_words", {}).get(k, set())

    blocked = set()
    if mastered:
        blocked |= set(mastered)
    if excluded:
        blocked |= set(excluded)

    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:
        if not blocked:
            return df
        keys = df["jp_word"].astype(str).str.strip()
        return df[~keys.isin(blocked)].copy()

    base = _filter_blocked(base_level)

    # 더 뽑을 단어가 없으면 “정복”
    if len(base) < N:
        st.session_state.setdefault("mastery_done", {})
        st.session_state.mastery_done[k] = True
        return []

    sampled = base.sample(n=N, replace=False).reset_index(drop=True)
    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]

def build_quiz_from_wrongs(wrong_list: list, qtype: str) -> list:
    ensure_pool_ready()
    pool = st.session_state["_pool"]

    wrong_words = []
    for w in (wrong_list or []):
        key = str(w.get("단어", "")).strip()
        if key:
            wrong_words.append(key)
    wrong_words = list(dict.fromkeys(wrong_words))

    if not wrong_words:
        st.warning("현재 오답 노트가 비어 있어요. 🙂")
        return []

    retry_df = pool[pool["jp_word"].isin(wrong_words)].copy()
    if len(retry_df) == 0:
        st.error("오답 단어를 풀에서 찾지 못했습니다. (jp_word/reading 매칭 확인)")
        st.stop()

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)
    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]

# ============================================================
# OK 마이페이지/관리자 (원본 기능 유지, 한자용으로 가벼운 조정)
# ============================================================

def render_admin_dashboard():
    st.subheader("📊 관리자 대시보드")

    if not is_admin():
        st.error("접근 권한이 없습니다.")
        st.session_state.page = "quiz"
        st.stop()

    if st.button("← 돌아가기", use_container_width=True, key="btn_admin_back"):
        st.session_state.page = "quiz"
        st.rerun()

    sb_authed_local = core.get_authed_sb()
    if sb_authed_local is None:
        st.warning("세션 토큰이 없습니다. 다시 로그인해 주세요.")
        return

    st.caption("※ 여기서부터 확장 가능(전체 기록 조회 등).")

def render_my_dashboard():
    st.subheader("📌 내 대시보드")

    if st.button("← 돌아가기", use_container_width=True, key="btn_my_back"):
        if st.session_state.get("HUB_MODE"):
            st.session_state["hub_page"] = "home"
            st.rerun()
        st.session_state.page = "quiz"
        st.rerun()

    u = st.session_state.get("user")
    if not u:
        st.warning("로그인 정보가 없습니다. 다시 로그인해 주세요.")
        st.session_state.page = "quiz"
        st.stop()

    user_id_local = getattr(u, "id", None)
    if not user_id_local:
        st.warning("유저 ID를 찾지 못했습니다. 다시 로그인해 주세요.")
        st.session_state.page = "quiz"
        st.stop()

    sb_authed_local = core.get_authed_sb()
    if sb_authed_local is None:
        st.warning("세션 토큰이 없습니다. 다시 로그인해 주세요.")
        return

    # 🗑️ 전체 학습 기록 완전 초기화
    with st.expander("🗑️ 전체 학습 기록 완전 초기화", expanded=False):
        st.warning(
            "이 작업은 되돌릴 수 없습니다.\n"
            "(최근 기록 / 오답 TOP10 / 진행중 복원까지 모두 초기화됩니다.)"
        )
        agree = st.checkbox("초기화에 동의합니다.", key="chk_reset_all_agree")
        if st.button("🗑️ 지금 완전 초기화", type="primary", use_container_width=True, key="btn_reset_all_records"):
            if not agree:
                st.error("초기화에 동의해 주세요.")
                st.stop()

            try:
                def _delete_all():
                    delete_all_learning_records(sb_authed_local, user_id_local)
                    return True
                run_db(_delete_all)

                clear_question_widget_keys()
                for k in [
                    "history", "wrong_counter", "total_counter",
                    "wrong_list", "quiz", "answers", "submitted",
                    "saved_this_attempt", "stats_saved_this_attempt",
                    "session_stats_applied_this_attempt",
                    "quiz_version",
                    "mastered_words", "mastery_banner_shown", "mastery_done",
                    "progress_restored", "pool_ready",
                    "excluded_wrong_words",
                ]:
                    st.session_state.pop(k, None)

                st.success("전체 학습 기록이 완전 초기화되었습니다.")
                st.session_state.page = "quiz"
                st.rerun()

            except Exception as e:
                st.error("초기화 실패: RLS 정책(삭제 권한) 또는 테이블/컬럼 확인이 필요합니다.")
                st.exception(e)

    def _fetch():
        return fetch_recent_attempts(sb_authed_local, user_id_local, limit=50)

    try:
        res = run_db(_fetch)
    except Exception as e:
        st.info("기록을 불러오지 못했습니다.")
        st.write(str(e))
        return

    if not res.data:
        st.info("아직 저장된 기록이 없습니다. 문제를 풀고 제출하면 기록이 쌓여요.")
        return

    hist = pd.DataFrame(res.data).copy()
    hist["created_at"] = to_kst_naive(hist["created_at"])
    hist["유형"] = hist["pos_mode"].map(lambda x: quiz_label_for_table.get(x, x))
    hist["정답률"] = (hist["score"] / hist["quiz_len"]).fillna(0.0)

    avg_rate = float(hist["정답률"].mean() * 100)
    best = int(hist["score"].max())
    last_score = int(hist.iloc[0]["score"])
    last_total = int(hist.iloc[0]["quiz_len"])

    # OK 마이페이지 상단 3카드 (components.html로 강제 렌더링)
    dashboard_html = f"""
    <style>
    .stat-grid{{
      display:grid;
      grid-template-columns: repeat(3, 1fr);
      gap:12px;
      margin: 6px 0 6px 0;
    }}
    .stat-card{{
      border:1px solid rgba(120,120,120,0.25);
      border-radius:18px;
      padding:14px 14px;
      background: rgba(255,255,255,0.02);
    }}
    .stat-label{{
      font-size:12px;
      font-weight:800;
      opacity:.72;
      line-height:1.2;
    }}
    .stat-value{{
      margin-top:6px;
      font-size:22px;
      font-weight:900;
      line-height:1.1;
    }}
    .stat-sub{{
      margin-top:6px;
      font-size:12px;
      opacity:.70;
      line-height:1.2;
    }}
    @media (max-width: 520px){{
      .stat-grid{{ grid-template-columns: 1fr; }}
      .stat-value{{ font-size:24px; }}
    }}
    </style>

    <div class="jp">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">최근 평균(최대 50회)</div>
          <div class="stat-value">{avg_rate:.0f}%</div>
          <div class="stat-sub">정답률 기준</div>
        </div>
    
        <div class="stat-card">
          <div class="stat-label">최고 점수</div>
          <div class="stat-value">{best} / {last_total}</div>
          <div class="stat-sub">최근 기록 중 최고</div>
        </div>
    
        <div class="stat-card">
          <div class="stat-label">최근 점수</div>
          <div class="stat-value">{last_score} / {last_total}</div>
          <div class="stat-sub">가장 최근 1회</div>
        </div>
      </div>
    </div>
    """
    components.html(dashboard_html, height=330)

    st.markdown("### ❌ 자주 틀린 단어 TOP10 (최근 50회)")

    counter = Counter()
    for row in (res.data or []):
        wl = row.get("wrong_list") or []
        if isinstance(wl, list):
            for w in wl:
                word = str(w.get("단어", "")).strip()
                if word:
                    counter[word] += 1

    if not counter:
        st.caption("아직 오답 데이터가 충분하지 않습니다. 몇 번 더 풀면 TOP10이 생겨요 🙂")
        return

    # --- TOP10 카드형 CSS (마이페이지에서만 쓰도록 이 블록 바로 위에 넣는 게 안전) ---
    st.markdown("""
    <style>
    .wt10-card{
      border:1px solid rgba(120,120,120,0.25);
      border-radius:18px;
      padding:14px 16px;
      margin:12px 0;
      background: rgba(255,255,255,0.02);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:14px;
    }
    .wt10-left{
      display:flex;
      flex-direction:column;
      gap:6px;
      min-width: 0;
    }
    .wt10-title{
      font-size:18px;
      font-weight:900;
      line-height:1.15;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .wt10-sub{
      font-size:13px;
      opacity:.75;
    }
    .wt10-badge{
      border:1px solid rgba(120,120,120,0.25);
      background: rgba(255,255,255,0.03);
      border-radius:999px;
      padding:7px 12px;
      font-size:13px;
      font-weight:900;
      white-space:nowrap;
    }
    </style>
    """, unsafe_allow_html=True)

    def render_wrong_top10_card(rank: int, word: str, cnt: int):
        st.markdown(f"""
    <div class="jp">
      <div class="wt10-card">
        <div class="wt10-left">
          <div class="wt10-title">#{rank} {word}</div>
          <div class="wt10-sub">최근 50회 기준</div>
        </div>
        <div class="wt10-badge">오답 {cnt}회</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    top10 = counter.most_common(10)
    for i, (w, cnt) in enumerate(top10, start=1):
        render_wrong_top10_card(i, str(w), int(cnt))

    if st.button("❌ 이 TOP10으로 시험 보기", type="primary", use_container_width=True, key="btn_quiz_from_top10"):
        clear_question_widget_keys()
        weak_wrong_list = [{"단어": w} for (w, _cnt) in top10]
        retry_quiz = build_quiz_from_wrongs(weak_wrong_list, st.session_state.quiz_type)

        k = mastery_key(qtype=st.session_state.quiz_type)
        st.session_state.setdefault("mastery_done", {})
        st.session_state.mastery_done[k] = False

        start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)
        st.session_state["_scroll_top_once"] = True
        st.session_state.page = "quiz"
        st.rerun()

def reset_quiz_state_only():
    clear_question_widget_keys()
    for k in ["quiz", "answers", "submitted", "wrong_list",
              "saved_this_attempt", "stats_saved_this_attempt",
              "session_stats_applied_this_attempt"]:
        st.session_state.pop(k, None)

def go_quiz_from_home():
    reset_quiz_state_only()
    st.session_state.page = "quiz"
    st.session_state["_scroll_top_once"] = True

def render_home():
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")
    # HUB 마이페이지에서는 제목을 "마이페이지"로 표시
    page_title = "👤 마이페이지" if st.session_state.get("page") == "my" else "✨하테나일본어 한자정복"


    quotes = [
        "배움은 매일 새로 시작해도 늦지 않다.",
        "오늘의 한 문제는 내일의 자신감이다.",
        "조금이라도 손을 움직인 날은 실패가 아니다.",
        "완벽보다 ‘계속’이 더 강하다.",
        "루틴은 작게, 지속은 길게.",
    ]
    q = random.choice(quotes)

    st.markdown(
        f"""
<div class="jp" style="
  margin-top:1px;
  border:1px solid rgba(120,120,120,0.18);
  border-radius:18px; padding:16px; background:rgba(255,255,255,0.03);">
  <div style="font-weight:900; font-size:14px; opacity:.75;">오늘의 말</div>
  <div style="margin-top:6px; font-weight:900; font-size:20px; line-height:1.3;">{q}</div>
  <div style="margin-top:10px; opacity:.80; font-size:13px; line-height:1.55;">
    일본어공부, 가볍게 시작해 볼까요?
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.divider()
    
    c1, c2, c3 = st.columns([5, 3, 3])
    with c1:
        st.button("▶ 오늘의 퀴즈 시작", type="primary", use_container_width=True,
                  key="btn_home_start", on_click=go_quiz_from_home)
    with c2:
        st.button("📌 마이페이지", use_container_width=True,
                  key="btn_home_my", on_click=nav_to, args=("my",))
    with c3:
        st.button("🚪 로그아웃", use_container_width=True,
                  key="btn_home_logout", on_click=nav_logout)

# ============================================================
# OK 앱 시작: refresh → 로그인 강제 → 페이지 설정
# ============================================================
# ============================================================
# ✅ 세션 복원 (Hub 이동/리렌더링에도 로그인 유지)
# - 여기서 '복원 실패'를 이유로 강제 로그아웃(clear_auth_everywhere)하지 않습니다.
#   (페이지 이동 시 일시적으로 token/user가 비어 보이는 순간이 있어도, core가 복원합니다.)
# ============================================================
try:
    core.ensure_core(cookie_prefix="hotena_beginner_", localstorage_keys=("hotena_rt","hotena_at"))
    core.refresh_session_from_cookie_if_needed(force=False)
except Exception:
    pass

require_login()

ALLOWED_PAGES = {"home", "quiz", "my", "admin"}
if "page" not in st.session_state:
    st.session_state.page = "home"
if st.session_state.get("page") not in ALLOWED_PAGES:
    st.session_state.page = "home"

# HUB에서 실행될 때는 기본적으로 퀴즈 화면으로 진입.
# 단, HUB 상단 메뉴에서 특정 화면(예: 마이페이지)을 요청한 경우는 그 화면으로 진입.
if st.session_state.get("HUB_MODE"):
    target = st.session_state.get("hub_target")
    if target in ("my", "admin", "home", "quiz"):
        st.session_state.page = target
    else:
        st.session_state.page = "quiz"

user = st.session_state.user
user_id = user.id
user_email = getattr(user, "email", None) or st.session_state.get("login_email")
sb_authed = core.get_authed_sb()

try:
    available_types = get_available_quiz_types() if sb_authed is not None else QUIZ_TYPES_USER
except Exception:
    available_types = QUIZ_TYPES_USER

# progress 자동복원 OFF (원본 유지)
st.session_state.progress_restored = True

if "level" not in st.session_state:
    st.session_state.level = "N5"

# title (home 제외: 페이지별로 제목 다르게)
if st.session_state.get("page") != "home":
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")

    _p = st.session_state.get("page")
    if _p == "my":
        _title = "👤 마이페이지"
    elif _p == "admin":
        _title = "🛠 관리자"
    else:
        _title = "✨ 한자 퀴즈"

    st.markdown(
        f"""
<div class="jp headbar">
  <div class="headtitle">{_title}</div>
</div>
""",
        unsafe_allow_html=True
    )

# 프로필/출석
if sb_authed is not None:
    ensure_profile(sb_authed, user)
    att = mark_attendance_once(sb_authed)
    if att:
        st.session_state["streak_count"] = int(att.get("streak_count", 0) or 0)
        st.session_state["did_attend_today"] = bool(att.get("did_attend", False))
else:
    st.caption("세션 토큰이 없습니다. (sb_authed=None) 다시 로그인해 주세요.")

# ============================================================
# OK 라우팅
# ============================================================
if st.session_state.page == "home":
    render_home()
    st.stop()

if st.session_state.page == "admin":
    if not is_admin():
        st.session_state.page = "quiz"
        st.warning("관리자 권한이 없습니다.")
        st.rerun()
    render_admin_dashboard()
    st.stop()

if st.session_state.page == "my":
    try:
        render_my_dashboard()
    except Exception:
        st.error("마이페이지에서 예외가 발생했습니다. 아래 Traceback을 확인해 주세요.")
        st.code(traceback.format_exc())
    st.stop()

# quiz page
render_topcard()
render_sound_toggle()  # 🔊 소리 ON/OFF 버튼(최초 1회 클릭 필요)


# ============================================================
# OK 상단: 오늘의 목표 + 출석 배지
# ============================================================
streak = st.session_state.get("streak_count")
did_today = st.session_state.get("did_attend_today")

if streak is not None:
    if did_today:
        st.success(f"오늘 출석 완료!  (연속 {streak}일)")
    else:
        st.caption(f"연속 출석 {streak}일")

    if streak >= 30:
        st.info("🔥 30일 연속 달성! 진짜 레전드…")
    elif streak >= 7:
        st.info("🏅 7일 연속 달성! 흐름이 잡혔어요.")


# OK (HOME HUB에서 '오늘의 목표'를 통합 관리합니다.)



# ============================================================
# OK 세션 초기화
# ============================================================

def render_kanji_hub(HUB_MODE: bool = False):
    if HUB_MODE: st.session_state['HUB_MODE']=True
    if "quiz_version" not in st.session_state:
        st.session_state.quiz_version = 0
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "wrong_list" not in st.session_state:
        st.session_state.wrong_list = []
    if "saved_this_attempt" not in st.session_state:
        st.session_state.saved_this_attempt = False
    if "stats_saved_this_attempt" not in st.session_state:
        st.session_state.stats_saved_this_attempt = False
    if "session_stats_applied_this_attempt" not in st.session_state:
        st.session_state.session_stats_applied_this_attempt = False
    if "history" not in st.session_state:
        st.session_state.history = []
    if "progress_dirty" not in st.session_state:
        st.session_state.progress_dirty = False
    if "wrong_counter" not in st.session_state:
        st.session_state.wrong_counter = {}
    if "total_counter" not in st.session_state:
        st.session_state.total_counter = {}

    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()

    # ============================================================
    # OK 상단 UI: 레벨 버튼(N5~N1) → 유형 버튼(카드형) → 캡션 → divider
    # ============================================================

    def on_pick_level(lv: str):
        lv = str(lv).strip().upper()
        if lv == st.session_state.level:
            return
        st.session_state.level = lv

        clear_question_widget_keys()
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)

        st.session_state["_scroll_top_once"] = True
    
    def on_pick_qtype(qt: str):
        qt = str(qt).strip()
        if qt == st.session_state.quiz_type:
            return
        st.session_state.quiz_type = qt

        clear_question_widget_keys()
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)

        st.session_state["_scroll_top_once"] = True
  
    st.markdown('<div class="qtypewrap">', unsafe_allow_html=True)

    # ----------------------------
    # 1) 레벨 버튼(N5~N1) 먼저
    # ----------------------------
    
    st.markdown('<div class="qtype_hint jp">✨레벨을 선택하세요</div>', unsafe_allow_html=True)
    
    level_cols = st.columns(len(LEVEL_OPTIONS), gap="small")
    for i, lv in enumerate(LEVEL_OPTIONS):
        is_selected_lv = (lv == st.session_state.level)
        btn_lv_type = "primary" if is_selected_lv else "secondary"
        icon_lv = "" if is_selected_lv else ""
        label_lv = LEVEL_LABEL_MAP.get(lv, lv)

        with level_cols[i]:
            st.button(
                f"{icon_lv}{label_lv}",
                use_container_width=True,
                type=btn_lv_type,
                key=f"btn_level_{lv}",
                on_click=on_pick_level,
                args=(lv,),
            )

    # ----------------------------
    # 2) 유형 버튼(발음/뜻/한→일)
    # ----------------------------
    
    st.markdown('<div class="qtype_hint jp">✨유형을 선택하세요</div>', unsafe_allow_html=True)
    
    type_cols = st.columns(len(available_types), gap="small")
    for i, qt in enumerate(available_types):
        is_selected = (qt == st.session_state.quiz_type)
        btn_type = "primary" if is_selected else "secondary"
        icon = "" if is_selected else ""
        label = quiz_label_map.get(qt, qt)

        with type_cols[i]:
            st.button(
                f"{icon}{label}",
                use_container_width=True,
                type=btn_type,
                key=f"btn_qtype_{qt}",
                on_click=on_pick_qtype,
                args=(qt,),
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # OK divider 간격은 tight-divider 래퍼로
    st.markdown('<div class="tight-divider">', unsafe_allow_html=True)
    st.divider()
    st.markdown('</div>', unsafe_allow_html=True)

    # ============================================================
    # OK 버튼: 새 문제 / 맞힌 단어 제외 초기화
    # ============================================================
    cbtn1, cbtn2 = st.columns(2)

    with cbtn1:
        if st.button("🔄 새 문제(랜덤 10문항)", use_container_width=True, key="btn_new_random_10"):
            k_now = mastery_key()
            if st.session_state.get("mastery_done", {}).get(k_now, False):
                st.session_state["_scroll_top_once"] = True
                st.rerun()

            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    with cbtn2:
        if st.button("맞힌 단어 제외 초기화", use_container_width=True, key="btn_reset_mastered_current_type"):
            ensure_mastered_words_shape()
            k_now = mastery_key()
            st.session_state.mastered_words[k_now] = set()
            st.session_state.mastery_banner_shown[k_now] = False
            st.session_state.mastery_done[k_now] = False

            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)

            st.success(f"초기화 완료 (유형: {quiz_label_map[st.session_state.quiz_type]})")
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    # 정복 안내
    k_now = mastery_key()
    if st.session_state.get("mastery_done", {}).get(k_now, False):
        st.success("🏆 이 유형을 완전히 정복했어요!")
        st.caption("👉 다른 유형을 선택하거나, '맞힌 단어 제외 초기화'로 다시 시작할 수 있어요.")

    # ============================================================
    # OK (중요) UI는 먼저 보여주고, 퀴즈가 없으면 여기서만 멈춘다
    # ============================================================
    if "quiz" not in st.session_state or not isinstance(st.session_state.quiz, list):
        st.session_state.quiz = []

    # 아직 퀴즈가 없다면 1회만 생성 시도 (UI는 이미 위에서 다 보여준 상태)
    k_now = mastery_key()
    is_mastered_done = bool(st.session_state.get("mastery_done", {}).get(k_now, False))

    if (not is_mastered_done) and len(st.session_state.quiz) == 0:
        clear_question_widget_keys()
        st.session_state.quiz = build_quiz(st.session_state.quiz_type, st.session_state.level) or []
        st.session_state.submitted = False

    # 그래도 0개면: 버튼은 이미 보이는 상태 → 안내만 하고 멈춤
    if len(st.session_state.quiz) == 0:
        st.info("이 레벨에 출제할 단어가 없어요. 다른 레벨을 선택하거나, CSV의 level 값을 확인해 주세요.")
        st.stop()

    # ============================================================
    # OK answers 길이 자동 맞춤
    # ============================================================
    if "quiz" not in st.session_state or not isinstance(st.session_state.quiz, list):
        st.session_state.quiz = []

    if len(st.session_state.quiz) == 0:
        st.session_state.quiz = build_quiz(st.session_state.quiz_type, st.session_state.level) or []

    # ============================================================
    # ✅ 페이지 진입 시: 보기 선택(위젯 q_...) 잔상 제거
    # - Hub(home.py)에서 p=kanji로 이동할 때마다 "처음 진입"으로 판단
    # - 보기 선택이 미리 체크되어 보이는 현상 방지
    # ============================================================
    def _maybe_reset_on_enter_kanji():
        try:
            cur_p = str(dict(st.query_params).get("p", ""))
        except Exception:
            cur_p = ""
        last_p = str(st.session_state.get("_nav_last_p", ""))
        if cur_p == "kanji" and last_p != "kanji":
            # 위젯 선택값 제거
            clear_question_widget_keys()
            # 채점/오답/선택 초기화
            st.session_state["is_graded"] = False
            st.session_state["wrong_list"] = []
            st.session_state["answers"] = [None] * len(st.session_state.get("quiz") or [])
        st.session_state["_nav_last_p"] = cur_p

    _maybe_reset_on_enter_kanji()



    quiz_len = len(st.session_state.quiz)
    if "answers" not in st.session_state or not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != quiz_len:
        st.session_state.answers = [None] * quiz_len

    # 정복 상태면 문제 영역 차단
    k_now = mastery_key()
    if bool(st.session_state.get("mastery_done", {}).get(k_now, False)):
        st.stop()

    # ============================================================
    # OK 문제 표시 (동그란 배지: ① ② ③ ... + 같은 줄)
    # ============================================================
    circled_nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"

    # ============================================================
    # OK 문제 표시 + 보기 선택 (form: 선택 중 rerun 최소화)
    # ============================================================
    quiz_len = len(st.session_state.quiz)
    with st.form('kanji_quiz_form', clear_on_submit=False):
        for idx, q in enumerate(st.session_state.quiz):
            badge = circled_nums[idx] if idx < len(circled_nums) else f"({idx+1})"
            st.markdown(
                f"""
    <div class="jp" style="display:flex; align-items:baseline; gap:5px; margin: 10px 0 8px 0;">
      <div style="
        flex:0 0 auto;
        font-size:20px;
        line-height:1;
        font-weight:900;
        transform: translateY(1px);
      ">{badge}</div>
      <div style="
        flex:1 1 auto;
        font-size:18px;
        font-weight:500;
        line-height:1.35;
      ">{q['prompt']}</div>
    </div>
    """,
                unsafe_allow_html=True,
            )
            widget_key = f"q_{st.session_state.quiz_version}_{idx}"
            prev = st.session_state.answers[idx]
            default_index = None
            if prev is not None and prev in q['choices']:
                default_index = q['choices'].index(prev)
            # ✅ form 내부에서는 on_change 콜백을 사용할 수 없음(Streamlit 제약)
            st.radio(
                label='보기',
                options=q['choices'],
                index=default_index,
                key=widget_key,
                label_visibility='collapsed',
            )
        submitted_btn = st.form_submit_button('제출하고 채점하기', type='primary', use_container_width=True)

    # form 제출 시에만 위젯 값을 answers로 동기화
    if submitted_btn:
        sync_answers_from_widgets()
        all_answered = (quiz_len > 0) and all(a is not None for a in st.session_state.answers)
        if not all_answered:
            st.warning('모든 문제에 답을 선택한 뒤 제출해 주세요.')
            st.stop()
        st.session_state.submitted = True
        st.session_state.session_stats_applied_this_attempt = False

    # 제출 전 안내(선택만으로는 rerun이 거의 없음)
    if (not st.session_state.submitted) and (quiz_len > 0) and any(a is None for a in st.session_state.answers):
        st.info('모든 문제에 답을 선택한 뒤 제출해 주세요.')
    # ============================================================
    # OK 제출 후 화면
    # ============================================================
    if st.session_state.submitted:
        show_post_ui = (SHOW_POST_SUBMIT_UI == "Y") or is_admin()

        ensure_mastered_words_shape()
        ensure_excluded_wrong_words_shape()

        current_type = st.session_state.quiz_type
        k_now = mastery_key()

        score = 0
        wrong_list = []

        for idx, q in enumerate(st.session_state.quiz):
            picked = st.session_state.answers[idx]
            correct = q["correct_text"]
            word_key = str(q.get("jp_word", "")).strip()

            if picked == correct:
                score += 1
                if word_key:
                    st.session_state.mastered_words.setdefault(k_now, set()).add(word_key)
            else:
                # OK 오답노트 채우기
                wrong_list.append({
                    "No": idx + 1,
                    "문제": str(q.get("prompt", "")),
                    "내 답": "" if picked is None else str(picked),
                    "정답": str(correct),
                    "단어": str(q.get("jp_word", "")).strip(),
                    "읽기": str(q.get("reading", "")).strip(),
                    "뜻": str(q.get("meaning", "")).strip(),
                    "유형": current_type,
                })

        st.session_state.wrong_list = wrong_list

        quiz_len = len(st.session_state.quiz)
        st.success(f"점수: {score} / {quiz_len}")
        ratio = score / quiz_len if quiz_len else 0

        
        # OK 점수 기반 SFX (제출 직후 1회) — core.py에서 중앙 통제
        _sfx_key = f"word_submit__{int(st.session_state.get('quiz_version', 0) or 0)}"
        if ratio == 1:
            core.play_sfx_once(_sfx_key, "reward")
        elif ratio >= 0.7:
            core.play_sfx_once(_sfx_key, "correct")
        else:
            core.play_sfx_once(_sfx_key, "wrong")
    
        if ratio == 1:
            st.balloons()
            st.success("🎉 완벽해요! 전부 정답입니다. 정말 잘했어요!")
            st.caption("※ 정복 판정은 ‘더 이상 출제할 단어가 없을 때’ 자동으로 표시됩니다.")
        elif ratio >= 0.7:
            st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
        else:
            st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")

        # OK DB 저장
        sb_authed_local = core.get_authed_sb()
        if sb_authed_local is None:
            if show_post_ui:
                st.warning("DB 저장/조회용 토큰이 없습니다. 다시 로그인해 주세요.")
        else:
            if not st.session_state.saved_this_attempt:
                def _save():
                    return save_attempt_to_db(
                        sb_authed=sb_authed_local,
                        user_id=user_id,
                        user_email=user_email,
                        level=st.session_state.level,
                        quiz_type=current_type,
                        quiz_len=quiz_len,
                        score=score,
                        wrong_list=wrong_list,
                    )
                try:
                    run_db(_save)
                    st.session_state.saved_this_attempt = True
                except Exception as e:
                    if show_post_ui:
                        st.warning("DB 저장에 실패했습니다. (테이블/컬럼/권한/RLS 정책 확인 필요)")
                        st.write(str(e))

            if not st.session_state.stats_saved_this_attempt:
                def _save_stats_bulk():
                    sync_answers_from_widgets()
                    items = build_word_results_bulk_payload(
                        quiz=st.session_state.quiz,
                        answers=st.session_state.answers,
                        quiz_type=current_type,
                        level=st.session_state.level,
                    )
                    if not items:
                        return None
                    return sb_authed_local.rpc("record_word_results_bulk", {"p_items": items}).execute()

                try:
                    run_db(_save_stats_bulk)
                    st.session_state.stats_saved_this_attempt = True
                    if show_post_ui:
                        st.success("단어 통계(bulk) 저장 성공")
                except Exception as e:
                    if show_post_ui:
                        st.error("❌ 단어 통계(bulk) 저장 실패")
                        st.exception(e)

            if show_post_ui:
                st.subheader("📌 내 최근 기록")
                def _fetch_hist():
                    return fetch_recent_attempts(sb_authed_local, user_id, limit=10)

                try:
                    res = run_db(_fetch_hist)
                    if not res.data:
                        st.info("아직 저장된 기록이 없습니다. 문제를 풀고 제출하면 기록이 쌓여요.")
                    else:
                        hist = pd.DataFrame(res.data).copy()
                        hist["created_at"] = to_kst_naive(hist["created_at"])
                        hist["유형"] = hist["pos_mode"].map(lambda x: quiz_label_for_table.get(x, x))
                        hist["정답률"] = (hist["score"] / hist["quiz_len"]).fillna(0.0)

                        avg_rate = float(hist["정답률"].mean() * 100)
                        best = int(hist["score"].max())
                        last_score = int(hist.iloc[0]["score"])
                        last_total = int(hist.iloc[0]["quiz_len"])

                        # OK 마이페이지 상단 3카드 (components.html로 강제 렌더링)
                        dashboard_html = f"""
                        <style>
                        .stat-grid{{
                          display:grid;
                          grid-template-columns: repeat(3, 1fr);
                          gap:12px;
                          margin: 6px 0 6px 0;
                        }}
                        .stat-card{{
                          border:1px solid rgba(120,120,120,0.25);
                          border-radius:18px;
                          padding:14px 14px;
                          background: rgba(255,255,255,0.02);
                        }}
                        .stat-label{{
                          font-size:12px;
                          font-weight:800;
                          opacity:.72;
                          line-height:1.2;
                        }}
                        .stat-value{{
                          margin-top:6px;
                          font-size:22px;
                          font-weight:900;
                          line-height:1.1;
                        }}
                        .stat-sub{{
                          margin-top:6px;
                          font-size:12px;
                          opacity:.70;
                          line-height:1.2;
                        }}
                        @media (max-width: 520px){{
                          .stat-grid{{ grid-template-columns: 1fr; }}
                          .stat-value{{ font-size:24px; }}
                        }}
                        </style>

                        <div class="jp">
                          <div class="stat-grid">
                            <div class="stat-card">
                              <div class="stat-label">최근 평균(최대 50회)</div>
                              <div class="stat-value">{avg_rate:.0f}%</div>
                              <div class="stat-sub">정답률 기준</div>
                            </div>

                            <div class="stat-card">
                              <div class="stat-label">최고 점수</div>
                              <div class="stat-value">{best} / {last_total}</div>
                              <div class="stat-sub">최근 기록 중 최고</div>
                            </div>

                            <div class="stat-card">
                              <div class="stat-label">최근 점수</div>
                              <div class="stat-value">{last_score} / {last_total}</div>
                              <div class="stat-sub">가장 최근 1회</div>
                            </div>
                          </div>
                        </div>
                        """
    
                        components.html(dashboard_html, height=330)

                except Exception as e:
                    st.info("기록을 불러오지 못했습니다.")
                    st.write(str(e))

        # OK 세션 통계(로컬 카운터) 적용은 '1번만'
        if not st.session_state.session_stats_applied_this_attempt:
            st.session_state.history.append({"type": current_type, "score": score, "total": quiz_len})

            for idx, q in enumerate(st.session_state.quiz):
                word_key = str(q.get("jp_word", "")).strip()
                if word_key:
                    st.session_state.total_counter[word_key] = st.session_state.total_counter.get(word_key, 0) + 1
                    if st.session_state.answers[idx] != q["correct_text"]:
                        st.session_state.wrong_counter[word_key] = st.session_state.wrong_counter.get(word_key, 0) + 1

            st.session_state.session_stats_applied_this_attempt = True

    # ============================================================
    # OK 오답노트 + 다시풀기
    # ============================================================
    if st.session_state.submitted and st.session_state.wrong_list:
        st.subheader("❌ 오답 노트")

        st.markdown(
            """
    <style>
    .wrong-card{
      border: 1px solid rgba(120,120,120,0.25);
      border-radius: 16px;
      padding: 14px 14px;
      margin-bottom: 10px;
      background: rgba(255,255,255,0.02);
    }
    .wrong-top{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:12px;
      margin-bottom: 8px;
    }
    .wrong-title{ font-weight: 900; font-size: 15px; margin-bottom: 4px; }
    .wrong-sub{ opacity: 0.8; font-size: 12px; }
    .tag{
      display:inline-flex;
      align-items:center;
      gap:6px;
      padding: 5px 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid rgba(120,120,120,0.25);
      background: rgba(255,255,255,0.03);
      white-space: nowrap;
    }
    .ans-row{
      display:grid;
      grid-template-columns: 72px 1fr;
      gap:10px;
      margin-top:6px;
      font-size: 13px;
    }
    .ans-k{ opacity: 0.7; font-weight: 700; }
    </style>
    """,
            unsafe_allow_html=True,
        )

        def _s(v):
            return "" if v is None else str(v)

        for w in st.session_state.wrong_list:
            no = _s(w.get("No"))
            qtext = _s(w.get("문제"))
            picked = _s(w.get("내 답"))
            correct = _s(w.get("정답"))
            word = _s(w.get("단어"))
            reading = _s(w.get("읽기"))
            meaning = _s(w.get("뜻"))
            mode = quiz_label_map.get(w.get("유형"), w.get("유형", ""))

            st.markdown(
                f"""
            <div class="jp">
              <div class="wrong-card">
                <div class="wrong-top">
                  <div>
                  <div class="wrong-title">Q{no}. {word}</div>
                  <div class="wrong-sub">{qtext} · 유형: {mode}</div>
                </div>
                <div class="tag">오답</div>
              </div>

              <div class="ans-row"><div class="ans-k">내 답</div><div>{picked}</div></div>
              <div class="ans-row"><div class="ans-k">정답</div><div><b>{correct}</b></div></div>
              <div class="ans-row"><div class="ans-k">발음</div><div>{reading}</div></div>
              <div class="ans-row"><div class="ans-k">뜻</div><div>{meaning}</div></div>
            </div>
            """,
               unsafe_allow_html=True,
            )

        if st.button("❌ 틀린 문제만 다시 풀기", type="primary", use_container_width=True, key="btn_retry_wrongs_bottom"):
            clear_question_widget_keys()
            retry_quiz = build_quiz_from_wrongs(st.session_state.wrong_list, st.session_state.quiz_type)
            start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    # 다음 10문항
    if st.session_state.submitted:
        if st.button("다음 10문항 시작하기", type="primary", use_container_width=True, key="btn_next_10"):
            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

        show_naver_talk = (SHOW_NAVER_TALK == "N") or is_admin()
        if show_naver_talk:
            render_naver_talk()


if __name__ == '__main__':
    render_kanji_hub(HUB_MODE=False)


def render():
    """Home hub에서 import 후 호출되는 진입점."""
    render_kanji_hub(HUB_MODE=True)
