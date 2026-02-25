# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations
# BUILD_STAMP_TALK: talk-newset-in-progress-v1 2026-02-22 KST (+09:00)

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib

import pandas as pd
import streamlit as st

import ai_tutor


# ============================================================
# ✅ wrong_notes debug helper
# ============================================================
_WN_DEBUG = bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))
def _wn_warn(msg: str):
    if _WN_DEBUG:
        try:
            st.warning(msg)
        except Exception:
            # fallback: Streamlit 기본 녹음(브라우저/환경에 따라 components 녹음이 막힐 때)
            try:
                st.audio_input("(선택) 내 말 녹음")
            except Exception:
                pass
# ============================================================
# ✅ HUB 진입 시: 선택/제출 상태 초기화 (회화)
# ============================================================
if st.session_state.get("_entered_talk"):
    for k in list(st.session_state.keys()):
        if k.startswith("talk_") or k in ("submitted", "is_graded", "answers"):
            st.session_state.pop(k, None)
    st.session_state["_entered_talk"] = False


import streamlit.components.v1 as components
from supabase import create_client

# ✅ MP3 base (스토리지)
BASE_AUDIO_URL = 'https://hotena.com/hotena/app/mp3/'

def resolve_audio_url(v: str) -> str:
    """CSV에 '00.mp3' 처럼 파일명만 적어도 재생되도록 URL을 보정한다.
    - v가 http(s)로 시작하면 그대로 사용
    - BASE_AUDIO_URL이 있으면 BASE_AUDIO_URL + v 로 결합
    - BASE_AUDIO_URL이 없으면 상대경로(v)를 그대로 사용(예: 'mp3/00.mp3')
    """
    v = (v or "").strip()
    if not v:
        return ""
    if v.startswith("http://") or v.startswith("https://"):
        return v
    if BASE_AUDIO_URL:
        return BASE_AUDIO_URL.rstrip("/") + "/" + v.lstrip("/")
    return v

# ✅ MP3 URL이 없을 때 브라우저 TTS로 대체할지 여부
USE_TTS_FALLBACK = True  # mp3만 쓰려면 False


# ============================================================
# ✅ Settings
# ============================================================
NS = "talk"
SET_LEN = 10
FREE_SET_LEN = 3  # FREE는 3문제만 제공
FREE_TTS_QUOTA = 3  # FREE 발음 듣기 3회(일)
FREE_RECORD_QUOTA = 3  # FREE 녹음 3회(일)

# ============================================================
# ✅ Hub login required
# ============================================================
u = st.session_state.get("user")
if not u:
    st.warning("홈에서 로그인 후 이용해 주세요.")
    st.stop()

USER_ID = getattr(u, "id", None)
USER_EMAIL = getattr(u, "email", "") or ""

USER_PLAN = (st.session_state.get("user_plan") or "free").lower()
IS_PRO = USER_PLAN == "pro"

def _inject_talk_ui_css():
    if st.session_state.get("_talk_ui_css_done", False):
        return
    st.session_state["_talk_ui_css_done"] = True
    st.markdown(
        """
<style>
.talk-bubble-row{display:flex;gap:10px;align-items:flex-end;margin:6px 0;}
.talk-bubble-label{min-width:68px;font-weight:800;opacity:.85;}
.talk-bubble{
  display:inline-block;
  max-width:100%;
  padding:10px 12px;
  border-radius:16px;
  border:1px solid rgba(49,51,63,.14);
  box-shadow:0 1px 0 rgba(0,0,0,.02);
  line-height:1.25;
  word-break:break-word;
}
.talk-bubble.partner{background:rgba(0,0,0,.02);}
.talk-bubble.me{background:rgba(33,150,243,.08);}
.talk-bubble-sub{font-size:.86rem;opacity:.70;margin-top:2px;}
.talk-tts-col{display:flex;justify-content:flex-end;align-items:center;}
</style>
""",
        unsafe_allow_html=True,
    )

_inject_talk_ui_css()

# ✅ TTS 플레이어(1개) 렌더 — 요청이 있을 때만 재생
# (moved) _render_talk_tts_player() call is placed near the end to avoid NameError on import.

st.markdown(
    """
<style>
/* 헤더 자리 고정: rerun 시에도 레이아웃 흔들림 최소화 */
.talk-fixed-header{
  padding: 6px 0 10px 0;
  min-height: 64px;     /* ✅ PC에서 타이틀+캡션 높이 자리 확보 */
}
.talk-fixed-title{
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.15;
  margin: 0;
}
.talk-fixed-caption{
  margin-top: 6px;
  font-size: 0.95rem;
  opacity: 0.75;
}
@media (max-width: 768px){
  .talk-fixed-header{ min-height: 52px; } /* 모바일은 조금 줄임 */
  .talk-fixed-title{ font-size: 1.6rem; }
}
</style>

<div class="talk-fixed-header">
  <div class="talk-fixed-title">일본어회화</div>
  <div class="talk-fixed-caption">
    1문제씩: 상황 → 상대 발화(🔊/PRO) → 보기 선택 → 제출 → 정답/설명 → (선택)말하기 완료 체크
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ✅ Supabase client (hub reuse)
# ============================================================

def get_cfg(key: str) -> str:
    cfg = st.session_state.get("cfg") or {}
    v = cfg.get(key)
    if v:
        return v
    try:
        return st.secrets[key]
    except Exception:
        return ""


@st.cache_resource(show_spinner=False)
def _make_sb(url: str, key: str):
    return create_client(url, key)

def get_sb():
    """Supabase client (lazy init + cached)."""
    sb = st.session_state.get("sb")
    if sb is not None:
        return sb
    url = get_cfg("SUPABASE_URL")
    key = get_cfg("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Supabase 설정이 없습니다. (SUPABASE_URL / SUPABASE_ANON_KEY)")
        st.stop()
    sb = _make_sb(url, key)
    st.session_state["sb"] = sb
    return sb


def get_authed_sb():
    # 홈허브 로그인 세션의 access_token을 사용해 PostgREST 권한 요청을 보냅니다.
    token = st.session_state.get("access_token")
    if not token:
        return None

    cached = st.session_state.get("_sb_authed_talk")
    cached_token = st.session_state.get("_sb_authed_talk_token")
    if cached is not None and cached_token == token:
        return cached

    sb2 = get_sb()
    try:
        # supabase-py: postgrest.auth(token)
        sb2.postgrest.auth(token)
    except Exception:
        # 일부 버전은 내부 client 설정이 다를 수 있음
        pass

    st.session_state["_sb_authed_talk"] = sb2
    st.session_state["_sb_authed_talk_token"] = token
    return sb2


sb = get_sb()

# ============================================================
# ✅ CSV load
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "talk_situations.csv"

if not CSV_PATH.exists():
    st.error(f"CSV 파일이 없습니다: {CSV_PATH}")
    st.stop()


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = ["qid", "level", "tag", "situation_kr", "partner_jp", "answer_jp"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")

    # 문자열 정리
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"nan": "", "NaN": "", "None": ""})

    # level/tag 소문자
    df["level"] = df["level"].astype(str).str.lower().str.strip()
    df["tag"] = df["tag"].astype(str).str.lower().str.strip()

    return df.fillna("")


DF = load_csv(CSV_PATH)

# ============================================================
# ✅ Labels
# ============================================================
TAG_LABELS = {
    "business": "비즈니스",
    "daily": "일상",
    "call": "전화/온라인",
    "interview": "면접",
    "travel": "여행",
    "shopping": "쇼핑",
    "food": "음식/카페",
    "emergency": "긴급/트러블",
}
LEVEL_LABELS = {"n5": "N5", "n4": "N4", "n3": "N3"}

# ============================================================
# ✅ Progress I/O (profiles.progress)
# ============================================================

def load_progress() -> dict:
    if isinstance(st.session_state.get("progress_all"), dict):
        return st.session_state["progress_all"]
    try:
        resp = sb.table("profiles").select("progress").eq("id", USER_ID).single().execute()
        prog = (getattr(resp, "data", None) or {}).get("progress") or {}
        if not isinstance(prog, dict):
            prog = {}
        st.session_state["progress_all"] = prog
        return prog
    except Exception:
        prog = {}
        st.session_state["progress_all"] = prog
        return prog


def save_progress(progress_all: dict):
    st.session_state["progress_all"] = progress_all
    try:
        sb.table("profiles").update({"progress": progress_all}).eq("id", USER_ID).execute()
    except Exception:
        pass
# ============================================================
# ✅ Recent 2 turns (stable, 안전 2턴 유지)
# - session_state + profiles.progress['talk']['recent_turns']에 함께 저장
# - 항상 길이 2 유지(부족하면 빈 턴으로 패딩)
# ============================================================
def _ensure_recent_turns():
    lst = st.session_state.get("talk_recent_turns")
    if not isinstance(lst, list) or not lst:
        # seed from DB-backed progress (best effort)
        try:
            prog = load_progress()
            talk_prog = prog.get("talk") or {}
            seeded = talk_prog.get("recent_turns") or []
            if isinstance(seeded, list):
                lst = seeded
        except Exception:
            lst = []

    if not isinstance(lst, list):
        lst = []
    lst = [x for x in lst if isinstance(x, dict)]

    pad = {"qid": "", "situation_kr": "", "partner_jp": "", "selected": "", "correct": "", "ok": None}
    while len(lst) < 2:
        lst.insert(0, dict(pad))
    lst = lst[-2:]

    st.session_state["talk_recent_turns"] = lst

    # persist (best effort) — 매 rerun마다 DB 업데이트하지 않도록 변경
    try:
        h = hashlib.md5(str(lst).encode("utf-8")).hexdigest()
        if st.session_state.get("_talk_recent_turns_hash") != h:
            prog = load_progress()
            talk_prog = prog.get("talk") or {}
            talk_prog["recent_turns"] = lst
            prog["talk"] = talk_prog
            save_progress(prog)
            st.session_state["_talk_recent_turns_hash"] = h
    except Exception:
        pass

def _push_recent_turn(turn: dict):
    _ensure_recent_turns()
    lst = st.session_state.get("talk_recent_turns") or []
    if not isinstance(lst, list):
        lst = []
    if isinstance(turn, dict):
        lst.append(turn)
    lst = [x for x in lst if isinstance(x, dict)][-2:]

    pad = {"qid": "", "situation_kr": "", "partner_jp": "", "selected": "", "correct": "", "ok": None}
    while len(lst) < 2:
        lst.insert(0, dict(pad))

    st.session_state["talk_recent_turns"] = lst

    # persist (best effort) — 매 rerun마다 DB 업데이트하지 않도록 변경
    try:
        h = hashlib.md5(str(lst).encode("utf-8")).hexdigest()
        if st.session_state.get("_talk_recent_turns_hash") != h:
            prog = load_progress()
            talk_prog = prog.get("talk") or {}
            talk_prog["recent_turns"] = lst
            prog["talk"] = talk_prog
            save_progress(prog)
            st.session_state["_talk_recent_turns_hash"] = h
    except Exception:
        pass

def _recent_turns_summary() -> str:
    _ensure_recent_turns()
    lst = st.session_state.get("talk_recent_turns") or []
    lines = []
    for i, t in enumerate(lst, start=1):
        s = str((t or {}).get("situation_kr") or "").strip()
        p = str((t or {}).get("partner_jp") or "").strip()
        me = str((t or {}).get("selected") or "").strip()
        ok = (t or {}).get("ok")
        ok_mark = "O" if ok is True else ("X" if ok is False else "-")
        if not (s or p or me):
            continue
        lines.append(f"[최근{i}]({ok_mark}) 상황:{s[:40]} / 상대:{p[:40]} / 내:{me[:40]}")
    return "\n".join(lines).strip()

# init buffer early
try:
    _ensure_recent_turns()
except Exception:
    pass




# ============================================================
# ✅ FREE quota (daily): TTS 3회 / 녹음 3회
# - profiles.progress['talk']['free_quota'] 에 저장해서 새로고침/재로그인에도 유지
# ============================================================
from datetime import date as _date

def _today_key() -> str:
    try:
        return _date.today().isoformat()
    except Exception:
        return "1970-01-01"


def _get_free_quota() -> dict:
    """returns dict: {'date': 'YYYY-MM-DD', 'tts_used': int, 'record_used': int}"""
    prog = load_progress()
    talk_prog = prog.get("talk") or {}
    fq = talk_prog.get("free_quota") or {}
    if not isinstance(fq, dict):
        fq = {}
    d = fq.get("date") or ""
    if d != _today_key():
        fq = {"date": _today_key(), "tts_used": 0, "record_used": 0}
        talk_prog["free_quota"] = fq
        prog["talk"] = talk_prog
        save_progress(prog)
    fq["date"] = fq.get("date") or _today_key()
    fq["tts_used"] = int(fq.get("tts_used") or 0)
    fq["record_used"] = int(fq.get("record_used") or 0)
    return fq


def _set_free_quota(fq: dict):
    prog = load_progress()
    talk_prog = prog.get("talk") or {}
    talk_prog["free_quota"] = fq
    prog["talk"] = talk_prog
    save_progress(prog)


def _free_tts_remaining() -> int:
    if IS_PRO:
        return 9999
    fq = _get_free_quota()
    return max(0, int(FREE_TTS_QUOTA) - int(fq.get("tts_used") or 0))


def _free_record_remaining() -> int:
    if IS_PRO:
        return 9999
    fq = _get_free_quota()
    return max(0, int(FREE_RECORD_QUOTA) - int(fq.get("record_used") or 0))


def _use_free_tts_once():
    if IS_PRO:
        return
    fq = _get_free_quota()
    fq["tts_used"] = int(fq.get("tts_used") or 0) + 1
    _set_free_quota(fq)


def _use_free_record_once():
    if IS_PRO:
        return
    fq = _get_free_quota()
    fq["record_used"] = int(fq.get("record_used") or 0) + 1
    _set_free_quota(fq)


def log_attempt(level: str, score: int, quiz_len: int, wrong_count: int, wrong_list: list[dict], tag: str):
    try:
        sb.table("quiz_attempts").insert(
            {
                "user_id": USER_ID,
                "user_email": USER_EMAIL,
                "level": "talk",  # 홈 마이페이지에서 훈련 구분
                "pos_mode": f"talk:{tag}:{level}",
                "quiz_len": int(quiz_len),
                "score": int(score),
                "wrong_count": int(wrong_count),
                "wrong_list": wrong_list,
            }
        ).execute()
    except Exception:
        pass


def award_xp(amount: int, reason: str):
    fn = st.session_state.get("hub_award_xp")
    if callable(fn):
        fn(int(amount), reason)


# ============================================================
# ✅ New set / reset on hub navigation
# ============================================================

def reset_set():
    for k in list(st.session_state.keys()):
        if k.startswith(f"{NS}_"):
            # 홈에서 공유하는 건 제외
            if k.startswith("talk_"):
                st.session_state.pop(k, None)
    # 안전하게 핵심만 제거
    for k in [
        f"{NS}_set_qids",
        f"{NS}_idx",
        f"{NS}_answers",
        f"{NS}_submitted",
        f"{NS}_selected",
        f"{NS}_opts",
        f"{NS}_spoken",
    ]:
        st.session_state.pop(k, None)


try:
    nav = st.session_state.get("_hub_nav_token")
    last = st.session_state.get(f"_{NS}_last_nav_token")
    if nav and nav != last:
        st.session_state[f"_{NS}_last_nav_token"] = nav
        reset_set()
except Exception:
    pass

# ============================================================
# ✅ Filters (상황(tag))  ※ 현재는 '인사말(aisatsu)'만 노출
# ============================================================

# --- normalize (비교 실패/공백 문제 방지) ---
for _c in ["mode", "tag", "level"]:
    if _c in DF.columns:
        DF[_c] = DF[_c].astype(str).fillna("").str.strip()

if "mode" in DF.columns:
    DF["mode"] = DF["mode"].str.lower()
if "tag" in DF.columns:
    DF["tag"] = DF["tag"].str.lower().str.replace(r"[\s\-]+", "_", regex=True)
if "sub" in DF.columns:
    DF["sub"] = (
        DF["sub"].astype(str)
        .str.replace("\u3000", " ", regex=False)
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
    )
if "level" in DF.columns:
    DF["level"] = DF["level"].str.lower().str.replace(" ", "")

# --- 실전회화만 사용 ---
DF_BASE = DF.copy()

# --- 현재는 인사말만(aisatsu) ---
TAG_LABEL = {"aisatsu": "인사말"}
def _tag_label(t: str) -> str:
    return TAG_LABEL.get(str(t), str(t))

# 인사말은 tag=aisatsu 고정
tag_options = ["aisatsu"]

if not tag_options:
    st.warning("해당 상황의 회화 문제가 없습니다. (CSV의 tag 확인)")
    st.stop()

tag = st.selectbox(
    "상황 선택",
    options=tag_options,
    format_func=_tag_label,
    key=f"{NS}_tag",
)

# ✅ 인사말 유형(sub) 선택 (CSV에 sub 컬럼이 있으면 노출)
SUB_LABEL = {
    "__all__": "전체",
    "home": "집/가정",
    "morning": "아침",
    "day": "낮/친구",
    "evening": "저녁/밤",
    "thanks": "감사",
    "apology": "사과",
    "work": "회사 기본",
    "meeting": "미팅/첫인사",
    "phone": "전화",
    "basic": "기본/기타",
}

def _sub_label(s: str) -> str:
    return SUB_LABEL.get(str(s), str(s))

sub = "__all__"
has_sub = ("sub" in DF_BASE.columns) and DF_BASE["sub"].astype(str).str.strip().ne("").any()
if has_sub:
    subs_in_data = sorted(set([x for x in DF_BASE["sub"].astype(str).tolist() if str(x).strip()]))
    sub_options = ["__all__"] + subs_in_data
    sub = st.selectbox(
        "인사말 유형",
        options=sub_options,
        format_func=_sub_label,
        key=f"{NS}_sub",
    )

# 레벨 선택은 사용하지 않음(인사말에서 N4~N3 혼합)
level = "mix"

pool_df = DF_BASE[(DF_BASE["tag"] == tag)].copy().reset_index(drop=True)
if has_sub and sub != "__all__":
    pool_df = pool_df[pool_df["sub"].astype(str) == str(sub)].copy().reset_index(drop=True)


if pool_df.empty:
    st.warning("해당 상황의 회화 문제가 없습니다. (CSV의 tag 확인)")
    st.stop()

# ============================================================
# ✅ TTS (PRO only) - 브라우저 SpeechSynthesis
# ============================================================


# ============================================================
# ✅ TTS (Unified player: single iframe, no per-line components.html)
# - 버튼 클릭 → session_state에 요청 저장 → 아래 플레이어가 1회 재생
# - UI/기능은 유지하되, iframe 난립으로 인한 번쩍임을 줄입니다.
# ============================================================

def _talk_tts_request(text: str, audio_url: str = "") -> None:
    txt = (text or "").strip()
    au = (audio_url or "").strip()
    if not txt and not au:
        return
    st.session_state["_talk_tts_nonce"] = int(st.session_state.get("_talk_tts_nonce") or 0) + 1
    st.session_state["_talk_tts_req"] = {
        "text": txt,
        "audio_url": resolve_audio_url(au),
        "nonce": int(st.session_state["_talk_tts_nonce"]),
    }

def _render_talk_tts_player() -> None:
    req = st.session_state.get("_talk_tts_req")
    if not isinstance(req, dict):
        return
    txt = str(req.get("text") or "")
    au = str(req.get("audio_url") or "")
    nonce = int(req.get("nonce") or 0)

    # JS-safe escape
    def _esc(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
             .replace('"', '\"')
             .replace("`", "")
             .replace("\n", " ")
             .replace("\r", " ")
        )

    txt_js = _esc(txt)
    au_js = _esc(au)

    components.html(
        f"""<script>
(function(){{
  // nonce가 바뀔 때마다 재생
  const nonce = {nonce};
  const text = "{txt_js}";
  const audioUrl = "{au_js}";

  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const vs = synth ? (synth.getVoices() || []) : [];
      const ja = vs.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if(!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||"")) || ja.find(v => /日本|japanese/i.test(v.name||"")) || ja[0] || null;
    }} catch(e) {{
      return null;
    }}
  }}

  function speak(){{
    try {{
      if (!window.speechSynthesis) return;
      const synth = window.speechSynthesis;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      u.rate = 1.0; u.pitch = 1.0;
      synth.speak(u);
    }} catch(e) {{}}
  }}

  function playAudio(){{
    try {{
      const a = new Audio(audioUrl);
      a.play().catch(()=>{{ speak(); }});
    }} catch(e) {{
      speak();
    }}
  }}

  if (audioUrl) playAudio();
  else speak();
}})();
</script>""",
        height=0,
    )

def tts_inline_row(role_label: str, text: str, key: str, show_text: bool = True, audio_url: str = ""):
    """문장 오른쪽 스피커 아이콘.
    ✅ PRO 클릭 시: 브라우저에서 바로 재생(오디오/mp3 우선, 없으면 SpeechSynthesis)
    ✅ FREE: 잠금(비활성)
    - Streamlit 버튼을 쓰지 않아, 클릭 시 페이지 rerun(번쩍임)을 유발하지 않습니다.
    """
    txt = (text or "").strip()
    au = resolve_audio_url(audio_url)

    c1, c2, c3 = st.columns([0.18, 0.72, 0.10], vertical_alignment="center")
    with c1:
        st.markdown(f"**{role_label}**")
    with c2:
        if show_text:
            st.markdown(txt if txt else "")
        else:
            st.markdown("&nbsp;", unsafe_allow_html=True)
    with c3:
        disabled = (not IS_PRO) or (not txt)
        # JS-safe
        def _esc(s: str) -> str:
            return (
                (s or "")
                .replace("\\", "\\\\")
                .replace('"', '\"')
                .replace("`", "")
                .replace("\n", " ")
                .replace("\r", " ")
            )
        txt_js = _esc(txt)
        au_js = _esc(au)

        components.html(
            f"""<div style="width:100%;display:flex;justify-content:flex-end;align-items:center;gap:6px;">
  <button id="btn-{key}" {'disabled' if disabled else ''} style="border:0;background:transparent;padding:0;margin:0;
          font-size:1.05rem;cursor:{'not-allowed' if disabled else 'pointer'};opacity:{'0.35' if disabled else '0.95'};">🔊</button>
  {('<span style="font-size:.75rem;letter-spacing:.02em;border:1px solid rgba(0,0,0,.18);border-radius:999px;padding:1px 6px;opacity:.45;">PRO</span>' if (not IS_PRO) else '')}
</div>
<script>
(function(){{
  const btn = document.getElementById("btn-{key}");
  if(!btn) return;
  if(btn.dataset.bound === "1") return;
  btn.dataset.bound = "1";
  const text = "{txt_js}";
  const audioUrl = "{au_js}";
  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const vs = synth ? (synth.getVoices() || []) : [];
      const ja = vs.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if(!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||"")) || ja.find(v => /日本|japanese/i.test(v.name||"")) || ja[0] || null;
    }} catch(e) {{ return null; }}
  }}
  function speak(){{
    try {{
      if (!window.speechSynthesis) return;
      const synth = window.speechSynthesis;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      u.rate = 1.0; u.pitch = 1.0;
      synth.speak(u);
    }} catch(e) {{}}
  }}
  function playAudio(){{
    try {{
      const a = new Audio(audioUrl);
      a.play().catch(()=>{{ speak(); }});
    }} catch(e) {{
      speak();
    }}
  }}
  btn.addEventListener("click", (e)=>{{
    e.preventDefault();
    if (btn.disabled) return;
    if (audioUrl) playAudio();
    else speak();
  }});
}})();
</script>""",
            height=44,
        )

def tts_inline_pair(partner_text: str, answer_text: str, qid: str, show_text: bool = True,
                    partner_audio_url: str = "", answer_audio_url: str = ""):
    """결과 박스: 상대/내 문장을 한 줄씩 + 스피커(문장 오른쪽).
    ✅ PRO 클릭 시: 브라우저에서 바로 재생(오디오/mp3 우선, 없으면 SpeechSynthesis)
    ✅ FREE: 잠금(비활성)
    - Streamlit 버튼을 쓰지 않아, 클릭 시 페이지 rerun(번쩍임)을 유발하지 않습니다.
    """
    p = (partner_text or "").strip()
    a = (answer_text or "").strip()
    p_au = resolve_audio_url(partner_audio_url)
    a_au = resolve_audio_url(answer_audio_url)

    # JS-safe
    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("\\", "\\\\")
            .replace('"', '\"')
            .replace("`", "")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    p_safe = _esc(p)
    a_safe = _esc(a)
    p_au_safe = _esc(p_au)
    a_au_safe = _esc(a_au)

    disabled = (not IS_PRO) or (not (p or a))

    # show_text=False면 텍스트는 숨기고(공백), 버튼만 남김
    show = "block" if show_text else "none"

    html = f"""
<div class="ttspair">
  <div class="row">
    <span class="lab">상대(말)</span>
    <span class="txt" style="display:{show}">{p_safe}</span>
    <button class="btn" id="pbtn-{qid}" aria-label="listen" {'disabled' if (not IS_PRO) or (not p) else ''}>🔊</button>
    {('<span class="pro">PRO</span>' if (not IS_PRO) else '')}
  </div>
  <div class="row">
    <span class="lab">내(말)</span>
    <span class="txt" style="display:{show}">{a_safe}</span>
    <button class="btn" id="abtn-{qid}" aria-label="listen" {'disabled' if (not IS_PRO) or (not a) else ''}>🔊</button>
    {('<span class="pro">PRO</span>' if (not IS_PRO) else '')}
  </div>
</div>
<style>
  .ttspair{{display:flex;flex-direction:column;gap:8px;}}
  .ttspair .row{{display:flex;align-items:center;gap:8px;line-height:1.45;}}
  .ttspair .lab{{min-width:52px;font-weight:700;opacity:.85;}}
  .ttspair .txt{{font-size:1.05rem;}}
  .ttspair .btn{{border:0;background:transparent;padding:0;margin-left:2px;font-size:1.05rem;cursor:pointer;opacity:.95;}}
  .ttspair .btn[disabled]{{cursor:not-allowed;opacity:.35;}}
  .ttspair .pro{{font-size:.75rem;letter-spacing:.02em;border:1px solid rgba(0,0,0,.18);border-radius:999px;padding:1px 6px;opacity:.45;}}
</style>
<script>
(function(){{
  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const vs = synth ? (synth.getVoices() || []) : [];
      const ja = vs.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if(!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||"")) || ja.find(v => /日本|japanese/i.test(v.name||"")) || ja[0] || null;
    }} catch(e) {{ return null; }}
  }}
  function speak(text){{
    try {{
      if(!window.speechSynthesis) return;
      const synth = window.speechSynthesis;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if(v) u.voice = v;
      u.rate = 1.0; u.pitch = 1.0;
      synth.speak(u);
    }} catch(e) {{}}
  }}
  function play(audioUrl, text){{
    if(audioUrl){{
      try{{ const a = new Audio(audioUrl); a.play().catch(()=>{{ speak(text); }}); return; }}catch(e){{}}
    }}
    speak(text);
  }}
  const pbtn = document.getElementById('pbtn-{qid}');
  const abtn = document.getElementById('abtn-{qid}');
  if(pbtn) pbtn.addEventListener('click', (e)=>{{ e.preventDefault(); if(pbtn.disabled) return; play("{p_au_safe}", "{p_safe}"); }});
  if(abtn) abtn.addEventListener('click', (e)=>{{ e.preventDefault(); if(abtn.disabled) return; play("{a_au_safe}", "{a_safe}"); }});
}})();
</script>
"""

    components.html(html, height=180)

def play_audio_or_tts(text: str, audio_url: str, label: str, key: str):
    """PRO: mp3 URL 재생 / FREE: 잠금. URL 없으면 TTS fallback."""
    audio_url = (audio_url or "").strip()
    # URL이 전체가 아니면 BASE_AUDIO_URL을 붙입니다.
    if audio_url and (not audio_url.startswith('http://')) and (not audio_url.startswith('https://')):
        audio_url = BASE_AUDIO_URL.rstrip('/') + '/' + audio_url.lstrip('/')

    if audio_url:
        if IS_PRO:
            if st.button(f"🔊 {label}", key=f"{key}_btn"):
                st.audio(audio_url)
        else:
            st.button(f"🔒 {label} (PRO 전용)", disabled=True, key=f"{key}_lock")
        return

    # URL이 없으면 브라우저 TTS fallback
    if st.button(f"🔊 {label}", key=f"{key}_ttsbtn"):
        tts_button(text, label, key=f"{key}_tts")

def build_choices(row: dict, pool_answers: list[str]) -> list[str]:
    correct = str(row.get("answer_jp", "")).strip()
    qid_seed = str(row.get("qid", "") or "") + "|" + correct
    # ✅ 보기 순서가 '클릭/리런'에 따라 바뀌지 않도록, qid 기반으로 셔플을 고정합니다.
    # (세션키가 초기화되어도 항상 같은 순서로 재생성)
    seed = int(hashlib.md5(qid_seed.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)

    picks: list[str] = []

    for c in ["d1_jp", "d2_jp", "d3_jp"]:
        if c in row:
            v = str(row.get(c, "")).strip()
            if v and v != correct and v not in picks:
                picks.append(v)

    if len(picks) < 3:
        cand = [a for a in pool_answers if a and a != correct and a not in picks]
        rng.shuffle(cand)
        picks += cand[: (3 - len(picks))]

    picks = picks[:3]
    choices = picks + [correct]
    rng.shuffle(choices)
    return choices




pool_answers = pool_df["answer_jp"].astype(str).tolist()

# ============================================================
# ✅ Initialize set (10 qids) + pointer
# ============================================================
if f"{NS}_set_qids" not in st.session_state:
    n = min((SET_LEN if IS_PRO else FREE_SET_LEN), len(pool_df))
    sample = pool_df.sample(n=n, replace=False).reset_index(drop=True)
    qids = sample["qid"].astype(str).tolist()
    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = 0
    st.session_state[f"{NS}_answers"] = {qid: {"selected": None, "ok": None, "spoken": False} for qid in qids}
    st.session_state[f"{NS}_submitted"] = False

qids: list[str] = st.session_state[f"{NS}_set_qids"]
idx: int = int(st.session_state.get(f"{NS}_idx") or 0)
idx = max(0, min(idx, len(qids) - 1))
answers = st.session_state.get(f"{NS}_answers") or {}

# ============================================================
# ✅ Progress header (1/10)
#   - '새 세트' 버튼을 진행 영역 오른쪽으로 이동(필터와 분리)
# ============================================================
progress = (idx + 1) / max(1, len(qids))

p1, p2 = st.columns([1.6, 0.6], vertical_alignment="center")
with p1:
    st.progress(progress)
    st.caption(f"진행: {idx+1}/{len(qids)}")

with p2:
    if st.button("🔄 새 세트", use_container_width=True, type="secondary", key=f"{NS}_new_set"):
        reset_set()
        # st.rerun()  # Streamlit은 버튼 클릭 시 자동 rerun됩니다.

# ============================================================
# ✅ Current question
# ============================================================
qid = qids[idx]
_cur = pool_df[pool_df["qid"].astype(str) == str(qid)]
# ✅ 필터/상황/레벨 변경 등으로 qid가 풀에서 사라질 수 있음 → 안전 처리
if _cur.empty:
    # 가장 첫 문제로 강제 리셋
    st.session_state[f"{NS}_idx"] = 0
    qid = qids[0]
    _cur = pool_df[pool_df["qid"].astype(str) == str(qid)]
if _cur.empty:
    # 선택된 qid가 현재 풀에 없으면 첫 문제로 안전하게 재설정
    qid = str(pool_df.iloc[0].get("qid"))
    st.session_state[f"{NS}_qid"] = qid
    _cur = pool_df[pool_df["qid"].astype(str) == str(qid)]
row = _cur.iloc[0].to_dict()

# options fixed per qid
opt_key = f"{NS}_opts_{qid}"
if opt_key not in st.session_state:
    st.session_state[opt_key] = build_choices(row, pool_answers)
choices: list[str] = st.session_state[opt_key]

# selected
sel_key = f"{NS}_selected_{qid}"
if sel_key not in st.session_state:
    st.session_state[sel_key] = None
selected = st.session_state.get(sel_key)

submitted_key = f"{NS}_submitted_{qid}"
if submitted_key not in st.session_state:
    st.session_state[submitted_key] = False
submitted = bool(st.session_state.get(submitted_key))


# ============================================================
# ✅ Next question helper (명확한 UX) + FAB queryparam hook
# ============================================================
def _go_next_question():
    nxt = idx + 1
    if nxt >= len(qids):
        nxt = 0
    st.session_state[f"{NS}_idx"] = nxt
    # 상태 초기화(다음 문제)
    st.session_state[submitted_key] = False
    st.session_state.pop(sel_key, None)
    st.session_state.pop(f"{NS}_radio_{qid}", None)
    st.session_state.pop(f"{NS}_speak_done_{qid}", None)
    st.session_state.pop(f"{NS}_reward_ready_{qid}", None)
    st.rerun()

# ✅ FAB(우측 하단)에서 URL queryparam으로 다음 이동 요청
try:
    qp = st.query_params
    if str(qp.get("talk_next", "")) == "1":
        # param 먼저 제거(무한루프 방지)
        try:
            del qp["talk_next"]
        except Exception:
            pass
        # 제출된 상태에서만 다음으로 이동(미제출이면 이동하지 않음)
        if submitted:
            _go_next_question()
        else:
            st.rerun()
except Exception:
    pass

# ============================================================
# ✅ Render card
# ============================================================
with st.container(border=True):
    st.markdown(f"**상황**: {row.get('situation_kr','')}")
    # FREE는 듣기가 잠겨 있으니, 문제 단계에서 스크립트를 보여줍니다.
    # 상대(말): PRO는 스크립트 숨김(듣기만), FREE는 스크립트 + (발음 듣기 3회/일) 버튼
    if IS_PRO:
        tts_inline_row("상대(말)", row.get("partner_jp",""), key=f"{qid}_partner_q", show_text=False, audio_url=row.get("partner_mp3","") or row.get("partner_audio","") or row.get("partner_audio_url","") or "")
    else:
        tts_inline_row("상대(말)", row.get("partner_jp",""), key=f"{qid}_partner_q", show_text=True, audio_url=row.get("partner_mp3","") or row.get("partner_audio","") or row.get("partner_audio_url","") or "")
        rem = _free_tts_remaining()
        if rem > 0:
            if st.button(f"🔊 발음 듣기 (무료 {FREE_TTS_QUOTA-rem+1}/{FREE_TTS_QUOTA})", key=f"{qid}_free_tts_q", use_container_width=True):
                _use_free_tts_once()
                components.html(f"""<script>
(function(){{
  try{{
    const synth = window.speechSynthesis;
    function pickJaVoice(){{
      const voices = synth.getVoices() || [];
      const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if (!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||""))
          || ja.find(v => /日本|japanese/i.test(v.name||""))
          || ja[0] || null;
    }}
    const u = new SpeechSynthesisUtterance({(row.get('partner_jp','') or '').replace(chr(10),' ')!r});
    u.lang = "ja-JP";
    const v = pickJaVoice();
    if (v) u.voice = v;
    synth.cancel();
    synth.speak(u);
  }}catch(e){{}}
}})();
</script>""", height=0)
        else:
            st.markdown(
                '<div style="margin-top:6px;display:flex;align-items:center;gap:8px;">'
                '<span style="font-size:12px;background:#FFD54F;color:#000;padding:2px 6px;border-radius:8px;font-weight:800;">PRO</span>'
                '<span style="font-size:0.92rem;opacity:0.85;">발음 듣기는 PRO 전용 (무료 3회 소진)</span>'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    with st.container(border=True):
        st.markdown("**내가 할 말(선택)**")

        # ✅ 보기 선택(속도/안정성 개선)
        # - st.button 4개는 클릭할 때마다 전체가 재렌더링되어 체감이 느릴 수 있어
        # - st.radio 1개 위젯으로 선택만 바꾸면 훨씬 가볍고, 보기 순서도 고정됨
        radio_key = f"{NS}_radio_{qid}"
        # 기존 selected가 있으면 라디오 기본값으로 반영
        if selected and selected in choices:
            default_idx = choices.index(selected)
        else:
            default_idx = 0

        form_key = f"{NS}_form_{qid}"
        with st.form(key=form_key, clear_on_submit=False):
            picked = st.radio(
                label="보기 선택",
                options=choices,
                index=default_idx,
                key=radio_key,
                disabled=submitted,
                label_visibility="collapsed",
            )
            can_submit = bool(picked) and (not submitted)
            submitted_now = st.form_submit_button(
                "정답 제출",
                use_container_width=True,
                disabled=not can_submit,
            )

        # 제출 시에만 선택/제출 상태를 확정
        if submitted_now and (not submitted):
            st.session_state[sel_key] = picked
            st.session_state[submitted_key] = True
            selected = picked
            submitted = True

# ============================================================
# ✅ After submit
# ============================================================
if submitted:
    correct = str(row.get("answer_jp", "")).strip()
    ok = (selected == correct)

    # ✅ 최근 2턴 저장(정답 제출 직후 1회만)
    try:
        snap_key = f"talk_turn_saved_{qid}"
        if not st.session_state.get(snap_key):
            _push_recent_turn({
                "qid": str(qid),
                "situation_kr": str(row.get("situation_kr", "")).strip(),
                "partner_jp": str(row.get("partner_jp", "")).strip(),
                "selected": str(selected or "").strip(),
                "correct": str(correct or "").strip(),
                "ok": bool(ok),
            })
            st.session_state[snap_key] = True
    except Exception:
        pass


    # ============================================================
    # ✅ 오답 상세 저장 (wrong_notes) — 회화도 '단어/정답/내답' 기록
    # ============================================================
    if not ok:
        try:
            sb2 = st.session_state.get("sb_authed") or sb  # hub에서 공유되면 sb_authed 우선
            if sb2 and USER_ID:
                q_text = (str(row.get("q_jp", "")) or str(row.get("situation_kr",""))).strip()
                sb2 = get_authed_sb() or sb2

                if not sb2:

                    _wn_warn("오답 저장 실패: authed client 없음(access_token).")

                else:

                    try:

                        sb2.table("wrong_notes").insert({

                            "user_id": USER_ID,

                            "quiz_type": "talk",

                            "question": q_text if q_text else str(row.get("id", "")),

                            "correct_answer": str(correct),

                            "user_answer": str(selected),

                            "level": "talk",

                        }).execute()

                    except Exception as e:

                        _wn_warn(f"오답 저장 실패: {e}")
        except Exception:
            pass

# 저장(answers)
    answers.setdefault(qid, {})
    answers[qid]["selected"] = selected
    answers[qid]["ok"] = ok
    st.session_state[f"{NS}_answers"] = answers

    st.markdown("---")
    st.subheader("결과")

    if ok:
        st.success("정답 ✅")
    else:
        st.error("오답 ❌")

    # 상대/정답 스크립트 + 해설(제출 후에만)
    with st.container(border=True):
        st.markdown("### 🧑‍🏫 발음/말하기")

        # ✅ 상황(제출 전에도 보이지만, 결과 박스에도 다시 한 번 노출)
        situation = str(row.get("situation_kr", "")).strip()
        if situation:
            st.caption(f"상황: {situation}")

        # ✅ 상대(말) / 내(말) — 스피커 아이콘 버튼은 여기서만 노출
        
        # ✅ 상대(말) / 내(말) — 한 iframe에서 2줄 렌더(간격 촘촘)
        tts_inline_pair(row.get("partner_jp",""), row.get("answer_jp",""), qid=str(qid), show_text=True,
                   partner_audio_url=row.get("partner_mp3","") or row.get("partner_audio","") or row.get("partner_audio_url","") or "",
                   answer_audio_url=row.get("answer_mp3","") or row.get("answer_audio","") or row.get("answer_audio_url","") or "")

        # FREE: 제출 후에도 발음 듣기 하루 3회만 허용 (상대/내 각각 버튼 제공)
        if not IS_PRO:
            rem2 = _free_tts_remaining()
            c1, c2 = st.columns(2)
            with c1:
                if rem2 > 0 and st.button("🔊 상대 발음 듣기", key=f"{qid}_free_tts_partner_after", use_container_width=True):
                    _use_free_tts_once()
                    components.html(f"""<script>
(function(){{
  try{{
    const synth = window.speechSynthesis;
    function pickJaVoice(){{
      const voices = synth.getVoices() || [];
      const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if (!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||""))
          || ja.find(v => /日本|japanese/i.test(v.name||""))
          || ja[0] || null;
    }}
    const u = new SpeechSynthesisUtterance({(row.get('partner_jp','') or '').replace(chr(10),' ')!r});
    u.lang = "ja-JP";
    const v = pickJaVoice();
    if (v) u.voice = v;
    synth.cancel();
    synth.speak(u);
  }}catch(e){{}}
}})();
</script>""", height=0)
                elif rem2 <= 0:
                    st.button("🔒 상대 발음 듣기 (PRO)", key=f"{qid}_free_tts_partner_after_lock", disabled=True, use_container_width=True)
            with c2:
                rem3 = _free_tts_remaining()
                if rem3 > 0 and st.button("🔊 내 발음 듣기", key=f"{qid}_free_tts_answer_after", use_container_width=True):
                    _use_free_tts_once()
                    components.html(f"""<script>
(function(){{
  try{{
    const synth = window.speechSynthesis;
    function pickJaVoice(){{
      const voices = synth.getVoices() || [];
      const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if (!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||""))
          || ja.find(v => /日本|japanese/i.test(v.name||""))
          || ja[0] || null;
    }}
    const u = new SpeechSynthesisUtterance({(row.get('answer_jp','') or '').replace(chr(10),' ')!r});
    u.lang = "ja-JP";
    const v = pickJaVoice();
    if (v) u.voice = v;
    synth.cancel();
    synth.speak(u);
  }}catch(e){{}}
}})();
</script>""", height=0)
                elif rem3 <= 0:
                    st.button("🔒 내 발음 듣기 (PRO)", key=f"{qid}_free_tts_answer_after_lock", disabled=True, use_container_width=True)
# ✅ 하테나쌤 코멘트 (explain_kr 우선, 없으면 hint_kr)
        explain_kr = str(row.get("explain_kr", "")).strip()
        hint = str(row.get("hint_kr", "")).strip()

        if explain_kr:
            st.info("💡 하테나쌤 원포인트 일본어\n\n" + explain_kr)
        elif hint:
            st.info("💡 하테나쌤 원포인트 일본어\n\n" + hint)
        else:
            st.info("💡 하테나쌤 원포인트 일본어\n\n포인트: 상황에서 ‘요청/사과/확인/거절’ 중 무엇인지 먼저 잡고, 그에 맞는 톤(정중/캐주얼)을 고르면 실수가 줄어듭니다.")

        with st.expander("🤖 내용이 어려우면 하테나쌤에게 물어보세요", expanded=False):
            st.markdown("### 💬 하테나쌤 스마트 코치")

            q_default = st.session_state.get("talk_ai_last_q") or ""
            user_q = st.text_input(
                "질문",
                value=str(q_default),
                key=f"talk_ai_q_{qid}",
                placeholder="예) 더 자연스러운 표현도 있어요? / 회화에 도움이 되는 패키지는 뭐예요?",
                label_visibility="collapsed",
            )

            # auto context (cheap)
            ctx_parts = []
            s = str(row.get("situation_kr", "")).strip()
            p = str(row.get("partner_jp", "")).strip()
            a = str(row.get("answer_jp", "")).strip()
            me = str(selected or "").strip()
            ctx_parts.append(f"현재상황: {s}")
            ctx_parts.append(f"상대발화: {p}")
            ctx_parts.append(f"정답표현: {a}")
            if me:
                ctx_parts.append(f"내선택: {me}")
            ctx_parts.append(f"정오답: {'정답' if ok else '오답'}")

            try:
                recent = _recent_turns_summary()
                if recent:
                    ctx_parts.append("최근2턴:\n" + recent)
            except Exception:
                pass

            ctx = "\n".join([x for x in ctx_parts if x]).strip()

            st.caption("핵심을 짚어 질문할수록 더 정밀한 코칭을 받을 수 있어요.")

            ask = st.button("AI 코칭 받기 시작", use_container_width=True, key=f"talk_ai_ask_{qid}")

            if ask and str(user_q).strip():
                st.session_state["talk_ai_last_q"] = str(user_q).strip()
                with st.spinner("하테나쌤 답변 중…"):
                    ans = ai_tutor.ask_hatena(
                        mode="talk",
                        user_input=str(user_q).strip(),
                        context=ctx,
                        meta={
                            "page": "talk",
                            "qid": str(qid),
                            "tag": str(tag),
                            "sub": str(sub) if 'sub' in locals() else "",
                            "submitted": True,
                            "ok": bool(ok),
                        },
                    )
                st.info(ans)

if submitted:
    with st.container(border=True):
        total_cnt = len(qids)
        current_no = idx + 1
        st.markdown(
            f"""
        <div style="display:flex; align-items:baseline; justify-content:space-between; gap:12px;">
          <div style="font-size:1.25rem; font-weight:700;">🎙️ 발음 체크</div>
          <div style="font-size:1rem; opacity:0.85;">📘 진행: {current_no} / {total_cnt}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )


        # ✅ 말하기 녹음(선택)
        # - PRO: 녹음 가능
        # - FREE: PRO 안내 카드 노출
        if IS_PRO:
            _audio = st.audio_input("🎤 (선택) 내 발음을 녹음하고 들어보세요", key=f"{qid}_record")
            if _audio is not None:
                st.audio(_audio)
        else:
            remr = _free_record_remaining()
            if remr > 0:
                st.caption(f"FREE 녹음 남은 횟수: {remr}/{FREE_RECORD_QUOTA} (오늘 기준)")
                _audio = st.audio_input("🎤 (무료) 내 발음을 녹음하고 들어보세요", key=f"{qid}_record_free")
                if _audio is not None:
                    _use_free_record_once()
                    st.audio(_audio)
            else:
                st.markdown(
                    '''
<div style="padding:12px;border:1px solid #FFD54F;border-radius:12px;background:#FFF8E1;">
  <div style="font-weight:800;">🎙️ 발음 녹음 기능은 PRO 전용입니다</div>
  <div style="margin-top:6px;font-size:0.92rem;opacity:0.9;">
    오늘의 무료 녹음 3회를 모두 사용했습니다.
  </div>
  <div style="margin-top:10px;">
    <span style="background:#FFD54F;color:#000;padding:3px 10px;border-radius:10px;font-weight:900;">PRO</span>
  </div>
</div>
''',
                    unsafe_allow_html=True,
                )

        st.caption("정답을 보고 2~3번 따라 말한 뒤, 아래 버튼을 눌러 다음으로 넘어가세요.")
        reward_key = f"{NS}_reward_ready_{qid}"
        if st.button("✅ 다 했어요 (보상 받기)", use_container_width=True, key=f"{NS}_next_after"):
            # ✅ 1단계: 보상만 보여주고, 다음 이동은 사용자가 명확히 누르도록 분리
            st.session_state[reward_key] = True

        if st.session_state.get(reward_key):
            st.success("+2 XP 🎤 (말하기 완료 보상)")
            st.caption("👇 아래 버튼을 누르면 다음 문제로 넘어갑니다.")

            if st.button("➡️ 다음 문제 풀기", use_container_width=True, key=f"{NS}_go_next_after_reward_{qid}"):
                _go_next_question()
# st.rerun()  # Streamlit은 버튼 클릭 시 자동 rerun됩니다.



# ============================================================
# ✅ 우측 하단 바로가기(FAB): 제출 후 "다음 문제" 빠른 이동
# - Streamlit 위젯 클릭 rerun을 피하기 위해, queryparam 방식으로 트리거
# ============================================================
def _render_talk_fab_next():
    if not submitted:
        return
    components.html(
        r"""
<style>
  .talk-fab-next{
    position: fixed;
    right: 16px;
    bottom: 18px;
    z-index: 9999;
    width: 56px;
    height: 56px;
    border-radius: 999px;
    border: 1px solid rgba(0,0,0,.12);
    box-shadow: 0 10px 28px rgba(0,0,0,.16);
    background: white;
    cursor: pointer;
    font-size: 18px;
    font-weight: 800;
    display:flex;
    align-items:center;
    justify-content:center;
    user-select:none;
  }
  .talk-fab-next:active{ transform: translateY(1px); }
</style>
<button class="talk-fab-next" id="talkFabNext" aria-label="다음 문제">➡️</button>
<script>
(function(){
  const b = document.getElementById("talkFabNext");
  if(!b) return;
  if(b.dataset.bound === "1") return;
  b.dataset.bound = "1";
  b.addEventListener("click", () => {
    try{
      const url = new URL(window.location.href);
      url.searchParams.set("talk_next","1");
      window.location.href = url.toString();
    }catch(e){}
  });
})();
</script>
""",
        height=0,
    )

_render_talk_fab_next()

# ============================================================# ✅ Set completion (10문제 모두 제출되면 자동 집계)
# ============================================================

def is_done_one(qid_: str) -> bool:
    return bool(st.session_state.get(f"{NS}_submitted_{qid_}"))


def finalize_set_if_ready():
    if not all(is_done_one(q) for q in qids):
        return

    # 중복 집계 방지
    done_key = f"{NS}_set_done"
    if st.session_state.get(done_key):
        return

    score = 0
    wrong_list: list[dict] = []
    for q in qids:
        tmp = pool_df[pool_df["qid"].astype(str) == str(q)]
        if tmp.empty:
            continue
        r = tmp.iloc[0].to_dict()
        correct = str(r.get("answer_jp", "")).strip()
        sel = st.session_state.get(f"{NS}_selected_{q}")
        ok = (sel == correct)
        score += 1 if ok else 0
        if not ok:
            wrong_list.append({"qid": q, "selected": sel, "correct": correct})

    wrong_count = len(wrong_list)

    # progress 저장(누적)
    prog = load_progress()
    talk_prog = prog.get("talk") or {}
    talk_prog["attempts"] = int(talk_prog.get("attempts") or 0) + len(qids)
    talk_prog["correct"] = int(talk_prog.get("correct") or 0) + score
    talk_prog["wrongs"] = int(talk_prog.get("wrongs") or 0) + wrong_count
    talk_prog["last_set"] = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "tag": tag,
        "level": level,
        "score": score,
        "quiz_len": len(qids),
        "wrong_count": wrong_count,
        "qids": qids,
    }
    prog["talk"] = talk_prog
    save_progress(prog)

    # DB 로그(선택)
    log_attempt(level=level, score=score, quiz_len=len(qids), wrong_count=wrong_count, wrong_list=wrong_list, tag=tag)

    # 홈 공통 streak/오늘세트 + XP(10)
    rec = st.session_state.get("hub_record_completion")
    if callable(rec):
        rec("talk", score, len(qids))

    st.session_state[done_key] = True

    st.balloons()
    st.success(f"🎉 10문제 완주! 점수: {score}/{len(qids)}  ·  오답: {wrong_count}")



# ============================================================
# ✅ TTS single-player renderer (hidden)
# - Render once per rerun, placed here to ensure definition exists (prevents NameError).
# - Plays audio/TTS only when st.session_state['_talk_tts_req'] nonce changes.
# ============================================================
_render_talk_tts_player()

finalize_set_if_ready()
