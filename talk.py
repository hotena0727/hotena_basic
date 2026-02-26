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
            st.markdown('<div style="font-size:1.25rem; font-weight:700;">📊 말하기 점수</div>', unsafe_allow_html=True)
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
