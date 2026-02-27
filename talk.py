# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations
# BUILD_STAMP_TALK: talk-newset-in-progress-v1 2026-02-22 KST (+09:00)

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib
import os
import difflib
import re

# ============================================================
# ✅ (선택) 한자/가나 표기 차이를 줄이기 위한 히라가나 정규화
# - pykakasi가 설치되어 있으면: 한자/카타카나 → 히라가나로 통일
# - 설치되어 있지 않으면: 원문 그대로(표기 차이에 따른 감점 가능)
# ============================================================
try:
    from pykakasi import kakasi as _kakasi  # type: ignore
    _KKS = _kakasi()
    _KKS.setMode("J", "H")  # Kanji to Hiragana
    _KKS.setMode("K", "H")  # Katakana to Hiragana
    _KKS.setMode("H", "H")  # Hiragana keep
    _KKS_CONV = _KKS.getConverter()
    def _to_hira(s: str) -> str:
        try:
            return _KKS_CONV.do(s or "")
        except Exception:
            return s or ""
except Exception:
    _KKS_CONV = None
    def _to_hira(s: str) -> str:
        return s or ""
import pandas as pd
import streamlit as st


# ============================================================
# ✅ Hotena UI: 타이틀 왼쪽 캐릭터 아이콘(최소 버전)
# ============================================================
import base64
from pathlib import Path
import streamlit as st

def _img_to_data_uri(path: str) -> str:
    p = Path(path)
    b = p.read_bytes()
    ext = p.suffix.lower().lstrip(".")
    mime = "png" if ext == "png" else ext
    return f"data:image/{mime};base64," + base64.b64encode(b).decode("utf-8")

def hotena_title(icon_path: str, title: str, size_px: int = 56, gap_px: int = 6,
                 right_text: str | None = None, text_nudge_px: int = 0):
    """
    아이콘 바닥과 텍스트 바닥을 최대한 맞춤.
    text_nudge_px로 텍스트를 1~4px 정도 아래로 미세 조정 가능.
    """
    try:
        uri = _img_to_data_uri(icon_path)
        right_html = (
            f'<div style="margin-left:auto;font-size:0.98rem;opacity:0.85;'
            f'line-height:1; transform:translateY({text_nudge_px}px);">{right_text}</div>'
            if right_text else ""
        )

        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-end;gap:{gap_px}px;margin:4px 0 10px 0;">
              <img src="{uri}" style="
                width:{size_px}px;height:{size_px}px;
                object-fit:contain;flex:0 0 auto;
                display:block;   /* ✅ 이미지 아래 베이스라인 갭 제거 */
              " />
              <div style="
                font-size:1.18rem;font-weight:900;
                line-height:2;   /* ✅ 글 박스 바닥을 더 정확히 */
                white-space:nowrap;
                transform:translateY({text_nudge_px}px); /* ✅ 필요시 1~4px */
              ">{title}</div>
              {right_html}
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        st.markdown(f"### {title}")

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
    "basic": "기본",
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


# ============================================================
# ✅ Pronunciation score (A안: 서버 STT → 텍스트 유사도 점수)
# - "보기 선택" 단계에는 영향을 주지 않도록, 제출 후/버튼 클릭 시에만 실행
# ============================================================
def _norm_jp(s: str) -> str:
    s = (s or "").strip()
    # 공백/전각공백 제거
    s = s.replace(" ", "").replace("\\u3000", "")
    # 흔한 문장부호 제거
    s = re.sub(r"[、。．，!！?？…]+", "", s)
    # ✅ 표기 차이를 줄이기 위해 히라가나로 통일(가능할 때만)
    s = _to_hira(s)
    return s

def _bigrams(s: str) -> set[str]:
    return {s[i:i+2] for i in range(len(s)-1)} if len(s) >= 2 else set()

def _levenshtein(a: str, b: str) -> int:
    # O(len(a)*len(b)) DP
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]

def _similarity_score(a: str, b: str, gate: float = 0.15, floor_to_zero: int = 15) -> int:
    """발음 점수(0~100):
    1) 2글자 bigram 겹침이 너무 적으면(완전 다른 문장) 0점
    2) 편집거리(순서 포함) 기반 점수
    3) 너무 낮은 점수는 0으로 정리(선택)
    """
    a2, b2 = _norm_jp(a), _norm_jp(b)
    if not a2 or not b2:
        return 0

    # 1) 완전 다른 문장 차단
    ba = _bigrams(b2)
    if ba:
        overlap = len(_bigrams(a2) & ba) / max(1, len(ba))
        if overlap < gate:
            return 0

    # 2) 순서 기반 점수(편집거리)
    dist = _levenshtein(a2, b2)
    max_len = max(len(a2), len(b2))
    score = int(round(100 * (1 - dist / max_len)))

    # 3) 바닥값 정리
    if score < int(floor_to_zero):
        return 0
    return max(0, min(100, score))

def _openai_transcribe_bytes(audio_bytes: bytes, mime: str = "audio/wav") -> str:
    # OpenAI Python SDK (new) 사용. 없으면 예외로 안내.
    api_key = (st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else "") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.") from e

    client = OpenAI(api_key=api_key)
    # 파일 객체 형태로 전달
    file_tuple = ("speech.wav", audio_bytes, mime)
    try:
        out = client.audio.transcriptions.create(
            model=model,
            file=file_tuple,
        )
        # SDK 버전에 따라 text 속성/문자열 반환이 다를 수 있어 안전 처리
        txt = getattr(out, "text", None)
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
        if isinstance(out, str) and out.strip():
            return out.strip()
        # dict 형태 fallback
        if isinstance(out, dict):
            t = out.get("text")
            if isinstance(t, str):
                return t.strip()
        return ""
    except Exception as e:
        raise RuntimeError(f"STT 실패: {e}") from e


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
# ✅ Filters (상황(tag))
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
if "mode" in DF_BASE.columns:
    # 기본값: real(실전회화)만. 다른 모드가 없으면 전체 사용.
    _real = DF_BASE[DF_BASE["mode"].astype(str).str.lower() == "real"]
    if not _real.empty:
        DF_BASE = _real.copy()

# --- tag(상황) 라벨: 기본값 + CSV에 없는 태그는 그대로 노출 ---
TAG_LABELS = {
    "aisatsu": "인사말",
    "understand": "이해",
    "travel": "여행",
    "shopping": "쇼핑",
    "food": "음식/카페",
    "call": "전화/온라인",
    "business": "비즈니스",
    "interview": "면접",
    "emergency": "긴급/트러블",
}

def _tag_label(t: str) -> str:
    t = str(t)
    return TAG_LABELS.get(t, t)

# ✅ CSV에 존재하는 tag 자동 수집
if "tag" in DF_BASE.columns:
    tag_options = sorted([x for x in DF_BASE["tag"].astype(str).tolist() if str(x).strip()])
    # 중복 제거 + 순서 유지(정렬 유지하려면 set 사용)
    tag_options = sorted(set(tag_options))
else:
    tag_options = []

if not tag_options:
    st.warning("해당 상황의 회화 문제가 없습니다. (CSV의 tag 확인)")
    st.stop()

tag = st.selectbox(
    "상황 선택",
    options=tag_options,
    format_func=_tag_label,
    key=f"{NS}_tag",
)

# ✅ 유형(sub) 선택 (CSV에 sub 컬럼이 있으면 노출)
SUB_LABEL = {
    "__all__": "전체",
    # aisatsu 쪽에서 쓰는 값들
    "home": "집/가정",
    "morning": "아침",
    "day": "낮/친구",
    "evening": "저녁/밤",
    "thanks": "감사",
    "apology": "사과",
    "work": "회사 기본",
    "meeting": "미팅/첫인사",
    "phone": "전화",
    "basic": "기본",
    "daily": "일상",
    # understand 등에서 쓰는 값들
    "mixed": "혼합",
}

def _sub_label(s: str) -> str:
    s = str(s)
    return SUB_LABEL.get(s, s)

sub = "__all__"

# ✅ 유형(sub)은 '선택된 tag' 안에서만 보여주기(다른 tag의 sub가 섞여 나오면 혼란)
has_sub_col = "sub" in DF_BASE.columns

subs_in_tag = []
if has_sub_col:
    _df_tag = DF_BASE[DF_BASE["tag"].astype(str) == str(tag)].copy()
    subs_in_tag = [x for x in _df_tag["sub"].astype(str).tolist() if str(x).strip()]

# tag 안에 sub 값이 2개 이상 있을 때만 노출(1개면 자동 선택)
subs_in_tag = sorted(set([str(x).strip() for x in subs_in_tag if str(x).strip()]))

if len(subs_in_tag) >= 2:
    sub_options = ["__all__"] + subs_in_tag
    sub = st.selectbox(
        "유형 선택",
        options=sub_options,
        format_func=_sub_label,
        key=f"{NS}_sub",
    )
elif len(subs_in_tag) == 1:
    # ✅ 1개뿐이면 드롭다운은 숨기되, 사용자에게는 '고정된 유형'을 표시
    sub = subs_in_tag[0]
    try:
        st.caption(f"유형: {_sub_label(sub)} (고정)")
    except Exception:
        pass
else:
    # sub 컬럼이 없거나, 해당 tag는 sub가 비어있음
    sub = "__all__"

# 레벨 선택은 사용하지 않음(현재는 N4~N3 혼합 운영)
level = "mix"

pool_df = DF_BASE[(DF_BASE["tag"] == tag)].copy().reset_index(drop=True)
if ("sub" in DF_BASE.columns) and sub != "__all__":
    pool_df = pool_df[pool_df["sub"].astype(str) == str(sub)].copy().reset_index(drop=True)

if pool_df.empty:
    st.warning("해당 상황의 회화 문제가 없습니다. (CSV의 tag/sub 확인)")
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
                    partner_audio_url: str = "", answer_audio_url: str = "",
                    partner_kr: str = "", answer_kr: str = ""):
    '''결과 박스: 상대/내 문장을 한 줄씩 + 스피커(문장 오른쪽).
    ✅ PRO 클릭 시: 브라우저에서 바로 재생(오디오/mp3 우선, 없으면 SpeechSynthesis)
    ✅ FREE: 잠금(비활성)
    - Streamlit 버튼을 쓰지 않아, 클릭 시 페이지 rerun(번쩍임)을 유발하지 않습니다.
    '''
    p = (partner_text or "").strip()
    a = (answer_text or "").strip()
    p_au = resolve_audio_url(partner_audio_url)
    a_au = resolve_audio_url(answer_audio_url)

    # JS-safe
    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("`", "")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    p_safe = _esc(p)
    a_safe = _esc(a)
    pkr_safe = _esc((partner_kr or "").strip())
    akr_safe = _esc((answer_kr or "").strip())
    p_au_safe = _esc(p_au)
    a_au_safe = _esc(a_au)

    disabled = (not IS_PRO) or (not (p or a))

    # show_text=False면 텍스트는 숨기고(공백), 버튼만 남김
    show = "block" if show_text else "none"

    # ✅ 컴포넌트 높이(불필요 공백 최소화)
    has_pkr = bool(pkr_safe)
    has_akr = bool(akr_safe)
    height = 154
    if show_text:
        if has_pkr:
            height += 22
        if has_akr:
            height += 22

    html = f"""
<div class="ttspair">
  <div class="row bubble bubble-p">
    <span class="lab">상대(말)</span>
    <div class="txtwrap" style="display:{show}">
      <div class="jp">{p_safe}</div>
      <div class="kr" style="display:{'block' if has_pkr else 'none'}">{pkr_safe}</div>
    </div>
    <button class="btn" id="pbtn-{qid}" aria-label="listen" {'disabled' if disabled or (not p) else ''}>🔊</button>
    {('<span class="pro">PRO</span>' if (not IS_PRO) else '')}
  </div>

  <div class="row bubble bubble-a">
    <span class="lab">내(말)</span>
    <div class="txtwrap" style="display:{show}">
      <div class="jp">{a_safe}</div>
      <div class="kr" style="display:{'block' if has_akr else 'none'}">{akr_safe}</div>
    </div>
    <button class="btn" id="abtn-{qid}" aria-label="listen" {'disabled' if disabled or (not a) else ''}>🔊</button>
    {('<span class="pro">PRO</span>' if (not IS_PRO) else '')}
  </div>
</div>

<style>
  /* ✅ 무지/미니멀 A안 + 말풍선 각각 아웃라인(레이아웃 영향 없음: box-shadow) */
  .ttspair{{display:flex;flex-direction:column;gap:8px;}}
  .ttspair .row{{display:flex;align-items:flex-start;gap:10px;line-height:1.35;}}
  .ttspair .bubble{{border-radius:14px; box-shadow:0 0 0 1px rgba(0,0,0,.12);}}
  .ttspair .bubble-p{{box-shadow:0 0 0 1px rgba(0,0,0,.20);}}
  .ttspair .bubble-a{{box-shadow:0 0 0 1px rgba(0,0,0,.12);}}

  .ttspair .lab{{min-width:52px;font-weight:650;opacity:.82;flex:0 0 auto;padding:10px 0 10px 10px;}}
  .ttspair .txtwrap{{flex:1 1 auto;min-width:0;white-space:normal;overflow-wrap:anywhere;word-break:break-word;padding:10px 0;}}
  .ttspair .jp{{font-size:1.03rem;font-weight:560;line-height:1.35;letter-spacing:.01em;}}
  .ttspair .kr{{margin-top:3px;font-size:.86rem;line-height:1.25;opacity:.72;}}
  .ttspair .btn{{border:0;background:transparent;padding:10px 10px 10px 0;margin-left:2px;font-size:1.05rem;cursor:pointer;opacity:.95;}}
  .ttspair .btn[disabled]{{cursor:not-allowed;opacity:.35;}}
  .ttspair .pro{{align-self:flex-start;margin-top:10px;font-size:.75rem;letter-spacing:.02em;border:1px solid rgba(0,0,0,.18);border-radius:999px;padding:1px 6px;opacity:.45;}}
</style>

<script>
(function(){{
  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const vs = synth ? (synth.getVoices() || []) : [];
      const ja = vs.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if(!ja.length) return null;
      const pref = ja.find(v => /female|woman|kyoko|haruka|nanami|mizuki|yuna/i.test(String(v.name||"")));
      return pref || ja[0];
    }} catch(e) {{
      return null;
    }}
  }}

  function speak(text){{
    try {{
      const synth = window.speechSynthesis;
      if(!synth) return;
      const u = new SpeechSynthesisUtterance(text || "");
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if(v) u.voice = v;
      synth.cancel();
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
<script>
(function(){{
  function send(){{
    try{{
      var h = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0
      );
      if (window.parent){{
        window.parent.postMessage({{isStreamlitMessage:true, type:"streamlit:setFrameHeight", height:h + 12}}, "*");
      }}
    }}catch(e){{}}
  }}
  try{{
    if (window.ResizeObserver){{
      var ro = new ResizeObserver(function(){{ send(); }});
      ro.observe(document.body);
    }}
  }}catch(e){{}}
  window.addEventListener("load", function(){{ setTimeout(send, 30); }});
  setTimeout(send, 80);
}})();
</script>


"""

    components.html(html, height=10, scrolling=False)

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

# ✅ FAB에서 URL queryparam으로 다음 이동 요청
try:
    qp = st.query_params
    v = str(qp.get("talk_next", "")).strip()
    if v:
        if st.session_state.get("_talk_next_seen") != v:
            st.session_state["_talk_next_seen"] = v
            try:
                del qp["talk_next"]
            except Exception:
                pass
            if submitted:
                _go_next_question()
        # 미제출이면 아무 것도 하지 않음(추가 rerun 금지)
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

        # ✅ 초기 선택은 비워두기: 기존 선택이 있을 때만 index 지정
        default_idx = choices.index(selected) if (selected and selected in choices) else None

        picked = st.radio(
            label="보기 선택",
            options=choices,
            index=default_idx,  # None이면 미선택 상태
            key=radio_key,
            disabled=submitted,
            label_visibility="collapsed",
        )

        # ✅ radio는 선택 시 즉시 rerun되므로, 버튼 활성화가 즉시 반영됨
        can_submit = bool(picked) and (not submitted)
        submitted_now = st.button(
            "정답 제출",
            use_container_width=True,
            disabled=not can_submit,
            key=f"{NS}_submit_{qid}",
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
        hotena_title("assets/hotena_talk/icons_title/icon_pronounce_title.png", "발음/말하기")

        # ✅ 상황(제출 전에도 보이지만, 결과 박스에도 다시 한 번 노출)
        situation = str(row.get("situation_kr", "")).strip()
        if situation:
            st.caption(f"상황: {situation}")

        # ✅ 상대(말) / 내(말) — 스피커 아이콘 버튼은 여기서만 노출
        
        # ✅ 상대(말) / 내(말) — 한 iframe에서 2줄 렌더(간격 촘촘)
        tts_inline_pair(
            row.get("partner_jp",""),
            row.get("answer_jp",""),
            qid=str(qid),
            show_text=True,
            partner_audio_url=(row.get("partner_mp3","") or row.get("partner_audio","") or row.get("partner_audio_url","") or ""),
            answer_audio_url=(row.get("answer_mp3","") or row.get("answer_audio","") or row.get("answer_audio_url","") or ""),
            partner_kr=(row.get("partner_kr","") or row.get("partner_ko","") or row.get("partner_kor","") or ""),
            answer_kr=(row.get("answer_kr","") or row.get("answer_ko","") or row.get("answer_kor","") or ""),
        )

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
# ============================================================
        # ✅ 제출 이후에만 원포인트 + 스마트코치 표시
        # ============================================================
        if submitted:

            # ------------------------------------
            # 💡 원포인트 일본어
            # ------------------------------------
            explain_kr = str(row.get("explain_kr", "")).strip()
            hint = str(row.get("hint_kr", "")).strip()

            if explain_kr:
                st.markdown("<div style='margin-top:-18px'></div>", unsafe_allow_html=True)
                st.info("💡 하테나쌤 원포인트 일본어\n\n" + explain_kr)
            elif hint:
                st.markdown("<div style='margin-top:-18px'></div>", unsafe_allow_html=True)
                st.info("💡 하테나쌤 원포인트 일본어\n\n" + hint)
            else:
                st.markdown("<div style='margin-top:-18px'></div>", unsafe_allow_html=True)
                st.info(
                    "💡 하테나쌤 원포인트 일본어\n\n"
                    "포인트: 상황에서 ‘요청/사과/확인/거절’ 중 무엇인지 먼저 잡고, "
                    "그에 맞는 톤(정중/캐주얼)을 고르면 실수가 줄어듭니다."
                )

            # ------------------------------------
            # 🤖 스마트 코치
            # ------------------------------------
            with st.expander("🤖 원포인트 일본어가 어려우면 하테나쌤에게 물어보세요", expanded=False):

                hotena_title("assets/hotena_talk/icons_title/icon_coach_title.png", "스마트코치")

                st.markdown("### 💬 하테나쌤 스마트 코치")

                q_default = st.session_state.get("talk_ai_last_q") or ""
                user_q = st.text_input(
                    "질문",
                    value=str(q_default),
                    key=f"talk_ai_q_{qid}",
                    placeholder="예) 더 자연스러운 표현도 있어요?",
                    label_visibility="collapsed",
                )

                st.caption("회화 표현·뉘앙스·자연스러움 위주 질문에 최적화되어 있어요.")

                ask = st.button(
                    "AI 코칭 받기 시작",
                    use_container_width=True,
                    key=f"talk_ai_ask_{qid}",
                )

                coach_slot = st.empty()

                if ask and str(user_q).strip():

                    question = str(user_q).strip()
                    st.session_state["talk_ai_last_q"] = question

                    # 👉 일반 문의 분기
                    general_keywords = [
                        "패키지", "요금", "가격", "결제",
                        "환불", "기능", "프로", "무료",
                        "상담", "문의", "톡", "네이버", "교재"
                    ]

                    if any(k in question for k in general_keywords):

                        coach_slot.info(
                            "📌 해당 문의는 회화 코칭 범위를 벗어납니다.\n\n"
                            "👉 정확한 안내는 **하테나쌤 톡**으로 문의해주세요 🙂"
                        )

                        st.link_button(
                            "💬 톡 문의하기",
                            "http://talk.naver.com/W45141",
                            use_container_width=True
                        )

                    else:
                        # 회화 질문일 때만 AI 호출
                        def _is_ctx_relevant(q: str, row_: dict) -> bool:
                            q = (q or "").strip().lower()
                            if not q:
                                return False
                            # If question explicitly refers to correctness/nuance/why, treat as relevant
                            key_hits = ["정답", "오답", "왜", "뉘앙스", "자연", "어색", "차이", "문법", "표현", "대안", "바꿔", "맞아", "틀려"]
                            if any(k in q for k in key_hits):
                                return True
                            # If includes Japanese chars, likely about the expression
                            if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", q):
                                return True
                            # If includes a snippet from this item's fields, it's relevant
                            s = str(row_.get("situation_kr", "") or "").strip().lower()
                            p = str(row_.get("partner_jp", "") or "").strip().lower()
                            a = str(row_.get("answer_jp", "") or "").strip().lower()
                            for ref in (p, a):
                                if ref and ref[:8] in q:
                                    return True
                            # Default: treat as general question → do NOT bind to current quiz context
                            return False


                        use_ctx = _is_ctx_relevant(question, row)
                        ctx_parts = [] if use_ctx else None

                        s = str(row.get("situation_kr", "")).strip()
                        p = str(row.get("partner_jp", "")).strip()
                        a = str(row.get("answer_jp", "")).strip()
                        me = str(selected or "").strip()

                        if ctx_parts is not None and s:
                            ctx_parts.append(f"현재상황: {s}")
                        if ctx_parts is not None and p:
                            ctx_parts.append(f"상대발화: {p}")
                        if ctx_parts is not None and a:
                            ctx_parts.append(f"정답표현: {a}")
                        if ctx_parts is not None and me:
                            ctx_parts.append(f"내선택: {me}")

                        if ctx_parts is not None:
                            ctx_parts.append(f"정오답: {'정답' if ok else '오답'}")

                        ctx = "\n".join(ctx_parts) if isinstance(ctx_parts, list) else ""

                        with st.spinner("하테나쌤 답변 중…"):
                            ans = ai_tutor.ask_hatena(
                                mode="talk",
                                user_input=question,
                                context=ctx,
                                meta={
                                    "page": "talk",
                                    "qid": str(qid),
                                    "submitted": True,
                                    "ctx_used": bool(ctx),
                                    "ok": bool(ok),
                                    "is_admin": bool(
                                        st.session_state.get("is_admin", False)
                                        or st.session_state.get("is_admin_cached", False)
                                    ),
                                },
                            )

                        coach_slot.info(ans)# ============================================================
# ✅ (추가) 정답 발음 확인 버튼용: 플레이어 없이 즉시 재생(JS Audio / TTS)
# - 브라우저에 플레이어 UI가 뜨지 않게, new Audio().play()로만 재생
# - JS 문자열은 % 포맷을 써서 f-string 중괄호 오류를 방지
# ============================================================
import json as _json

def _play_audio_html_oneclick(url: str, uid: str, label: str = "🔊 정답 발음 확인") -> None:
    """One-click hidden audio play (no player UI). Works on iOS/Android/PC."""
    url = (url or "").strip()
    if not url:
        return
    try:
        safe_url = _json.dumps(url)
        html = f"""
        <div style="margin:6px 0 2px 0;">
          <audio id="aud_{uid}" preload="none" src={safe_url}></audio>
          <button type="button"
            onclick="(function(){{try{{var a=document.getElementById('aud_{uid}');if(!a)return;a.currentTime=0;a.play();}}catch(e){{}}}})()"
            style="width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(0,0,0,.15);background:#fff;font-size:16px;font-weight:700;cursor:pointer;">
            {label}
          </button>
        </div>
        """
        components.html(html, height=70)
    except Exception:
        pass


def _play_audio_no_player(url: str) -> None:
    url = (url or "").strip()
    if not url:
        return
    try:
        components.html(
            "<script>(function(){try{new Audio(%s).play();}catch(e){}})();</script>" % _json.dumps(url),
            height=0,
        )
    except Exception:
        pass

def _speak_no_player(text: str) -> None:
    txt = (text or "").strip()
    if not txt:
        return
    try:
        components.html(
            "<script>(function(){try{const synth=window.speechSynthesis;if(!synth)return;"
            "function pick(){const vs=synth.getVoices()||[];const ja=vs.filter(v=>(String(v.lang||'').toLowerCase().startsWith('ja')));"
            "return ja.find(v=>/google/i.test(v.name||''))||ja[0]||null;}"
            "const u=new SpeechSynthesisUtterance(%s);u.lang='ja-JP';const v=pick();if(v)u.voice=v;"
            "synth.cancel();synth.speak(u);}catch(e){}})();</script>" % _json.dumps(txt),
            height=0,
        )
    except Exception:
        pass

if submitted:
    with st.container(border=True):
        total_cnt = len(qids)
        current_no = idx + 1
        hotena_title("assets/hotena_talk/icons_title/icon_check_title.png", "발음 체크", size_px=56, right_text=f"📘 진행: {current_no} / {total_cnt}")


        
        # ✅ 정답 발음 확인 (플레이어 없이)
        # - PRO: 무제한
        # - FREE: 남은 발음 듣기(무료 3회/일) 내에서 사용
        _ans_audio = (
            row.get("answer_mp3", "")
            or row.get("answer_audio", "")
            or row.get("answer_audio_url", "")
            or ""
        )
        _ans_audio = resolve_audio_url(str(_ans_audio))
        _ans_txt = str(row.get("answer_jp", "") or "").strip()

        if IS_PRO:
            # ✅ PRO: universal one-click no-player playback (all platforms)
            if _ans_audio:
                _play_audio_html_oneclick(_ans_audio, uid=f"{qid}_ans_pron_html", label="🔊 정답 발음 확인")
            else:
                if st.button("🔊 정답 발음 확인", key=f"{qid}_ans_pron_tts", use_container_width=True):
                    _speak_no_player(_ans_txt)
        else:
            _rem_tts = _free_tts_remaining()
            if _rem_tts > 0:
                if st.button(
                    f"🔊 정답 발음 확인 (무료 {FREE_TTS_QUOTA-_rem_tts+1}/{FREE_TTS_QUOTA})",
                    key=f"{qid}_ans_pron_free",
                    use_container_width=True,
                ):
                    _use_free_tts_once()
                    if _ans_audio:
                        _play_audio_no_player(_ans_audio)
                    else:
                        _speak_no_player(_ans_txt)
            else:
                st.button("🔒 정답 발음 확인 (PRO)", key=f"{qid}_ans_pron_lock", disabled=True, use_container_width=True)
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

        # ✅ 말하기 점수 (A안: 서버 STT 기반) — 제출 후/버튼 클릭 시에만 실행
        # - 보기 선택 단계에는 영향을 주지 않습니다.
        score_key = f"talk_pron_score_{qid}"
        text_key = f"talk_pron_text_{qid}"
        err_key = f"talk_pron_err_{qid}"

        audio_obj = locals().get("_audio", None)
        has_audio = audio_obj is not None

        # ✅ 자동 점수 계산 (녹음이 새로 들어왔을 때 1회만)
        # - 보기 선택 단계/리런에 영향 없도록, 오디오 해시가 바뀐 경우에만 실행합니다.
        if has_audio:
            try:
                _b = b""
                _mime = "audio/wav"
                _mime = getattr(audio_obj, "type", None) or "audio/wav"
                if hasattr(audio_obj, "getvalue"):
                    _b = audio_obj.getvalue()
                elif hasattr(audio_obj, "read"):
                    _b = audio_obj.read()
                _h = hashlib.sha1(_b).hexdigest() if _b else ""
            except Exception:
                _b, _mime, _h = b"", "audio/wav", ""

            _last_hash_key = f"talk_pron_lasthash_{qid}"
            if _h and st.session_state.get(_last_hash_key) != _h:
                st.session_state[_last_hash_key] = _h
                st.session_state.pop(err_key, None)
                with st.spinner("말하기 점수 계산 중..."):
                    try:
                        _txt = _openai_transcribe_bytes(_b, mime=_mime)
                        st.session_state[text_key] = _txt
                        st.session_state[score_key] = _similarity_score(_txt, str(row.get("answer_jp", "")))
                    except Exception as _e:
                        st.session_state[err_key] = str(_e)

        c_sc1, c_sc2 = st.columns([0.72, 0.28], vertical_alignment="center")
        with c_sc1:
            hotena_title("assets/hotena_talk/icons_title/icon_score_title.png", "말하기 점수", size_px=44, gap_px=0)
        with c_sc2:
            # ✅ '다시 계산'은 네트워크/브라우저 상태 등으로 자동 계산이 실패했을 때만 노출
            show_recalc = bool(st.session_state.get(err_key))
            do_calc = False
            if show_recalc:
                do_calc = st.button("다시 계산", use_container_width=True, disabled=not has_audio, key=f"{qid}_pron_calc")

        if do_calc:
            try:
                b = b""
                mime = "audio/wav"
                if audio_obj is not None:
                    mime = getattr(audio_obj, "type", None) or "audio/wav"
                    if hasattr(audio_obj, "getvalue"):
                        b = audio_obj.getvalue()
                    elif hasattr(audio_obj, "read"):
                        b = audio_obj.read()
                txt = _openai_transcribe_bytes(b, mime=mime)
                st.session_state[text_key] = txt
                st.session_state[score_key] = _similarity_score(txt, str(row.get("answer_jp", "")))
                st.session_state.pop(err_key, None)
            except Exception as e:
                st.session_state[err_key] = str(e)

        if st.session_state.get(err_key):
            st.warning("점수 계산 실패: " + str(st.session_state.get(err_key)))

        # 결과 표시(계산된 경우)
        if st.session_state.get(text_key):
            st.caption("인식 결과(참고)")
            st.write(str(st.session_state.get(text_key)))

        if st.session_state.get(score_key) is not None:
            st.metric("점수", int(st.session_state.get(score_key) or 0))

        st.caption("정답을 보고 2~3번 따라 말해 보세요. 녹음이 끝나면 점수가 자동으로 계산됩니다.")
        reward_key = f"{NS}_reward_ready_{qid}"
        if st.button("✅ 다 했어요 (보상 받기)", use_container_width=True, key=f"{NS}_next_after"):
            # ✅ 규칙: '녹음'을 했고, 점수가 100점일 때만 보상을 받습니다.
            _sc = int(st.session_state.get(score_key) or 0) if st.session_state.get(score_key) is not None else 0
            _said = str(st.session_state.get(text_key) or "").strip()
            if _said and _sc == 100:
                # ✅ 1단계: 보상만 보여주고, 다음 이동은 사용자가 명확히 누르도록 분리
                st.session_state[reward_key] = True
            else:
                st.warning("보상은 '녹음 + 100점'일 때만 받을 수 있어요. 먼저 녹음하고 100점을 만들어 주세요.")


        if st.session_state.get(reward_key):
            hotena_title("assets/hotena_talk/icons_title/icon_reward_title.png", "말하기 완료 보상")
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
