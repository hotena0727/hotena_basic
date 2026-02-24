# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations
# BUILD_STAMP_TALK: talk-newset-in-progress-v1 2026-02-22 KST (+09:00)

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib

import pandas as pd
import streamlit as st



# ============================================================
# ✅ wrong_notes debug helper
# ============================================================
_WN_DEBUG = bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))
def _wn_warn(msg: str):
    if _WN_DEBUG:
        try:
            st.warning(msg)
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

# ✅ MP3 URL이 없을 때 브라우저 TTS로 대체할지 여부
USE_TTS_FALLBACK = True  # mp3만 쓰려면 False


# ============================================================
# ✅ Settings
# ============================================================
NS = "talk"
SET_LEN = 10

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

st.title("일본어회화")
st.caption("1문제씩: 상황 → 상대 발화(🔊/PRO) → 보기 선택 → 제출 → 정답/설명 → (선택)말하기 완료 체크")

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


def get_sb():
    sb = st.session_state.get("sb")
    if sb is not None:
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
    url = get_cfg("SUPABASE_URL")
    key = get_cfg("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Supabase 설정이 없습니다. (SUPABASE_URL / SUPABASE_ANON_KEY)")
        st.stop()
    sb = create_client(url, key)
    st.session_state["sb"] = sb
    return sb


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


def tts_button(text: str, label: str, key: str):
    '''브라우저 SpeechSynthesis 기반 TTS 버튼.
    - PRO: 클릭 시 재생 / FREE: 잠금(비활성)
    - 일본어 voice 자동 선택(가능하면 Google/日本語系)
    '''
    txt = text or ""
    is_icon = (label or "").strip() in ["🔊", "🔈"]
    disabled = "true" if (not IS_PRO) else "false"
    btn_text = (f"🔒 {label}" if (not IS_PRO) else label)

    style_btn = (
        "width:36px;height:36px;border-radius:999px;display:flex;align-items:center;justify-content:center;font-size:18px;"
        if is_icon
        else "width:100%;padding:8px 10px;border-radius:12px;font-size:15px;"
    )

    components.html(
        f"""
<div style="width:100%;display:flex;justify-content:{'flex-end' if is_icon else 'stretch'};">
  <button id="tts_{key}" {'disabled' if not IS_PRO else ''} style="{style_btn}
           border:1px solid rgba(49,51,63,.18);
           background:{'#f6f7f9' if not IS_PRO else 'white'};
           cursor:{'not-allowed' if not IS_PRO else 'pointer'};
           font-weight:800;opacity:{'0.7' if not IS_PRO else '1.0'};">
    {btn_text}
  </button>
</div>
<script>
(function() {{
  const btn = document.getElementById("tts_{key}");
  if (!btn) return;
  if ({disabled}) return;
  if (btn.dataset.bound === "1") return;
  btn.dataset.bound = "1";

  const synth = window.speechSynthesis;

  function pickJaVoice() {{
    const voices = synth.getVoices() || [];
    const ja = voices.filter(v => String(v.lang || "").toLowerCase().startsWith("ja"));
    if (!ja.length) return null;
    return ja.find(v => /google/i.test(v.name || "")) 
        || ja.find(v => /日本|japanese/i.test(v.name || "")) 
        || ja[0] || null;
  }}

  function speak() {{
    try {{
      const u = new SpeechSynthesisUtterance({txt!r});
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      synth.cancel();
      synth.speak(u);
    }} catch(e) {{}}
  }}

  btn.addEventListener("click", () => {{
    if ((synth.getVoices() || []).length === 0) {{
      let tried = 0;
      const t = setInterval(() => {{
        tried += 1;
        if ((synth.getVoices() || []).length > 0 || tried >= 10) {{
          clearInterval(t);
          speak();
        }}
      }}, 150);
    }} else {{
      speak();
    }}
  }});
}})();
</script>
""",
        height=(44 if is_icon else 60),
    )


def tts_inline_row(role_label: str, text: str, key: str, show_text: bool = True):
    # 문장 오른쪽에 스피커 아이콘을 '텍스트 바로 옆'에 붙여 표시 (iframe 1개로 렌더링)
    txt = text or ""
    safe = txt.replace("\\", "\\\\").replace("`", "").replace("\n", " ")
    disabled = "true" if (not IS_PRO) else "false"
    btn = "🔒" if (not IS_PRO) else "🔊"
    show = "inline" if show_text else "none"

    components.html(
        f'''
<div style="display:flex;align-items:center;gap:8px;line-height:1.25;">
  <div style="min-width:72px;font-weight:800;opacity:.85;">{role_label}</div>
  <div style="flex:1;display:flex;align-items:center;gap:6px;">
    <span style="display:{show};font-weight:500;">{txt}</span>
    <button id="tts_{key}" {'disabled' if not IS_PRO else ''}
      title="발음 듣기"
      style="padding:0;margin:0;border:none;background:transparent;
             cursor:{'not-allowed' if not IS_PRO else 'pointer'};
             font-size:18px;font-weight:900;line-height:1;
             opacity:{'0.55' if not IS_PRO else '0.9'};">
      {btn}
    </button>
  </div>
</div>
<script>
(function() {{
  const btn = document.getElementById("tts_{key}");
  if (!btn) return;
  if ({disabled}) return;
  if (btn.dataset.bound === "1") return;
  btn.dataset.bound = "1";

  const synth = window.speechSynthesis;

  function pickJaVoice() {{
    const voices = synth.getVoices() || [];
    const ja = voices.filter(v => String(v.lang || "").toLowerCase().startsWith("ja"));
    if (!ja.length) return null;
    return ja.find(v => /google/i.test(v.name || ""))
        || ja.find(v => /日本|japanese/i.test(v.name || ""))
        || ja[0] || null;
  }}

  function speak() {{
    try {{
      const u = new SpeechSynthesisUtterance({safe!r});
      u.lang = "ja-JP";
      const v = pickJaVoice();
      if (v) u.voice = v;
      synth.cancel();
      synth.speak(u);
    }} catch(e) {{}}
  }}

  btn.addEventListener("click", () => {{
    if ((synth.getVoices() || []).length === 0) {{
      let tried = 0;
      const t = setInterval(() => {{
        tried += 1;
        if ((synth.getVoices() || []).length > 0 || tried >= 10) {{
          clearInterval(t);
          speak();
        }}
      }}, 150);
    }} else {{
      speak();
    }}
  }});
}})();
</script>
''',
        height=40,
    )



# ======================================
# ======================================
# ✅ Build choices (문제 로딩 시 1회 셔플 후 고정)
# ============================================================


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
    picks: list[str] = []

    for c in ["d1_jp", "d2_jp", "d3_jp"]:
        if c in row:
            v = str(row.get(c, "")).strip()
            if v and v != correct and v not in picks:
                picks.append(v)

    if len(picks) < 3:
        cand = [a for a in pool_answers if a and a != correct and a not in picks]
        random.shuffle(cand)
        picks += cand[: (3 - len(picks))]

    picks = picks[:3]
    choices = picks + [correct]
    random.shuffle(choices)
    return choices


pool_answers = pool_df["answer_jp"].astype(str).tolist()

# ============================================================
# ✅ Initialize set (10 qids) + pointer
# ============================================================
if f"{NS}_set_qids" not in st.session_state:
    n = min(SET_LEN, len(pool_df))
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
        st.rerun()

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
# ✅ Render card
# ============================================================
with st.container(border=True):
    st.markdown(f"**상황**: {row.get('situation_kr','')}")
    # FREE는 듣기가 잠겨 있으니, 문제 단계에서 스크립트를 보여줍니다.
    # 상대(말): FREE는 스크립트(+잠금), PRO는 스크립트 숨김(듣기만)
    if not IS_PRO:
        tts_inline_row("상대(말)", row.get("partner_jp",""), key=f"{qid}_partner_q", show_text=True)
    else:
        tts_inline_row("상대(말)", row.get("partner_jp",""), key=f"{qid}_partner_q", show_text=False)

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

        picked = st.radio(
            label="보기 선택",
            options=choices,
            index=default_idx,
            key=radio_key,
            disabled=submitted,
            label_visibility="collapsed",
        )
        # 선택값 반영
        if not submitted:
            st.session_state[sel_key] = picked
            selected = picked

        # ============================================================
        # ✅ Controls (단순화)
        # - 이전/다음 제거
        # - "정답 제출" 버튼은 유지 (제출 후에는 비활성)
        # - "다음 문제" 버튼은 최하단(말하기 완료 아래)에서만 노출
        # ============================================================
        can_submit = bool(selected) and (not submitted)
        st.button(
            "정답 제출",
            use_container_width=True,
            disabled=not can_submit,
            key=f"{NS}_submit",
            on_click=(lambda: st.session_state.__setitem__(submitted_key, True)),
        )

# ============================================================
# ✅ After submit
# ============================================================
if submitted:
    correct = str(row.get("answer_jp", "")).strip()
    ok = (selected == correct)

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
        
        # ✅ 상대(말) / 내(말) — 문장 오른쪽에 아이콘을 딱 붙여 표시
        tts_inline_row("상대(말)", row.get("partner_jp", ""), key=f"{qid}_partner_r", show_text=True)
        st.markdown('<div style="margin-top:-10px"></div>', unsafe_allow_html=True)
        tts_inline_row("내(말)", row.get("answer_jp", ""), key=f"{qid}_answer_r", show_text=True)
# ✅ 하테나쌤 코멘트 (explain_kr 우선, 없으면 hint_kr)
        explain_kr = str(row.get("explain_kr", "")).strip()
        hint = str(row.get("hint_kr", "")).strip()

        if explain_kr:
            st.info("💡 하테나쌤 코멘트\n\n" + explain_kr)
        elif hint:
            st.info("💡 하테나쌤 코멘트\n\n" + hint)
        else:
            st.info("💡 하테나쌤 코멘트\n\n포인트: 상황에서 ‘요청/사과/확인/거절’ 중 무엇인지 먼저 잡고, 그에 맞는 톤(정중/캐주얼)을 고르면 실수가 줄어듭니다.")

if submitted:
    with st.container(border=True):
        st.markdown("### 🎤 말하기 체크")

        total_cnt = len(qids)
        current_no = idx + 1
        st.caption(f"📘 진행: {current_no} / {total_cnt}")


        # ✅ 말하기 녹음(선택) — 채점/인식 없이 '내 발화'만 남길 수 있게
        try:
            if hasattr(st, "audio_input"):
                audio = st.audio_input("내 말 녹음(선택)", key=f"{NS}_rec_{qid}")
                if audio is not None:
                    st.audio(audio)
            else:
                st.caption("현재 Streamlit 버전에서는 즉시 녹음이 지원되지 않아, 파일 업로드로 대체됩니다.")
                up = st.file_uploader("내 음성 파일 업로드(선택)", type=["wav", "mp3", "m4a"], key=f"{NS}_rec_up_{qid}")
                if up is not None:
                    st.audio(up)
        except Exception:
            pass

        st.caption("정답을 보고 2~3번 따라 말한 뒤, 아래 버튼을 눌러 다음으로 넘어가세요.")

        if st.button("✅ 다 했어요 (다음)", use_container_width=True, key=f"{NS}_next_after"):
            st.success("+2 XP 🎤 (말하기 완료 보상)")

            nxt = idx + 1
            if nxt >= len(qids):
                nxt = 0
            st.session_state[f"{NS}_idx"] = nxt
            # 상태 초기화(다음 문제)
            st.session_state[submitted_key] = False
            st.session_state.pop(sel_key, None)
            st.session_state.pop(f"{NS}_radio_{qid}", None)
            st.session_state.pop(f"{NS}_speak_done_{qid}", None)
            st.rerun()
# ============================================================
# ✅ Set completion (10문제 모두 제출되면 자동 집계)
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


finalize_set_if_ready()
