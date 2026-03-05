# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations
# BUILD_STAMP_TALK: talk-newset-in-progress-v1 2026-02-22 KST (+09:00)

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import math
import hashlib
import os
import difflib
import re
import io

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

import core

# ============================================================
# ✅ 오늘의 회화 레벨 게이지(일일 완료 카운트)
# ============================================================
def _kst_today_str() -> str:
    # 서버가 KST가 아닐 수 있으므로 +9 보정
    try:
        now = datetime.utcnow() + timedelta(hours=9)
    except Exception:
        now = datetime.now()
    return now.date().isoformat()

def _get_today_speech_done() -> int:
    """오늘 말한 문장 수(일 단위).
    - session_state가 날아가도, profiles.progress['talk']['speech_done']에서 복구
    - 날짜가 바뀌면 자동 0 리셋(+progress에도 반영)
    """
    key_date = "talk_speech_done_date"
    key_cnt = "talk_speech_done_cnt"
    today = _kst_today_str()

    # ✅ 1) session_state가 오늘로 세팅되어 있으면 그대로 사용
    if st.session_state.get(key_date) == today and st.session_state.get(key_cnt) is not None:
        return int(st.session_state.get(key_cnt) or 0)

    # ✅ 2) progress에서 복구 시도
    cnt_from_db = 0
    try:
        prog = load_progress()  # may raise if sb not ready
        talk_prog = (prog or {}).get("talk") or {}
        sd = talk_prog.get("speech_done") or {}
        if isinstance(sd, dict) and str(sd.get("date") or "") == today:
            cnt_from_db = int(sd.get("cnt") or 0)
    except Exception:
        cnt_from_db = 0

    st.session_state[key_date] = today
    st.session_state[key_cnt] = int(cnt_from_db)

    # ✅ 오늘로 progress가 없으면 0으로 초기화(다음 복구 안정)
    if int(cnt_from_db) == 0:
        try:
            prog = load_progress()
            talk_prog = prog.get("talk") or {}
            sd = talk_prog.get("speech_done")
            if not (isinstance(sd, dict) and str(sd.get("date") or "") == today):
                talk_prog["speech_done"] = {"date": today, "cnt": 0}
                prog["talk"] = talk_prog
                save_progress(prog)
        except Exception:
            pass

    return int(st.session_state.get(key_cnt) or 0)

def _inc_today_speech_done(n: int = 1) -> None:
    """오늘 말한 문장 수 증가 + progress에도 즉시 저장."""
    key_date = "talk_speech_done_date"
    key_cnt = "talk_speech_done_cnt"
    today = _kst_today_str()

    cur = _get_today_speech_done()
    new_cnt = int(cur) + int(n)

    st.session_state[key_date] = today
    st.session_state[key_cnt] = new_cnt

    # progress 저장(일 단위, 전역 카운트)
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        talk_prog["speech_done"] = {"date": today, "cnt": int(new_cnt)}
        prog["talk"] = talk_prog
        save_progress(prog)
    except Exception:
        pass


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
FREE_SET_LEN = SET_LEN  # ✅ FREE도 '문제 수' 제한 없음(세트는 10문제 기준 유지)
FREE_TTS_QUOTA = 3  # FREE 발음 듣기 3회(일)
FREE_RECORD_QUOTA = 3  # FREE 녹음 3회(일)

# 🔗 PRO 업그레이드 안내 URL (나중에 바꿀 수 있게 env로 교체 가능)
UPGRADE_URL = os.getenv("HOTENA_UPGRADE_URL") or "/pricing"


def _render_upgrade_cta(label: str = "✨ PRO로 업그레이드", help_text: str = ""):
    """PRO 결제/안내로 연결. Streamlit 버전에 따라 link_button이 없을 수 있어 fallback 제공."""
    if help_text:
        st.caption(help_text)
    try:
        st.link_button(label, UPGRADE_URL, use_container_width=True)
    except Exception:
        st.markdown(f"[{label}]({UPGRADE_URL})")



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

    # FREE 플랜: '상대(말)' 라벨과 일본어 문장 간격을 더 타이트하게
    _gap = "2px" if not IS_PRO else "6px"
    _label_min = "0px" if not IS_PRO else "54px"
    _label_align = "left" if not IS_PRO else "right"
    _label_pad = "4px" if not IS_PRO else "0px"

    st.markdown(
        f"""
<style>
.talk-bubble-row{{display:flex;gap:{_gap};align-items:flex-end;margin:6px 0;}}
.talk-bubble-label{{min-width:{_label_min};font-weight:800;opacity:.85;white-space:nowrap;text-align:{_label_align};padding-right:{_label_pad};}}
.talk-bubble{{
  display:inline-block;
  max-width:100%;
  padding:10px 12px;
  border-radius:16px;
  border:1px solid rgba(49,51,63,.14);
  box-shadow:0 1px 0 rgba(0,0,0,.02);
  line-height:1.25;
  word-break:break-word;
}}
.talk-bubble.partner{{background:rgba(0,0,0,.02);}}
.talk-bubble.me{{background:rgba(33,150,243,.08);}}
.talk-bubble-sub{{font-size:.86rem;opacity:.70;margin-top:2px;}}
.talk-tts-col{{display:flex;justify-content:flex-end;align-items:center;}}
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
    """Config getter that never crashes when secrets.toml is missing.

    Priority:
      1) st.session_state['cfg'] (if provided)
      2) ENV (Cloud Run recommended)
      3) st.secrets (only if available; wrapped in try)
    """
    cfg = st.session_state.get("cfg") or {}
    v = cfg.get(key)
    if isinstance(v, str) and v.strip():
        return v.strip()

    v_env = os.getenv(key, "")
    if isinstance(v_env, str) and v_env.strip():
        return v_env.strip()

    try:
        s = st.secrets  # may raise if secrets.toml missing
        if hasattr(s, "get"):
            v2 = s.get(key, "")
            return (v2 or "") if isinstance(v2, str) else str(v2)
        return s[key] if key in s else ""
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
# (legacy) 아래 라벨들은 현재 선택 UI(코스→유형→상황)에서는 사용하지 않습니다.
# 예전 버전 호환/참고용으로만 남깁니다. (TAG_LABELS를 덮어쓰지 않도록 이름 변경)
TAG_LABELS_LEGACY = {
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
LEVEL_LABELS_LEGACY = {"n5": "N5", "n4": "N4", "n3": "N3"}

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
# ✅ Daily resume (A안): tag/sub/plan 별로 '오늘 진행' 저장/복구
# - profiles.progress['talk']['daily_state']에 저장 (일 단위)
# - 같은 날/같은 필터(tag|sub|plan)이면 이어서 진행
# - 다음날이면 자동으로 새로 시작
# ============================================================
def _talk_resume_key(tag: str, sub: str, is_pro: bool) -> str:
    return f"{str(tag).strip().lower()}|{str(sub).strip().lower()}|{'pro' if is_pro else 'free'}"

def _get_talk_daily_state_all() -> dict:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        ds = talk_prog.get("daily_state") or {}
        if not isinstance(ds, dict):
            ds = {}
        return ds
    except Exception:
        return {}

def _set_talk_daily_state_all(ds: dict) -> None:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        talk_prog["daily_state"] = ds if isinstance(ds, dict) else {}
        prog["talk"] = talk_prog
        save_progress(prog)
    except Exception:
        pass

def _load_talk_daily_state(resume_key: str) -> dict | None:
    try:
        today = _kst_today_str()
        ds = _get_talk_daily_state_all()
        state = ds.get(resume_key)
        if not isinstance(state, dict):
            return None
        if str(state.get("date") or "") != today:
            return None
        # normalize
        qids = state.get("set_qids")
        idx = state.get("idx")
        if not isinstance(qids, list) or not qids:
            return None
        if idx is None:
            idx = 0
        try:
            idx = int(idx)
        except Exception:
            idx = 0
        return {"date": today, "set_qids": [str(x) for x in qids], "idx": idx}
    except Exception:
        return None

def _save_talk_daily_state(resume_key: str, set_qids: list[str], idx: int) -> None:
    try:
        today = _kst_today_str()
        ds = _get_talk_daily_state_all()
        ds[resume_key] = {
            "date": today,
            "set_qids": [str(x) for x in (set_qids or [])],
            "idx": int(idx),
        }
        _set_talk_daily_state_all(ds)
    except Exception:
        pass

def _clear_talk_daily_state(resume_key: str) -> None:
    try:
        ds = _get_talk_daily_state_all()
        if resume_key in ds:
            ds.pop(resume_key, None)
            _set_talk_daily_state_all(ds)
    except Exception:
        pass

def _restore_daily_progress_if_any(resume_key: str, pool_df: pd.DataFrame) -> bool:
    """session_state에 세트가 없을 때만 호출.
    성공 시 True (복구 완료), 실패 시 False.
    """
    stt = _load_talk_daily_state(resume_key)
    if not stt:
        return False

    # 현재 풀에 존재하는 qid만 유지(필터/CSV 변경 안전)
    pool_qids = set(pool_df["qid"].astype(str).tolist())
    qids = [q for q in (stt.get("set_qids") or []) if q in pool_qids]
    if not qids:
        return False

    idx = int(stt.get("idx") or 0)
    idx = max(0, min(idx, len(qids) - 1))

    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = idx
    st.session_state[f"{NS}_answers"] = {qid: {"selected": None, "ok": None, "spoken": False} for qid in qids}
    st.session_state[f"{NS}_submitted"] = False
    return True

def _persist_daily_progress(resume_key: str, set_qids: list[str], idx: int) -> None:
    # 너무 잦은 저장을 막기 위해 해시로 간단 가드
    try:
        payload = {"k": resume_key, "q": list(set_qids or []), "i": int(idx)}
        h = hashlib.md5(str(payload).encode("utf-8")).hexdigest()
        if st.session_state.get("_talk_daily_state_hash") == h:
            return
        _save_talk_daily_state(resume_key, list(set_qids or []), int(idx))
        st.session_state["_talk_daily_state_hash"] = h
    except Exception:
        pass

# ============================================================
# ============================================================
# ✅ Mastery progress (진도형 누적)
# - profiles.progress['talk']['mastery'][resume_key] 에 저장
# - { qid(str): 'YYYY-MM-DD' } 형태로 누적
# - 기존(list) 저장 형식도 자동 호환
# ============================================================
def _get_talk_mastery_all() -> dict:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        mastery = talk_prog.get("mastery") or {}
        return mastery if isinstance(mastery, dict) else {}
    except Exception:
        return {}

def _set_talk_mastery_all(mastery: dict) -> None:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        talk_prog["mastery"] = mastery if isinstance(mastery, dict) else {}
        prog["talk"] = talk_prog
        save_progress(prog)
    except Exception:
        pass

def _get_mastered_map(resume_key: str) -> dict:
    """returns dict[qid]=date_str"""
    mastery = _get_talk_mastery_all()
    raw = mastery.get(resume_key) or {}
    # legacy list -> map
    if isinstance(raw, list):
        today = _kst_today_str()
        raw = {str(q): today for q in raw}
    if not isinstance(raw, dict):
        raw = {}
    # normalize keys/values
    norm = {}
    for k,v in raw.items():
        if k is None:
            continue
        ks = str(k)
        vs = str(v) if v else ""
        norm[ks] = vs
    return norm

def _mark_mastered(resume_key: str, qid: str) -> None:
    try:
        mastery = _get_talk_mastery_all()
        m = _get_mastered_map(resume_key)
        qid = str(qid)
        if qid in m:
            return
        m[qid] = _kst_today_str()
        mastery[resume_key] = m
        _set_talk_mastery_all(mastery)
    except Exception:
        pass

def _reset_mastery(resume_key: str) -> None:
    try:
        mastery = _get_talk_mastery_all()
        if resume_key in mastery:
            mastery.pop(resume_key, None)
            _set_talk_mastery_all(mastery)
    except Exception:
        pass


# ============================================================
# ✅ Wrong progress (오답 누적: "틀린 것 우선 복습" 용)
# - profiles.progress['talk']['wrong'][resume_key] 에 저장
# - { qid(str): {"last":"YYYY-MM-DD","cnt":int} } 형태
# - legacy(list/set) 형식도 자동 호환
# ============================================================
def _get_talk_wrong_all() -> dict:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        wrong = talk_prog.get("wrong") or {}
        return wrong if isinstance(wrong, dict) else {}
    except Exception:
        return {}

def _set_talk_wrong_all(wrong: dict) -> None:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        talk_prog["wrong"] = wrong if isinstance(wrong, dict) else {}
        prog["talk"] = talk_prog
        save_progress(prog)
    except Exception:
        pass

# ============================================================
# ✅ '오늘의 복습' 세트 고정 저장 (하루 1세트)
# - profiles.progress['talk']['today_review'][resume_key]에 저장
#   { "date": "YYYY-MM-DD", "qids": [...], "done": {qid: "YYYY-MM-DD", ... } }
# ============================================================
def _get_talk_today_review_all() -> dict:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        tr = talk_prog.get("today_review") or {}
        return tr if isinstance(tr, dict) else {}
    except Exception:
        return {}

def _set_talk_today_review_all(tr_all: dict) -> None:
    try:
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        talk_prog["today_review"] = tr_all if isinstance(tr_all, dict) else {}
        prog["talk"] = talk_prog
        save_progress(prog)
    except Exception:
        pass

def _get_today_review_entry(resume_key: str) -> dict:
    all_ = _get_talk_today_review_all()
    ent = all_.get(resume_key) or {}
    return ent if isinstance(ent, dict) else {}

def _set_today_review_entry(resume_key: str, ent: dict) -> None:
    all_ = _get_talk_today_review_all()
    all_[resume_key] = ent if isinstance(ent, dict) else {}
    _set_talk_today_review_all(all_)

def _today_review_is_complete(resume_key: str) -> bool:
    ent = _get_today_review_entry(resume_key)
    qids = ent.get("qids") or []
    done = ent.get("done") or {}
    if not isinstance(qids, list):
        return False
    if not isinstance(done, dict):
        done = {}
    return (len(qids) > 0 and len(done) >= len(qids))

def _today_review_mark_done(resume_key: str, qid: str) -> None:
    try:
        today = _kst_today_str()
        ent = _get_today_review_entry(resume_key)
        if (ent.get("date") or "") != today:
            return
        qids = ent.get("qids") or []
        if qid not in [str(x) for x in qids]:
            return
        done = ent.get("done") or {}
        if not isinstance(done, dict):
            done = {}
        done[str(qid)] = today
        ent["done"] = done
        _set_today_review_entry(resume_key, ent)
    except Exception:
        pass

def _ensure_today_review_set(resume_key: str, pool_ids: list[str], n_target: int) -> list[str]:
    """Return today's fixed set qids; create once per day."""
    today = _kst_today_str()
    ent = _get_today_review_entry(resume_key)

    qids = ent.get("qids") if isinstance(ent, dict) else None
    if isinstance(qids, list) and ent.get("date") == today:
        pool_set = set(map(str, pool_ids))
        kept = [str(q) for q in qids if str(q) in pool_set]
        if len(kept) == len(qids) and len(kept) > 0:
            return kept

    pool_set = set(map(str, pool_ids))
    n_target = max(1, int(n_target or 5))
    chosen: list[str] = []

    # (a) 틀린 것 우선 2개 (cnt desc, last desc)
    wm = _get_wrong_map(resume_key)
    items = []
    for qid, v in (wm or {}).items():
        qid = str(qid)
        if qid not in pool_set:
            continue
        vv = v or {}
        cnt = int(vv.get("cnt") or 0)
        last = str(vv.get("last") or "")
        items.append((qid, cnt, last))
    items.sort(key=lambda x: (-x[1], x[2]), reverse=False)
    for qid, *_ in items[:2]:
        if qid not in chosen:
            chosen.append(qid)

    # (b) 오래된 것 2개 (mastery date asc)
    mm = _get_mastered_map(resume_key)
    old_items = []
    for qid, d in (mm or {}).items():
        qid = str(qid)
        if qid in chosen:
            continue
        if qid not in pool_set:
            continue
        old_items.append((qid, str(d or "")))
    old_items.sort(key=lambda x: x[1])
    for qid, _d in old_items[:2]:
        if qid not in chosen:
            chosen.append(qid)

    # (c) 랜덤으로 나머지 채움 (seeded: user_id+resume_key+today)
    remain = [q for q in map(str, pool_ids) if q in pool_set and q not in chosen]
    seed_src = f"{USER_ID}|{resume_key}|{today}"
    seed = int(hashlib.md5(seed_src.encode('utf-8')).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rng.shuffle(remain)
    need = max(0, min(n_target, len(pool_ids)) - len(chosen))
    chosen.extend(remain[:need])

    ent_new = {"date": today, "qids": chosen, "done": {}}
    _set_today_review_entry(resume_key, ent_new)
    return chosen


def _get_wrong_map(resume_key: str) -> dict:
    raw_all = _get_talk_wrong_all()
    raw = raw_all.get(resume_key) or {}
    # legacy list/set -> dict with cnt=1
    if isinstance(raw, (list, set, tuple)):
        today = _kst_today_str()
        raw = {str(q): {"last": today, "cnt": 1} for q in list(raw)}
    if not isinstance(raw, dict):
        raw = {}
    norm: dict = {}
    for k, v in raw.items():
        if k is None:
            continue
        q = str(k)
        if isinstance(v, dict):
            last = str(v.get("last") or "")
            cnt = int(v.get("cnt") or 1)
        else:
            # v가 날짜 문자열로만 들어온 경우
            last = str(v or "")
            cnt = 1
        norm[q] = {"last": last, "cnt": cnt}
    return norm

def _mark_wrong(resume_key: str, qid: str) -> None:
    try:
        wrong_all = _get_talk_wrong_all()
        m = _get_wrong_map(resume_key)
        qid = str(qid)
        cur = m.get(qid) or {"last": "", "cnt": 0}
        m[qid] = {"last": _kst_today_str(), "cnt": int(cur.get("cnt") or 0) + 1}
        wrong_all[resume_key] = m
        _set_talk_wrong_all(wrong_all)
    except Exception:
        pass

def _clear_wrong(resume_key: str, qid: str) -> None:
    try:
        wrong_all = _get_talk_wrong_all()
        m = _get_wrong_map(resume_key)
        qid = str(qid)
        if qid in m:
            m.pop(qid, None)
            wrong_all[resume_key] = m
            _set_talk_wrong_all(wrong_all)
    except Exception:
        pass

def _reset_wrong(resume_key: str) -> None:
    try:
        wrong_all = _get_talk_wrong_all()
        if resume_key in wrong_all:
            wrong_all.pop(resume_key, None)
            _set_talk_wrong_all(wrong_all)
    except Exception:
        pass

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

def _norm_jp_loose(s: str) -> str:
    """점수 보정용 느슨한 정규화.
    - 작은 문자/장음/촉음 등 STT 흔들림을 완화해 '과도한 감점'을 줄임.
    (최종 점수는 strict+loose 혼합으로 계산)
    """
    s = _norm_jp(s)
    if not s:
        return s
    # 장음 기호 제거(음성 인식에서 자주 빠짐/흔들림)
    s = s.replace("ー", "")
    # 촉음 っ 제거(완전 삭제가 아니라 완화용)
    s = s.replace("っ", "")
    # 작은 ゃゅょぁぃぅぇぉ を 큰 글자로 완화
    small_map = str.maketrans({
        "ゃ":"や","ゅ":"ゆ","ょ":"よ",
        "ぁ":"あ","ぃ":"い","ぅ":"う","ぇ":"え","ぉ":"お",
        "ゎ":"わ",
    })
    s = s.translate(small_map)
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
    """발음 점수(0~100).

    ✅ 유지하는 원칙
    - '완전 다른 문장'은 0점(gate)
    - 순서(워드/글자 순)를 반영한 편집거리 기반

    ✅ 개선점
    - STT가 흔들리기 쉬운 요소(장음/촉음/작은문자 등)로 '과도하게' 깎이지 않도록
      strict 점수 + loose(완화) 점수를 혼합해 최종 점수를 만듦.
    """
    a_strict, b_strict = _norm_jp(a), _norm_jp(b)
    if not a_strict or not b_strict:
        return 0

    a_loose, b_loose = _norm_jp_loose(a), _norm_jp_loose(b)

    # 1) 완전 다른 문장 차단(느슨한 기준으로 gate 적용: '다른데도 억지로 점수' 방지)
    bb = _bigrams(b_loose) if b_loose else set()
    if bb:
        overlap = len(_bigrams(a_loose) & bb) / max(1, len(bb))
        if overlap < gate:
            return 0

    # 2) strict 점수(기본)
    dist_s = _levenshtein(a_strict, b_strict)
    max_len_s = max(len(a_strict), len(b_strict)) or 1
    score_s = 100 * (1 - dist_s / max_len_s)

    # 3) loose 점수(완화)
    if a_loose and b_loose:
        dist_l = _levenshtein(a_loose, b_loose)
        max_len_l = max(len(a_loose), len(b_loose)) or 1
        score_l = 100 * (1 - dist_l / max_len_l)
    else:
        score_l = score_s

    # 4) 혼합(엄격 75% + 완화 25%)
    score = int(round(0.75 * score_s + 0.25 * score_l))

    # 5) 바닥값 정리
    if score < int(floor_to_zero):
        return 0
    return max(0, min(100, score))

def _openai_transcribe_bytes(audio_bytes: bytes, mime: str = "audio/wav") -> str:
    """OpenAI STT.
    ✅ 일본어 강제(language="ja")로 중국어/기타 언어 오인식을 크게 줄입니다.
    ✅ 결과가 가나(ひらがな/カタカナ)가 거의 없으면 1회만 프롬프트를 바꿔 재시도합니다.
    """
    api_key = get_cfg("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.") from e

    client = OpenAI(api_key=api_key)
    file_tuple = ("speech.wav", audio_bytes, mime)

    def _extract_text(out_obj) -> str:
        txt = getattr(out_obj, "text", None)
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
        if isinstance(out_obj, str) and out_obj.strip():
            return out_obj.strip()
        if isinstance(out_obj, dict):
            t = out_obj.get("text")
            if isinstance(t, str) and t.strip():
                return t.strip()
        return ""

    def _kana_ratio(s: str) -> float:
        s = s or ""
        if not s:
            return 0.0
        kana = re.findall(r"[ぁ-ゖァ-ヺー]", s)
        return len(kana) / max(1, len(s))

    # 1) 기본 호출: 일본어 고정
    try:
        out = client.audio.transcriptions.create(
            model=model,
            file=file_tuple,
            language="ja",
        )
        txt = _extract_text(out)
    except Exception as e:
        raise RuntimeError(f"STT 실패: {e}") from e

    # 2) 가나가 거의 없으면(=중국어/영문/잡음으로 튄 가능성) 1회만 재시도
    #    - 일본어로만 써달라고 강하게 유도(필요시 한자도 허용)
    if txt and _kana_ratio(txt) < 0.12:
        try:
            out2 = client.audio.transcriptions.create(
                model=model,
                file=file_tuple,
                language="ja",
                prompt="日本語で書き起こしてください。ひらがな・カタカナを優先し、必要なら漢字も使ってください。",
            )
            txt2 = _extract_text(out2)
            if txt2:
                txt = txt2
        except Exception:
            pass

    return (txt or "").strip()


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


def _mismatch_markup(said: str, correct: str, window: int = 5) -> str:
    """Return small colored snippet (green=match, red=mismatch) without '정답/인식' labels.
    - Shows about 3~5 chars around the first mismatch.
    - Uses hiragana normalization when possible.
    """
    try:
        a0 = (said or "").strip()
        b0 = (correct or "").strip()
        if not a0 or not b0:
            return ""
        # light normalization (hiragana + remove spaces/punct)
        a = _to_hira(a0)
        b = _to_hira(b0)
        a = re.sub(r"\s+", "", a)
        b = re.sub(r"\s+", "", b)
        a = re.sub(r"[\u3000\u3001\u3002,\.！？!\?\-ー〜～\(\)\[\]{}\"'・]", "", a)
        b = re.sub(r"[\u3000\u3001\u3002,\.！？!\?\-ー〜～\(\)\[\]{}\"'・]", "", b)
        if not a or not b:
            return ""

        sm = difflib.SequenceMatcher(a=a, b=b)
        first = None
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                first = (i1, j1)
                break
        if first is None:
            return ""
        ic, ia = first
        # show ~window chars around mismatch (3~5 is good)
        w = max(3, min(int(window or 5), 5))
        pre = 2  # show a little context before mismatch
        cs = max(0, ic - pre)
        as_ = max(0, ia - pre)
        ce = min(len(b), cs + w)
        ae = min(len(a), as_ + w)
        b_win = b[cs:ce]
        a_win = a[as_:ae]

        # align by simple position (good enough for 3~5 chars hint)
        L = max(len(b_win), len(a_win))
        b_pad = b_win.ljust(L, "∅")
        a_pad = a_win.ljust(L, "∅")

        def _color_span(ch: str, ok: bool) -> str:
            ch = ch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            col = "#16a34a" if ok else "#dc2626"  # green / red
            return f"<span style='color:{col}; font-weight:700;'>{ch}</span>"

        top = "".join(_color_span(b_pad[k], b_pad[k] == a_pad[k]) for k in range(L))
        bot = "".join(_color_span(a_pad[k], b_pad[k] == a_pad[k]) for k in range(L))

        return (
            "<div style='margin-top:4px; line-height:1.25; font-size:0.92rem;'>"
            f"<div>🎯 {top}</div>"
            f"<div>🗣️ {bot}</div>"
            "</div>"
        )
    except Exception:
        return ""

    sm = difflib.SequenceMatcher(a=a, b=b)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        exp = b[i1:i2]
        got = a[j1:j2]
        # 너무 길면 잘라서 표시
        if len(exp) > max_chars:
            exp = exp[:max_chars] + "…"
        if len(got) > max_chars:
            got = got[:max_chars] + "…"
        # 공백/빈 문자열 대비
        exp = exp or "∅"
        got = got or "∅"
        return f"차이(앞부분): 정답 {exp} → 인식 {got}"
    return ""


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
# ✅ Filters (코스(stage) → 유형(tag) → 상황(sub))  ✅ (선택 UI만 확장)
# ============================================================

# --- normalize (비교 실패/공백 문제 방지) ---
for _c in ["mode", "tag", "level", "stage"]:
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
if "stage" in DF.columns:
    DF["stage"] = DF["stage"].astype(str).str.strip()

# --- 실전회화만 사용 ---
DF_BASE = DF.copy()
if "mode" in DF_BASE.columns:
    # 기본값: real(실전회화)만. 다른 모드가 없으면 전체 사용.
    _real = DF_BASE[DF_BASE["mode"].astype(str).str.lower() == "real"]
    if not _real.empty:
        DF_BASE = _real.copy()

# --- tag(유형) 라벨: 기본값 + CSV에 없는 태그는 그대로 노출 ---
TAG_LABELS = {
    "aisatsu": "인사",
    "self_introduction": "자기소개",
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

# ✅ sub(상황) 라벨
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
    "meetup": "첫만남",    
    "first_meeting": "자기소개",
    "reason": "공부이유",    
    # (확장 대비) 자주 쓰는 상황 키
    "cafe": "카페",
    "restaurant": "식당",
    "hotel": "호텔",
    "station": "역/지하철",
    "street": "길/거리",
    "dm": "DM/채팅",
    "phone": "전화",
    "basic": "기본",
    "daily": "일상",
    # understand 등에서 쓰는 값들
    "confirm": "확인",
    "mixed": "혼합",
}

def _sub_label(s: str) -> str:
    s = str(s)
    return SUB_LABEL.get(s, s)

# ✅ 코스(stage) 라벨 — "CSV에 있는 코스만" 노출
COURSE_LABELS = {
    "1": "LV1: 말문 트기",
    "2": "LV2: 문장 늘리기",
    "3": "LV3: 대화 확장",
}
def _course_label(stage: str) -> str:
    stage = str(stage).strip()
    if stage in COURSE_LABELS:
        return COURSE_LABELS[stage]
    # 알 수 없는 stage도 CSV에 있으면 노출(확장 대비)
    if stage.isdigit():
        return f"LV{stage}"
    return stage

# ✅ 0) 코스 선택 (stage)
stage_val = ""
if "stage" in DF_BASE.columns:
    _stages = [str(x).strip() for x in DF_BASE["stage"].astype(str).tolist() if str(x).strip()]
    _stages = list(dict.fromkeys(_stages))  # stable unique
    # 숫자는 숫자 정렬, 그 외는 문자열 정렬
    def _stage_sort_key(x: str):
        return (0, int(x)) if x.isdigit() else (1, x)
    _stages = sorted(_stages, key=_stage_sort_key)

    if len(_stages) >= 1:
        stage_val = st.selectbox(
            "코스 선택",
            options=_stages,
            format_func=_course_label,
            key=f"{NS}_stage",
        )

# stage 필터(코스가 있으면 적용)
DF_SEL = DF_BASE.copy()
if stage_val and "stage" in DF_SEL.columns:
    DF_SEL = DF_SEL[DF_SEL["stage"].astype(str) == str(stage_val)].copy()

# ✅ 1) 유형(tag) — DF_SEL에 실제로 존재하는 것만 노출
tag_options_all: list[str] = []
if "tag" in DF_SEL.columns:
    tag_options_all = sorted(set([str(x).strip() for x in DF_SEL["tag"].astype(str).tolist() if str(x).strip()]))

if not tag_options_all:
    st.warning("회화 문제가 없습니다. (CSV의 stage/tag/sub 확인)")
    st.stop()

tag = st.selectbox(
    "유형 선택",
    options=tag_options_all,
    format_func=_tag_label,
    key=f"{NS}_tag",
)

# ✅ 2) 상황(sub) — 선택된 tag 안에서만, 실제 존재하는 것만 노출
sub = "__all__"
has_sub_col = "sub" in DF_SEL.columns

subs_all: list[str] = []
if has_sub_col:
    _df_for_subs = DF_SEL[DF_SEL["tag"].astype(str) == str(tag)].copy()
    subs_all = [x for x in _df_for_subs["sub"].astype(str).tolist() if str(x).strip()]
subs_all = sorted(set([str(x).strip() for x in subs_all if str(x).strip()]))

if len(subs_all) >= 2:
    sub_options = ["__all__"] + subs_all
    sub = st.selectbox(
        "상황 선택",
        options=sub_options,
        format_func=_sub_label,
        key=f"{NS}_sub",
    )
elif len(subs_all) == 1:
    # ✅ 옵션이 1개뿐이어도 '고정 캡션'이 아니라 선택 UI로 그대로 노출 (코스와 동일 UX)
    sub_options = [subs_all[0]]
    sub = st.selectbox(
        "상황 선택",
        options=sub_options,
        format_func=_sub_label,
        key=f"{NS}_sub",
    )
else:
    sub = "__all__"

# 레벨 선택은 사용하지 않음(현재는 N4~N3 혼합 운영)
level = "mix"

# ✅ 풀 구성: 코스(stage) → 유형(tag) → 상황(sub)
pool_df = DF_SEL.copy().reset_index(drop=True)
pool_df = pool_df[pool_df["tag"].astype(str) == str(tag)].copy().reset_index(drop=True)
if has_sub_col and sub != "__all__":
    pool_df = pool_df[pool_df["sub"].astype(str) == str(sub)].copy().reset_index(drop=True)

if pool_df.empty:
    st.warning("해당 조건의 회화 문제가 없습니다. (CSV의 stage/tag/sub 확인)")
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

    colspec = [0.18, 0.72, 0.10] if IS_PRO else [0.12, 0.78, 0.10]
    c1, c2, c3 = st.columns(colspec, vertical_alignment="center")
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
    # ✅ 컴포넌트 높이: 짧을 땐 컴팩트하게, 길면 자동 확장(너무 길면 내부 스크롤)
    # - Streamlit components.html은 "자동 높이"가 불가해서, 텍스트 길이로 높이를 추정합니다.
    # - 너무 긴 문장은 전체 UI가 과도하게 길어지지 않도록, 컴포넌트 높이를 상한으로 두고 내부 스크롤을 켭니다.
    def _lines(s: str, cpl: int) -> int:
        s = (s or "").strip()
        if not s:
            return 0
        return max(1, math.ceil(len(s) / max(8, cpl)))

    # ⚠️ 모바일 기준으로 보수적으로(더 많이 줄바꿈되는 쪽) 계산
    jp_p = _lines(p, 18)
    jp_a = _lines(a, 18)
    kr_p = _lines((partner_kr or ""), 22) if (partner_kr or "").strip() else 0
    kr_a = _lines((answer_kr or ""), 22) if (answer_kr or "").strip() else 0

    # 기본 + 라인 수에 따른 가변
    lines_total = jp_p + jp_a + kr_p + kr_a
    est = 92 + lines_total * 20
    if kr_p:
        est += 6
    if kr_a:
        est += 6

    min_h = 154
    height = int(max(min_h, est))

    # ✅ 상한/내부스크롤 제거: 길면 길수록 iframe이 그대로 늘어나도록
    scroll_mode = False
    txtmax = ""

    html = f"""
<div class="ttspair">
  <div class="row bubble bubble-p">
    <span class="lab">상대(말)</span>
    <div class="txtwrap" style="display:{show}">
      <div class="jp">{p_safe}</div>
      <div class="kr" style="display:{'block' if has_pkr else 'none'}">{pkr_safe}</div>
    </div>
    <button class="btn" id="pbtn-{qid}" aria-label="listen" {'disabled' if disabled or (not p) else ''}>🔊</button>
    
  </div>

  <div class="row bubble bubble-a">
    <span class="lab">내(말)</span>
    <div class="txtwrap" style="display:{show}">
      <div class="jp">{a_safe}</div>
      <div class="kr" style="display:{'block' if has_akr else 'none'}">{akr_safe}</div>
    </div>
    <button class="btn" id="abtn-{qid}" aria-label="listen" {'disabled' if disabled or (not a) else ''}>🔊</button>
    
  </div>
</div>

<style>
  /* ✅ 무지/미니멀 A안 + 말풍선 각각 아웃라인(레이아웃 영향 없음: box-shadow) */
  .ttspair{{display:flex;flex-direction:column;gap:8px;}}
  .ttspair .row{{display:flex;align-items:flex-start;gap:10px;line-height:1.35;}}
  .ttspair .bubble{{border-radius:14px; box-shadow:0 0 0 1px rgba(0,0,0,.12);}}
  .ttspair .bubble-p{{box-shadow:0 0 0 1px rgba(0,0,0,.20);}}
  .ttspair .bubble-a{{box-shadow:0 0 0 1px rgba(0,0,0,.12);}}

  .ttspair .lab{{min-width:52px;font-weight:650;opacity:.82;flex:0 0 auto;padding:10px 0 10px 10px;text-align:right;}}
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

    components.html(html, height=max(200, height + 40), scrolling=False)

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






# ============================================================
# ✅ Filter 변경(tag/sub/plan) 시 세트/진행 초기화
# - 특히 tag="understand"(이해)에서 '다음 문제'가 안 넘어가는 현상 방지
# ============================================================
_cur_fk = f"{tag}|{sub}|{'pro' if IS_PRO else 'free'}"
_prev_fk = st.session_state.get(f"{NS}_filter_key")
if _prev_fk != _cur_fk:
    # ✅ 세트/진행 관련 키만 제거 (tag/sub 선택 값은 유지)
    _keep = {f"{NS}_tag", f"{NS}_sub"}
    _wipe_exact = {
        f"{NS}_set_qids",
        f"{NS}_idx",
        f"{NS}_answers",
        f"{NS}_submitted",
        f"{NS}_selected",
        f"{NS}_opts",
        f"{NS}_spoken",
    }
    _wipe_prefix = (
        f"{NS}_submitted_",
        f"{NS}_selected_",
        f"{NS}_opts_",
        f"{NS}_radio_",
        f"{NS}_speak_done_",
        f"{NS}_reward_ready_",
        f"{NS}_submit_",
        f"{NS}_go_next_",
    )
    for _k in list(st.session_state.keys()):
        if str(_k) in _keep:
            continue
        if str(_k) in _wipe_exact or any(str(_k).startswith(p) for p in _wipe_prefix):
            st.session_state.pop(_k, None)
    st.session_state[f"{NS}_filter_key"] = _cur_fk
pool_answers = pool_df["answer_jp"].astype(str).tolist()


# ============================================================
# ✅ Initialize set (10 qids) + pointer
# - session_state가 초기화되어도 '오늘 진행'은 DB(progress)에 저장된 값으로 복구(A안)
# ============================================================
resume_key = _talk_resume_key(tag, sub, IS_PRO)

# ✅ 학습 모드/복습 모드
mode_key = f"{NS}_mode"
review_opt_key = f"{NS}_review_opt"
if st.session_state.get(mode_key) not in ("learn", "review"):
    st.session_state[mode_key] = "learn"
if st.session_state.get(review_opt_key) not in ("random", "oldest", "mixed", "wrong", "today"):
    st.session_state[review_opt_key] = "random"

def _make_review_qids(pool_df_: pd.DataFrame, resume_key_: str, opt: str, n_: int) -> list[str]:
    # 0) 🎯 오늘의 복습: 틀린 것2 + 오래된 것2 + 랜덤(나머지)
    if opt == "today":
        n_target = max(1, int(n_ or 5))
        pool_ids = pool_df_["qid"].astype(str).tolist()
        return _ensure_today_review_set(resume_key_, pool_ids, n_target)


    # 1) 틀린 것 우선: 오답 누적(wrong)에서 뽑기
    if opt == "wrong":

        wm = _get_wrong_map(resume_key_)
        if not isinstance(wm, dict):
            wm = {}

        # wrong 정책:
        # - 오답이 없으면 빈 리스트(=UI에서 시작 버튼 비활성/안내)
        # - 오답이 많으면: 최근/누적을 기준으로 상위 20개만 추려서 세트 구성
        items = []
        for qid, v in wm.items():
            vv = v or {}
            cnt = int(vv.get("cnt") or 0)
            last = str(vv.get("last") or "")
            items.append((str(qid), cnt, last))

        if not items:
            return []

        # 1) 누적횟수 높은 것 우선, 2) 최근 오답 우선(last desc)
        items.sort(key=lambda t: (t[1], t[2]), reverse=True)

        # 상위 20개만 사용 (너무 많아졌을 때 부담 줄이기)
        items = items[:20]
        selected_ids = [qid for (qid, _, _) in items]

        base = pool_df_[pool_df_["qid"].astype(str).isin(set(selected_ids))].copy()
        if base.empty:
            return []

        # items 순서를 유지(=우선순위 유지)하면서 최대 n_개로 자르기
        order = {qid: i for i, qid in enumerate(selected_ids)}
        base["__worder__"] = base["qid"].astype(str).map(lambda q: order.get(str(q), 10**9))
        base = base.sort_values("__worder__", ascending=True).reset_index(drop=True)
        return base.head(min(n_, len(base)))["qid"].astype(str).tolist()
    # 2) 기존 복습: mastery에서 뽑기(랜덤/오래된/혼합)
    m = _get_mastered_map(resume_key_)
    mastered = list(m.keys())
    if not mastered:
        # mastered가 없으면 그냥 랜덤
        return pool_df_.sample(n=min(n_, len(pool_df_)), replace=False)["qid"].astype(str).tolist()

    base = pool_df_[pool_df_["qid"].astype(str).isin(set(mastered))].copy()
    if base.empty:
        return pool_df_.sample(n=min(n_, len(pool_df_)), replace=False)["qid"].astype(str).tolist()

    if opt == "random":
        return base.sample(n=min(n_, len(base)), replace=False)["qid"].astype(str).tolist()

    # oldest / mixed: 날짜 기준 정렬
    def _dt(q):
        ds = m.get(str(q)) or ""
        return ds or "9999-12-31"
    base["__dt__"] = base["qid"].astype(str).map(_dt)
    base = base.sort_values("__dt__", ascending=True).reset_index(drop=True)

    if opt == "oldest":
        return base.head(min(n_, len(base)))["qid"].astype(str).tolist()

    # mixed
    n_old = max(1, int(round(n_ * 0.7)))
    old_part = base.head(min(n_old, len(base)))["qid"].astype(str).tolist()
    remain = base[~base["qid"].astype(str).isin(set(old_part))]
    n_rand = max(0, n_ - len(old_part))
    rand_part = []
    if n_rand > 0 and not remain.empty:
        rand_part = remain.sample(n=min(n_rand, len(remain)), replace=False)["qid"].astype(str).tolist()
    return old_part + rand_part


if f"{NS}_set_qids" not in st.session_state:
    # 0) 진도형(learn)일 때는 mastered 제외한 남은 문제로만 구성
    mode = st.session_state.get(mode_key) or "learn"
    mastered_map = _get_mastered_map(resume_key)
    mastered_set = set(mastered_map.keys())

    if mode == "learn":
        remain_df = pool_df[~pool_df["qid"].astype(str).isin(mastered_set)].reset_index(drop=True)

        # ✅ 전부 완료 → 완료 화면 + 복습/리셋 버튼
        if remain_df.empty:
            with st.container(border=True):
                st.success("🎉 이 코스는 모두 완료했습니다.")
                # ✅ 방금 마지막 문제에서 넘어온 경우: '다른 유형 선택' 안내를 더 명확히
                if st.session_state.pop(f"{NS}_just_completed", False):
                    st.info("이제 다른 유형을 선택해서 다음 코스로 넘어가 보세요. (원하면 아래에서 복습/초기화도 가능해요.)")
                st.caption("복습을 시작하거나, 진도를 초기화해서 처음부터 다시 학습할 수 있어요.")
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    if st.button("📚 복습(랜덤)", use_container_width=True, key=f"{NS}_review_random"):
                        reset_set()
                        st.session_state[mode_key] = "review"
                        st.session_state[review_opt_key] = "random"
                        _clear_talk_daily_state(resume_key)
                        st.rerun()
                with c2:
                    if st.button("🕒 복습(오래된)", use_container_width=True, key=f"{NS}_review_oldest"):
                        reset_set()
                        st.session_state[mode_key] = "review"
                        st.session_state[review_opt_key] = "oldest"
                        _clear_talk_daily_state(resume_key)
                        st.rerun()
                with c3:
                    if st.button("🔁 진도 초기화", use_container_width=True, key=f"{NS}_reset_mastery"):
                        _reset_mastery(resume_key)
                        _reset_wrong(resume_key)
                        reset_set()
                        _clear_talk_daily_state(resume_key)
                        st.session_state[mode_key] = "learn"
                        st.rerun()
            st.stop()

        # 1) 오늘 진행 복구 시도(남은 풀 기준으로만)
        restored = _restore_daily_progress_if_any(resume_key, remain_df)

        # 2) 복구 실패면 새 세트 생성(남은 풀에서 샘플)
        if not restored:
            n = min((SET_LEN if IS_PRO else FREE_SET_LEN), len(remain_df))
            sample = remain_df.sample(n=n, replace=False).reset_index(drop=True)
            qids = sample["qid"].astype(str).tolist()
            st.session_state[f"{NS}_set_qids"] = qids
            st.session_state[f"{NS}_idx"] = 0
            st.session_state[f"{NS}_answers"] = {qid: {"selected": None, "ok": None, "spoken": False} for qid in qids}
            st.session_state[f"{NS}_submitted"] = False

    else:
        # review mode
        opt = st.session_state.get(review_opt_key) or "random"
        n_base = (SET_LEN if IS_PRO else FREE_SET_LEN)
        # 🎯 오늘의 복습: 기본 5문제(요금제/풀 크기에 맞게 조정)
        if opt == "today":
            n = min(5, n_base, len(pool_df))
        else:
            n = min(n_base, len(pool_df))
        qids = _make_review_qids(pool_df, resume_key, opt, n)
        st.session_state[f"{NS}_set_qids"] = qids
        st.session_state[f"{NS}_idx"] = 0
        st.session_state[f"{NS}_answers"] = {qid: {"selected": None, "ok": None, "spoken": False} for qid in qids}
        st.session_state[f"{NS}_submitted"] = False

    # 3) 최초 진입 시점에도 저장(복구든 신규든)
    try:
        _persist_daily_progress(resume_key, st.session_state.get(f"{NS}_set_qids") or [], int(st.session_state.get(f"{NS}_idx") or 0))
    except Exception:
        pass
qids: list[str] = st.session_state[f"{NS}_set_qids"]
idx: int = int(st.session_state.get(f"{NS}_idx") or 0)
idx = max(0, min(idx, len(qids) - 1))
answers = st.session_state.get(f"{NS}_answers") or {}

# ============================================================
# ✅ Progress header (진도형)
#   - 1) 전체 진도(누적 mastery): 항상 표시
#   - 2) 복습 모드일 때만 '복습 진행' 바 표시 (학습 모드에서는 바 1개로 단순화)
# ============================================================
mode = st.session_state.get(mode_key) or "learn"
review_opt = st.session_state.get(review_opt_key) or "random"

mastered_map = _get_mastered_map(resume_key)
mastered_cnt = len(mastered_map)
total_cnt = int(len(pool_df) if pool_df is not None else 0)
remain_cnt = max(0, total_cnt - mastered_cnt)

# ✅ 세트 진도(현재 세션의 1세트 기준)
# - 선우님 정의: "10문제 = 1세트" (FREE도 동일하게 10문제 = 1세트)
# - 여기서의 '세트 진도'는 전체 풀(pool) 대비가 아니라, '현재 세트(1세트)' 진행률입니다.
#   따라서 항상 0/1 또는 1/1로 표시됩니다.
_set_size = int(SET_LEN)
_set_size = max(1, _set_size)

# 현재 세트에서 몇 문항까지 진행했는지(0~_set_size)
q_in_set = mastered_cnt % _set_size
if mastered_cnt > 0 and (mastered_cnt % _set_size) == 0:
    # 세트 경계(10,20,30...)에 도달했을 때는 '진행 문항'을 _set_size로 표시
    q_in_set = _set_size

set_done = 1 if mastered_cnt >= _set_size else 0
set_total = 1

# 퍼센트는 '현재 세트' 기준
pct = int(round((q_in_set / _set_size) * 100)) if _set_size > 0 else 0

# 참고용(전체 풀 대비) 퍼센트는 유지하되, 오해 없도록 별도 변수로만 둡니다.
pct_q = int(round((mastered_cnt / total_cnt) * 100)) if total_cnt > 0 else 0

is_done = (set_done >= set_total)

_badges = []
if is_done:
    _badges.append('<span class="ha-talk-badge ha-talk-badge-ok">✅ 완료</span>')
if mode == "review":
    _opt_label = {"wrong":"틀린 것", "random":"랜덤", "oldest":"오래된 것", "mixed":"혼합", "today":"오늘의 복습"}        .get(str(review_opt), str(review_opt))
    _badges.append(f'<span class="ha-talk-badge ha-talk-badge-review">🧠 복습 중 · {_opt_label}</span>')
    if str(review_opt) == "today" and _today_review_is_complete(resume_key):
        _badges.append('<span class="ha-talk-badge ha-talk-badge-ok">✅ 오늘의 복습 완료</span>')

st.markdown(
    """
    <style>
      .ha-talk-prog-wrap{display:flex; flex-direction:column; gap:6px; margin:2px 0 6px 0;}
      .ha-talk-prog-top{display:flex; align-items:center; justify-content:space-between; gap:10px;}
      .ha-talk-prog-title{font-weight:900; font-size:0.98rem;}
      .ha-talk-prog-sub{opacity:.75; font-size:.86rem; font-weight:700;}
      .ha-talk-badges{display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;}
      .ha-talk-badge{display:inline-flex; align-items:center; gap:6px; padding:3px 8px; border-radius:999px;
        font-size:.82rem; font-weight:900; border:1px solid rgba(0,0,0,.10); background:rgba(0,0,0,.04);}
      .ha-talk-badge-ok{background:rgba(46, 204, 113, .10);}
      .ha-talk-badge-review{background:rgba(52, 152, 219, .10);}
    </style>
    """,
    unsafe_allow_html=True,
)

p1, p2 = st.columns([1.6, 0.6], vertical_alignment="center")
with p1:
    st.markdown(
        f"""
        <div class='ha-talk-prog-wrap'>
          <div class='ha-talk-prog-top'>
            <div>
              <div class='ha-talk-prog-title'>📈 세트 {set_done}/{set_total} <span class='ha-talk-prog-sub'>(문항 {q_in_set}/{_set_size} · 남은 {max(0, _set_size - q_in_set)}) · {pct}%</span></div>
            </div>
            <div class='ha-talk-badges'>{''.join(_badges)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress((q_in_set / _set_size) if _set_size > 0 else 0.0)

with p2:
    if st.button("🔄 새 세트", use_container_width=True, type="secondary", key=f"{NS}_new_set"):
        reset_set()
        try:
            _clear_talk_daily_state(resume_key)
            _persist_daily_progress(resume_key, [], 0)
        except Exception:
            pass
        # st.rerun()  # Streamlit은 버튼 클릭 시 자동 rerun됩니다.

    # 📚 복습(진도형): 언제든 복습 모드로 전환 가능
    _popover = getattr(st, "popover", None)
    if callable(_popover):
        with st.popover("📚 복습", use_container_width=True):
            # 🎯 오늘의 자동 복습 세트 (틀린 것2 + 오래된 것2 + 랜덤1)
            c_today = st.columns([1,2])
            with c_today[0]:
                _today_done = _today_review_is_complete(resume_key)

                if _today_done:

                    st.info("오늘의 복습은 완료되었습니다. 내일 새 세트가 열립니다.")

                if st.button("🎯 오늘의 복습", use_container_width=True, key=f"{NS}_today_review_btn", disabled=_today_done):
                    reset_set()
                    st.session_state[f"{NS}_mode"] = "review"
                    st.session_state[f"{NS}_review_opt"] = "today"
                    _clear_talk_daily_state(resume_key)
                    st.rerun()
            with c_today[1]:
                st.caption("틀린 것·오래된 것·랜덤을 섞어 5문제로 자동 구성합니다.")

            _opt = st.radio(
                "복습 방식",
                options=["wrong","random","oldest","mixed"],
                format_func=lambda x: {"wrong":"틀린 것", "random":"랜덤", "oldest":"오래된 것", "mixed":"혼합(오래된+랜덤)"}[x],
                key=f"{NS}_review_opt_ui",
            )
            _has_wrong = bool(_get_wrong_map(resume_key))
            if _opt == "wrong" and not _has_wrong:
                st.info("틀린 문제가 아직 없어요. 먼저 학습 모드에서 몇 개 틀려보시면, 여기에서 오답만 모아서 복습할 수 있어요.")
            c_a, c_b = st.columns([1, 1])
            with c_a:
                if st.button("복습 시작", use_container_width=True, key=f"{NS}_review_start", disabled=(_opt=="wrong" and not _has_wrong)):
                    reset_set()
                    st.session_state[f"{NS}_mode"] = "review"
                    st.session_state[f"{NS}_review_opt"] = _opt
                    _clear_talk_daily_state(resume_key)
                    st.rerun()
            with c_b:
                if st.button("학습 모드", use_container_width=True, key=f"{NS}_learn_mode"):
                    reset_set()
                    st.session_state[f"{NS}_mode"] = "learn"
                    _clear_talk_daily_state(resume_key)
                    st.rerun()
    else:
        with st.expander("📚 복습", expanded=False):
            c_today = st.columns([1,2])
            with c_today[0]:
                _today_done = _today_review_is_complete(resume_key)

                if _today_done:

                    st.info("오늘의 복습은 완료되었습니다. 내일 새 세트가 열립니다.")

                if st.button("🎯 오늘의 복습", use_container_width=True, key=f"{NS}_today_review_btn2", disabled=_today_done):
                    reset_set()
                    st.session_state[f"{NS}_mode"] = "review"
                    st.session_state[f"{NS}_review_opt"] = "today"
                    _clear_talk_daily_state(resume_key)
                    st.rerun()
            with c_today[1]:
                st.caption("틀린 것·오래된 것·랜덤을 섞어 5문제로 자동 구성합니다.")

            _opt = st.radio(
                "복습 방식",
                options=["wrong","random","oldest","mixed"],
                format_func=lambda x: {"wrong":"틀린 것", "random":"랜덤", "oldest":"오래된 것", "mixed":"혼합(오래된+랜덤)"}[x],
                key=f"{NS}_review_opt_ui",
            )
            if st.button("복습 시작", use_container_width=True, key=f"{NS}_review_start", disabled=(_opt=="wrong" and not _has_wrong)):
                st.session_state[f"{NS}_mode"] = "review"
                st.session_state[f"{NS}_review_opt"] = _opt
                reset_set()
                _clear_talk_daily_state(resume_key)
                st.rerun()
            if st.button("학습 모드", use_container_width=True, key=f"{NS}_learn_mode"):
                reset_set()
                st.session_state[f"{NS}_mode"] = "learn"
                _clear_talk_daily_state(resume_key)
                st.rerun()


# ✅ 세트 진행(학습/복습)
if mode == "review":
    _rprog = (idx + 1) / max(1, len(qids))
    st.progress(_rprog)
    st.caption(f"복습 진행: {idx+1}/{len(qids)}")
else:
    st.caption(f"문항 진행: {idx+1}/{len(qids)}")


# ============================================================
# ✅ Review completion (avoid wrapping back to 1st)
# ============================================================
if mode == "review" and (idx is None or idx >= len(qids)):
    with st.container(border=True):
        st.success("✅ 복습을 완료했습니다.")
        st.caption("학습 모드로 돌아가거나, 다른 방식으로 복습을 이어갈 수 있어요.")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("학습 모드로", use_container_width=True, key=f"{NS}_review_done_to_learn"):
                reset_set()
                st.session_state[mode_key] = "learn"
                _clear_talk_daily_state(resume_key)
                st.rerun()
        with c2:
            if st.button("복습 다시", use_container_width=True, key=f"{NS}_review_done_restart"):
                reset_set()
                st.session_state[mode_key] = "review"
                st.session_state[review_opt_key] = review_opt
                _clear_talk_daily_state(resume_key)
                st.rerun()
    st.stop()

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

    # ✅ 마지막 문제까지 풀고 '다음'을 누르면 1번으로 돌아가지 않고
    #    완료 화면(다른 유형 선택/복습/초기화)로 자연스럽게 유도합니다.
    if nxt >= len(qids):
        # 다음 rerun에서 remain_df 체크가 돌도록 세트 키를 제거
        st.session_state[f"{NS}_just_completed"] = True

        for _k in (f"{NS}_set_qids", f"{NS}_idx", f"{NS}_answers", f"{NS}_qid"):
            st.session_state.pop(_k, None)

        # 오늘 진행도 더 이상 이어붙지 않게 정리(완료 상태는 mastery에 남음)
        try:
            _clear_talk_daily_state(resume_key)
            _persist_daily_progress(resume_key, [], 0)
        except Exception:
            pass

        # 현재 문제 위젯 상태도 정리
        st.session_state[submitted_key] = False
        st.session_state.pop(sel_key, None)
        st.session_state.pop(f"{NS}_radio_{qid}", None)
        st.session_state.pop(f"{NS}_speak_done_{qid}", None)
        st.session_state.pop(f"{NS}_reward_ready_{qid}", None)
        st.rerun()

    # 일반적인 다음 문제 이동
    st.session_state[f"{NS}_idx"] = nxt
    try:
        _persist_daily_progress(resume_key, qids, nxt)
    except Exception:
        pass

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
        def _render_free_listen_block_9c1b():
            rem = _free_tts_remaining()
            if rem > 0:
                if st.button(f"🔊 발음 듣기 (무료 {FREE_TTS_QUOTA-rem+1}/{FREE_TTS_QUOTA})", key=f"{qid}_free_tts_q", use_container_width=True):
                    _use_free_tts_once()
                    _au = resolve_audio_url(row.get('partner_mp3','') or row.get('partner_audio','') or row.get('partner_audio_url','') or '')
                    components.html(f"""<script>
    (function(){{
      try{{
        const audioUrl = {_au!r};
        const synth = window.speechSynthesis;
        function pickJaVoice(){{
          try {{
            const voices = (synth && synth.getVoices) ? (synth.getVoices() || []) : [];
            const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
            if (!ja.length) return null;
            return ja.find(v => /google/i.test(v.name||""))
                || ja.find(v => /日本|japanese/i.test(v.name||""))
                || ja[0] || null;
          }} catch(e) {{ return null; }}
        }}
        function speak(){{
          try {{
            if (!synth) return;
            const u = new SpeechSynthesisUtterance({(row.get('partner_jp','') or '').replace(chr(10),' ')!r});
            u.lang = "ja-JP";
            const v = pickJaVoice();
            if (v) u.voice = v;
            synth.cancel();
            synth.speak(u);
          }} catch(e) {{}}
        }}
        if (audioUrl) {{
          try {{
            const a = new Audio(audioUrl);
            a.play().catch(()=>speak());
          }} catch(e) {{
            speak();
          }}
        }} else {{
          speak();
        }}
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
                _render_upgrade_cta("✨ PRO로 업그레이드", "PRO에서는 발음듣기가 무제한입니다.")
        if hasattr(st, 'fragment'):
            _render_free_listen_block_9c1b = st.fragment(_render_free_listen_block_9c1b)
        _render_free_listen_block_9c1b()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
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

        def _render_submit_block_f0c2():
            # ✅ radio는 선택 시 즉시 rerun되므로, 버튼 활성화가 즉시 반영됨
            can_submit = bool(picked) and (not submitted)
            submitted_now = st.button(
                "정답 제출",
                use_container_width=True,
                disabled=not can_submit,
                key=f"{NS}_submit_{qid}",
            )

            # ✅ 제출 시에만 선택/제출 상태를 확정 (session_state만 업데이트)
            # (함수 내부에서 submitted/selected를 대입하면 지역변수 처리로 UnboundLocalError가 날 수 있어요.)
            if submitted_now and (not submitted):
                st.session_state[sel_key] = picked
                st.session_state[submitted_key] = True
                # ✅ fragment 내부 클릭일 때도 '전체 화면'이 다시 그려지도록 강제 rerun
                st.rerun()

        # ✅ 렌더(버튼 표시)
        if hasattr(st, 'fragment'):
            _render_submit_block_f0c2_ = st.fragment(_render_submit_block_f0c2)
            _render_submit_block_f0c2_()
        else:
            _render_submit_block_f0c2()


    # ============================================================
    # ✅ After submit
    # ============================================================
    if submitted:
        correct = str(row.get("answer_jp", "")).strip()
        ok = (selected == correct)

        # ✅ 제출 직후 SFX(정답/오답) — 문제(qid)당 1회만
        try:
            _sfx_guard = f"talk_sfx_{qid}"
            if not st.session_state.get(_sfx_guard, False):
                if hasattr(core, "play_sfx_once"):
                    core.play_sfx_once(_sfx_guard, "correct" if ok else "wrong")
                elif hasattr(core, "play_sfx"):
                    core.play_sfx("correct" if ok else "wrong")
                st.session_state[_sfx_guard] = True
        except Exception:
            pass


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
        # ✅ 진도형 누적: 정답이면 mastered로 기록(로그인/재접속에도 유지)
        if ok:
            try:
                _mark_mastered(resume_key, str(qid))
                # 정답으로 맞춘 건 오답 목록에서 제거(있다면)
                _clear_wrong(resume_key, str(qid))
            except Exception:
                pass
        else:
            # 오답 누적(틀린 것 우선 복습용)
            try:
                _mark_wrong(resume_key, str(qid))
            except Exception:
                pass

    
        # ✅ 오늘의 복습(하루 1세트 고정): 시도한 문제를 done으로 기록
        try:
            if st.session_state.get(mode_key) == "review" and st.session_state.get(review_opt_key) == "today":
                _today_review_mark_done(resume_key, str(qid))
        except Exception:
            pass

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
        try:
            _persist_daily_progress(resume_key, qids, idx)
        except Exception:
            pass

        st.markdown("---")
        st.subheader("결과")

        if ok:
            st.success("정답 ✅")
        else:
            st.error("오답 ❌")

        # ✅ 오늘의 회화 레벨 게이지(일일) + 미션 카드(포인트)
        _goal = 7
        _done = _get_today_speech_done()
        _ratio = min(1.0, (_done / _goal) if _goal else 0.0)
        # ✅ Mission card CSS는 rerun마다 다시 주입해야 레이아웃이 유지됩니다.
        st.markdown("""
    <style>
    .talk-mission-wrap{
      display:flex; align-items:center; justify-content:space-between;
      gap:12px; padding:12px 14px; border-radius:14px;
      border:1px solid rgba(0,0,0,.10);
      background:rgba(255, 244, 220, .55);
      margin:10px 0 12px 0;
    }
    .talk-mission-left{min-width:0;}
    .talk-mission-badge{
      display:inline-flex; align-items:center;
      padding:3px 8px; border-radius:999px;
      font-size:.82rem; font-weight:800;
      background:rgba(0,0,0,.06);
    }
    .talk-mission-text{
      margin-top:6px; font-size:0.98rem; font-weight:700;
      line-height:1.25;
    }
    .talk-mission-right{
      display:flex; flex-direction:column; align-items:flex-end;
      flex:0 0 auto;
    }
    .talk-count-label{font-size:.82rem; opacity:.85; font-weight:700;}
    .talk-count-num{font-size:1.9rem; font-weight:900; line-height:1;}
    .talk-count-unit{font-size:.82rem; opacity:.85; font-weight:700; margin-top:2px;}
    </style>
    """, unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class=\"talk-mission-wrap\">
              <div class=\"talk-mission-left\">
                <div class=\"talk-mission-badge\">🎯 오늘 미션</div>
                <div class=\"talk-mission-text\">오늘은 입을 <b>{_goal}번</b>만 열어봅시다.</div>
              </div>
              <div class=\"talk-mission-right\">
                <div class=\"talk-count-label\">🗣 오늘 말한 문장</div>
                <div class=\"talk-count-num\">{_done}</div>
                <div class=\"talk-count-unit\">문장</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(_ratio)

        # 상대/정답 스크립트 + 해설(제출 후에만)
        with st.container(border=True):
            hotena_title("assets/hotena_talk/icons_title/icon_pronounce_title.png", "대화/해설")


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

        ## FREE: 제출 후에도 발음 듣기 하루 3회만 허용 (상대/내 각각 버튼 제공)
        if not IS_PRO:
            def _render_free_after_tts_4b2c():
                rem2 = _free_tts_remaining()
                c1, c2 = st.columns(2)
                with c1:
                    if rem2 > 0 and st.button("🔊 상대 발음 듣기", key=f"{qid}_free_tts_partner_after", use_container_width=True):
                        _use_free_tts_once()
                        p_audio_url = resolve_audio_url((row.get("partner_mp3","") or row.get("partner_audio","") or row.get("partner_audio_url","") or ""))
                        p_text = (row.get("partner_jp","") or "").replace(chr(10)," ")
                        components.html(f"""<script>
(function(){{
  const audioUrl = {p_audio_url!r};
  const text = {p_text!r};
  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const voices = synth ? (synth.getVoices() || []) : [];
      const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if (!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||""))
          || ja.find(v => /日本|japanese/i.test(v.name||""))
          || ja[0] || null;
    }} catch(e) {{ return null; }}
  }}
  function speak(){{
    try {{
      const synth = window.speechSynthesis;
      if (!synth) return;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      synth.speak(u);
    }} catch(e) {{}}
  }}
  if (audioUrl){{
    try {{
      const a = new Audio(audioUrl);
      a.play().catch(()=>speak());
    }} catch(e) {{
      speak();
    }}
  }} else {{
    speak();
  }}
}})();
</script>""", height=0)
                    elif rem2 <= 0:
                        st.button("🔒 상대 발음 듣기 (PRO)", key=f"{qid}_free_tts_partner_after_lock", disabled=True, use_container_width=True)

                with c2:
                    rem3 = _free_tts_remaining()
                    if rem3 > 0 and st.button("🔊 내 발음 듣기", key=f"{qid}_free_tts_answer_after", use_container_width=True):
                        _use_free_tts_once()
                        a_audio_url = resolve_audio_url((row.get("answer_mp3","") or row.get("answer_audio","") or row.get("answer_audio_url","") or ""))
                        a_text = (row.get("answer_jp","") or "").replace(chr(10)," ")
                        components.html(f"""<script>
(function(){{
  const audioUrl = {a_audio_url!r};
  const text = {a_text!r};
  function pickJaVoice(){{
    try {{
      const synth = window.speechSynthesis;
      const voices = synth ? (synth.getVoices() || []) : [];
      const ja = voices.filter(v => String(v.lang||"").toLowerCase().startsWith("ja"));
      if (!ja.length) return null;
      return ja.find(v => /google/i.test(v.name||""))
          || ja.find(v => /日本|japanese/i.test(v.name||""))
          || ja[0] || null;
    }} catch(e) {{ return null; }}
  }}
  function speak(){{
    try {{
      const synth = window.speechSynthesis;
      if (!synth) return;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      synth.speak(u);
    }} catch(e) {{}}
  }}
  if (audioUrl){{
    try {{
      const a = new Audio(audioUrl);
      a.play().catch(()=>speak());
    }} catch(e) {{
      speak();
    }}
  }} else {{
    speak();
  }}
}})();
</script>""", height=0)
                    elif rem3 <= 0:
                        st.button("🔒 내 발음 듣기 (PRO)", key=f"{qid}_free_tts_answer_after_lock", disabled=True, use_container_width=True)

            # ✅ FREE 버튼 클릭 시 페이지 전체 rerun(번쩍임)을 줄이기 위해 fragment로 격리
            if hasattr(st, 'fragment'):
                _render_free_after_tts_4b2c = st.fragment(_render_free_after_tts_4b2c)
            _render_free_after_tts_4b2c()

            # ✅ FREE: '대화/해설' 영역 발음듣기 소진 시에도 PRO 업그레이드 안내(발음체크와 동일)
            if (not IS_PRO) and submitted and (_free_tts_remaining() <= 0):
                st.markdown(
                    '<div style="margin-top:6px;display:flex;align-items:center;gap:8px;">'
                    '<span style="font-size:12px;background:#FFD54F;color:#000;padding:2px 6px;border-radius:8px;font-weight:800;">PRO</span>'
                    '<span style="font-size:0.92rem;opacity:0.85;">발음 듣기는 PRO 전용 (무료 3회 소진)</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                _render_upgrade_cta("✨ PRO로 업그레이드", "PRO에서는 발음듣기가 무제한입니다.")
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
            _frag = getattr(st, 'fragment', None)
            def _render_smartcoach_block():
                coach_open_key = f"talk_ai_open_{qid}"
                coach_answer_key = f"talk_ai_answer_{qid}"
                if coach_open_key not in st.session_state:
                    st.session_state[coach_open_key] = False
            
                with st.expander(
                    "🤖 원포인트 일본어가 어려우면 하테나쌤에게 물어보세요",
                    expanded=bool(st.session_state.get(coach_open_key, False)),
                ):
                    hotena_title("assets/hotena_talk/icons_title/icon_coach_title.png", "하테나쌤 스마트 코치")
                    q_default = st.session_state.get("talk_ai_last_q") or ""
                    coach_slot = st.empty()
            
                    # ✅ 입력 중에는 rerun이 자주 나지 않도록 form으로 감쌉니다.
                    with st.form(key=f"talk_ai_form_{qid}", clear_on_submit=False):
                        user_q = st.text_input(
                            "질문",
                            value=str(q_default),
                            key=f"talk_ai_q_{qid}",
                            placeholder="예) 더 자연스러운 표현도 있어요?",
                            label_visibility="collapsed",
                        )
                        st.caption("회화 표현·뉘앙스·자연스러움 위주 질문에 최적화되어 있어요.")
                        ask = st.form_submit_button("AI 코칭 받기 시작", use_container_width=True)
            
                    # ✅ 요청 직후에는 expander를 '열린 상태'로 고정
                    if ask:
                        st.session_state[coach_open_key] = True
            
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
                                use_container_width=True,
                            )
                        else:
                            # 회화 질문일 때만 AI 호출
                            def _is_ctx_relevant(q: str, row_: dict) -> bool:
                                q = (q or "").strip().lower()
                                if not q:
                                    return False
                                key_hits = ["정답", "오답", "왜", "뉘앙스", "자연", "어색", "차이", "문법", "표현", "대안", "바꿔", "맞아", "틀려"]
                                if any(k in q for k in key_hits):
                                    return True
                                if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", q):
                                    return True
                                p_ = str(row_.get("partner_jp", "") or "").strip().lower()
                                a_ = str(row_.get("answer_jp", "") or "").strip().lower()
                                for ref in (p_, a_):
                                    if ref and ref[:8] in q:
                                        return True
                                return False
            
                            use_ctx = _is_ctx_relevant(question, row)
                            ctx_parts = [] if use_ctx else None
                            s = str(row.get("situation_kr", "") or "").strip()
                            p_ = str(row.get("partner_jp", "") or "").strip()
                            a_ = str(row.get("answer_jp", "") or "").strip()
                            me_ = str(selected or "").strip()
                            if ctx_parts is not None and s:
                                ctx_parts.append(f"현재상황: {s}")
                            if ctx_parts is not None and p_:
                                ctx_parts.append(f"상대발화: {p_}")
                            if ctx_parts is not None and a_:
                                ctx_parts.append(f"정답표현: {a_}")
                            if ctx_parts is not None and me_:
                                ctx_parts.append(f"내선택: {me_}")
                            if ctx_parts is not None:
                                ctx_parts.append(f"정오답: {'정답' if ok else '오답'}")
                            ctx = "\n".join(ctx_parts) if isinstance(ctx_parts, list) else ""
            
                            # ✅ talk(44) 느낌: expander 안에서 같은 자리에서 로딩→답변 갱신
                            # (로딩 표시는 상단 1회만 표시)
                            coach_slot.info("답변 중…")
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
                            st.session_state[coach_answer_key] = ans
                            coach_slot.info(ans)
            
                    # ✅ rerun 이후에도 마지막 답은 expander 안에서 유지
                    if (not ask) and st.session_state.get(coach_answer_key):
                        coach_slot.info(st.session_state[coach_answer_key])
            
            if IS_PRO:
                if _frag:
                    @_frag
                    def _render_smartcoach_frag():
                        _render_smartcoach_block()
                    _render_smartcoach_frag()
                else:
                    _render_smartcoach_block()
            else:
                st.info("🤖 AI 스마트코치는 PRO 플랜에서만 이용 가능합니다.")# ============================================================
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

def _render_pron_a3cfa850():
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
                _render_upgrade_cta("✨ PRO로 발음듣기 무제한 사용하기", "무료 3회를 모두 사용했어요. PRO에서는 발음듣기가 무제한입니다.")
        # ✅ 말하기 녹음(선택)
        # - PRO: 녹음 가능
        # - FREE: PRO 안내 카드 노출
        # ✅ 녹음 위젯이 간헐적으로 꼬이는 환경(모바일/브라우저) 대비: 문제(qid)마다 key nonce를 바꿔 새 위젯으로 렌더
        if st.session_state.get("_talk_audio_nonce_qid") != str(qid):
            st.session_state["_talk_audio_nonce"] = int(st.session_state.get("_talk_audio_nonce") or 0) + 1
            st.session_state["_talk_audio_nonce_qid"] = str(qid)
        _audio_nonce = int(st.session_state.get("_talk_audio_nonce") or 0)
        _audio = None
        if IS_PRO:
            _audio = st.audio_input("🎤 (선택) 내 발음을 녹음하고 들어보세요", key=f"{qid}_record_{_audio_nonce}")
            if _audio is not None:
                # 🔧 audio_input 반환 객체를 그대로 st.audio에 넘기면(스트림 포인터/재렌더링 영향)
                # 일부 환경에서 'An error has occurred, please try again.'가 뜰 수 있어
                # bytes로 복사해서 재생/후속 처리에 재사용합니다.
                _rec_bytes_key = f"{qid}__rec_bytes"
                try:
                    if hasattr(_audio, "getvalue"):
                        _ab = _audio.getvalue()
                    else:
                        _ab = _audio.read()
                        if hasattr(_audio, "seek"):
                            _audio.seek(0)  # ✅ audio_input 내부 미리보기/파형용으로 되감기
                except Exception:
                    _ab = None
    
                if _ab:
                    st.session_state[_rec_bytes_key] = _ab
                    _rec_mime_key = f"{qid}__rec_mime"
                    _fmt = getattr(_audio, "type", None) or "audio/wav"
                    st.session_state[_rec_mime_key] = _fmt
        else:
            remr = _free_record_remaining()
            if remr > 0:
                st.caption(f"FREE 녹음 남은 횟수: {remr}/{FREE_RECORD_QUOTA} (오늘 기준)")
                _audio = st.audio_input("🎤 (무료) 내 발음을 녹음하고 들어보세요", key=f"{qid}_record_free_{_audio_nonce}")
                if _audio is not None:
                    _use_free_record_once()
                    # 🔧 FREE도 PRO와 동일하게 bytes 복사 + format 자동으로 통일
                    _rec_bytes_key = f"{qid}__rec_bytes"
                    try:
                        if hasattr(_audio, "getvalue"):
                            _ab = _audio.getvalue()
                        else:
                            _ab = _audio.read()
                            if hasattr(_audio, "seek"):
                                _audio.seek(0)
                    except Exception:
                        _ab = None

                    if _ab:
                        st.session_state[_rec_bytes_key] = _ab
                        _rec_mime_key = f"{qid}__rec_mime"
                        _fmt = getattr(_audio, "type", None) or "audio/wav"
                        st.session_state[_rec_mime_key] = _fmt
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

        # ✅ (중요) 정답 제출 직후에는 '녹음 전' 상태가 기본입니다.
        # - Streamlit rerun/캐시로 이전 결과가 남아 보이는 현상을 막기 위해,
        #   이 문제(qid)의 발음 점수/인식결과는 '처음 진입' 시 1회 초기화합니다.
        _entered_key = f"talk_pron_entered_{qid}"
        if not st.session_state.get(_entered_key, False):
            st.session_state[_entered_key] = True
            st.session_state.pop(text_key, None)
            st.session_state.pop(score_key, None)
            st.session_state.pop(err_key, None)
            st.session_state.pop(f"talk_pron_lasthash_{qid}", None)

        audio_obj = locals().get("_audio", None)
        # bytes를 session_state에 저장해두었다면(BytesIO로 감싸서) 이후 STT/채점에서 안정적으로 사용
        _rec_bytes_key = f"{qid}__rec_bytes"
        _ab = st.session_state.get(_rec_bytes_key)
        if _ab:
            try:
                audio_obj = io.BytesIO(_ab)
            except Exception:
                pass

        # ✅ 녹음 '전'에는 결과/점수 표시 및 자동 계산을 절대 하지 않기
        _peek = b""
        if audio_obj is not None:
            try:
                if hasattr(audio_obj, "getvalue"):
                    _peek = audio_obj.getvalue() or b""
                elif hasattr(audio_obj, "read"):
                    _pos = audio_obj.tell() if hasattr(audio_obj, "tell") else None
                    _peek = audio_obj.read() or b""
                    if _pos is not None and hasattr(audio_obj, "seek"):
                        audio_obj.seek(_pos)
            except Exception:
                _peek = b""

        has_audio = bool(_peek)
        if not has_audio:
            # 화면에는 '녹음기'만 보이고, 결과/점수는 숨깁니다.
            st.session_state.pop(text_key, None)
            st.session_state.pop(score_key, None)
            st.session_state.pop(err_key, None)


        # ✅ (중요) 녹음을 아직 하지 않았는데 이전 결과(점수/인식)가 남아 보이는 경우가 있어
        # 제출 직후(또는 위젯이 아직 비어있는 상태)에는 결과를 초기화합니다.
        _last_hash_key = f"talk_pron_lasthash_{qid}"
        if not has_audio:
            st.session_state.pop(text_key, None)
            st.session_state.pop(score_key, None)
            st.session_state.pop(err_key, None)
            st.session_state.pop(_last_hash_key, None)

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

            # 오디오가 아직 실제로 녹음되지 않은 상태(빈 바이트)면 이전 결과를 보여주지 않음
            if not _h:
                st.session_state.pop(text_key, None)
                st.session_state.pop(score_key, None)
                st.session_state.pop(err_key, None)
                st.session_state.pop(_last_hash_key, None)

            # ✅ (UX) 녹음 정지 직후: Streamlit은 위젯 이벤트(정지/업로드)마다 '전체 rerun'이 기본 동작입니다.
            #    여기서 st.rerun()을 추가로 호출하면(=2회 연속 rerun) 일부 브라우저에서 audio_input 미리보기가 깨지며
            #    'An error has occurred, please try again.'가 뜨는 경우가 있어요.
            #    그래서: '정지로 발생한 1회 rerun' 안에서 바로 STT/점수 계산을 끝내고, 추가 rerun은 하지 않습니다.

            if _h and st.session_state.get(_last_hash_key) != _h:
                st.session_state[_last_hash_key] = _h
                st.session_state.pop(err_key, None)
                with st.spinner("말하기 점수 계산 중."):
                    try:
                        _txt = _openai_transcribe_bytes(_b, mime=_mime)
                        st.session_state[text_key] = _txt
                        st.session_state[score_key] = _similarity_score(_txt, str(row.get("answer_jp", "")))
                        # ✅ 발음 100점 SFX (qid+오디오 해시당 1회만)
                        try:
                            _pron_score = st.session_state.get(score_key)
                            if isinstance(_pron_score, (int, float)) and _pron_score >= 100:
                                _psfx_guard = f"talk_pron_sfx_{qid}_{_h}"
                                if not st.session_state.get(_psfx_guard, False):
                                    if hasattr(core, "play_sfx_once"):
                                        core.play_sfx_once(_psfx_guard, "correct")
                                    elif hasattr(core, "play_sfx"):
                                        core.play_sfx("correct")
                                    st.session_state[_psfx_guard] = True
                        except Exception:
                            pass
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
                _rec_bytes_key = f"{qid}__rec_bytes"
                _rec_mime_key = f"{qid}__rec_mime"
                b = st.session_state.get(_rec_bytes_key) or b""
                mime = st.session_state.get(_rec_mime_key) or "audio/wav"
                if (not b) and (audio_obj is not None):
                    mime = getattr(audio_obj, "type", None) or mime
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
            _scv = int(st.session_state.get(score_key) or 0)
            st.metric("점수", _scv)

            # ✅ 어디가 틀렸는지(짧게 3~5글자) 색으로 표시 — 점수가 100이 아닐 때만
            _said_txt = str(st.session_state.get(text_key) or "").strip()
            _ans_txt = str(row.get("answer_jp", "") or "").strip()
            if _said_txt and _ans_txt and _scv < 100:
                _mk = _mismatch_markup(_said_txt, _ans_txt, window=5)
                if _mk:
                    st.markdown(_mk, unsafe_allow_html=True)

        st.caption("정답을 보고 2~3번 따라 말해 보세요. 녹음이 끝나면 점수가 자동으로 계산됩니다.")
        reward_key = f"{NS}_reward_ready_{qid}"
        if st.button("✅ 다 했어요 (보상 받기)", use_container_width=True, key=f"{NS}_next_after"):
            # ✅ 규칙:
            # - '녹음'을 했고, 점수가 100점일 때만
            # - 그리고 "보기 선택"이 정답(ok=True)일 때만 보상을 지급합니다.
            _sc = int(st.session_state.get(score_key) or 0) if st.session_state.get(score_key) is not None else 0
            _said = str(st.session_state.get(text_key) or "").strip()

            _ok = None
            try:
                _am = st.session_state.get(f"{NS}_answers") or {}
                _ok = (_am.get(qid) or {}).get("ok")
            except Exception:
                _ok = None

            if (_ok is True) and _said and _sc == 100:
                # ✅ 1단계: 보상만 보여주고, 다음 이동은 사용자가 명확히 누르도록 분리
                st.session_state[reward_key] = True
                _inc_today_speech_done(1)
            else:
                # ✅ 발음 100점이라도, 문제 선택이 오답이면 보상은 지급하지 않음(정오답 판정 분리)
                if (_ok is False) and _said and _sc == 100:
                    st.warning("발음은 100점이지만, 문제 선택이 오답이라 보상은 지급되지 않습니다. (정답/발음은 별개로 관리돼요.)")
                else:
                    st.warning("보상은 '녹음 + 100점'일 때만 받을 수 있어요. 지금 바로 녹음하고 100점을 만들어 보세요.")

        # ✅ 보상 조건을 못 맞춰도, 다음 문제로는 넘어갈 수 있게(보상만 미지급)
        if st.button("➡️ 다음 문제로 (보상 없이)", use_container_width=True, key=f"{NS}_go_next_no_reward_{qid}"):
            _go_next_question()


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

# ✅ Pronunciation block isolation: use st.fragment if available to avoid whole-page flicker on record/stop
if hasattr(st, 'fragment'):
    _render_pron_a3cfa850 = st.fragment(_render_pron_a3cfa850)

if submitted:
    _render_pron_a3cfa850()
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
