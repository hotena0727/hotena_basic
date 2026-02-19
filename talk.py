# talk.py (v26)
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ============================================================
# ✅ Settings
# ============================================================
NS = "talk"
QUIZ_LEN = 10

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

st.title("회화 훈련 · 상황판단")
st.caption("상황 → 상대 발화(🔊/PRO) → 보기 선택 → 제출 후 정답/설명(🔊/PRO)")

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
    # optional:
    # partner_kr, answer_kr, hint_kr, audio_partner, audio_answer
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"nan": "", "NaN": "", "None": ""})
    return df.fillna("")

DF = load_csv(CSV_PATH)

# ============================================================
# ✅ UI labels
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
def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def ensure_profile():
    # best-effort: if profile row doesn't exist, do nothing (word app usually creates it)
    return

def load_progress() -> dict:
    # home/word/kanji usually load and put in session_state; reuse if present
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

def log_attempt(level: str, score: int, wrong_count: int, wrong_list: list[dict]):
    try:
        sb.table("quiz_attempts").insert({
            "user_id": USER_ID,
            "user_email": USER_EMAIL,
            "level": level,
            "pos_mode": "talk",
            "quiz_len": QUIZ_LEN,
            "score": score,
            "wrong_count": wrong_count,
            "wrong_list": wrong_list,
        }).execute()
    except Exception:
        pass

# ============================================================
# ✅ New set / reset on hub navigation
# ============================================================
def reset_set():
    for k in list(st.session_state.keys()):
        if k.startswith(f"{NS}_q_") or k.startswith(f"{NS}_choices_"):
            st.session_state.pop(k, None)
    st.session_state.pop(f"{NS}_set_qids", None)
    st.session_state.pop(f"{NS}_submitted", None)
    st.session_state.pop(f"{NS}_answers", None)

try:
    nav = st.session_state.get("_hub_nav_token")
    last = st.session_state.get(f"_{NS}_last_nav_token")
    if nav and nav != last:
        st.session_state[f"_{NS}_last_nav_token"] = nav
        reset_set()
except Exception:
    pass

# ============================================================
# ✅ Filters (tag/level)
# ============================================================
all_tags = [t for t in DF["tag"].astype(str).unique().tolist() if t]
tag_options = [t for t in ["daily","business","call","interview","travel","shopping","food","emergency"] if t in all_tags]
if not tag_options:
    tag_options = all_tags

tag = st.selectbox(
    "상황 선택",
    options=tag_options,
    format_func=lambda x: TAG_LABELS.get(x, x),
    key=f"{NS}_tag",
)

# level: only n5~n3 for 왕초보
levels_in_data = [lv for lv in ["n5","n4","n3"] if lv in DF["level"].astype(str).str.lower().unique().tolist()]
if not levels_in_data:
    levels_in_data = ["n5","n4","n3"]

level = st.selectbox(
    "레벨",
    options=levels_in_data,
    format_func=lambda x: LEVEL_LABELS.get(x, x.upper()),
    key=f"{NS}_level",
)

pool_df = DF[
    (DF["tag"].astype(str) == tag) &
    (DF["level"].astype(str).str.lower() == level)
].copy()

if pool_df.empty:
    st.warning("해당 조건의 회화 문제가 없습니다. (CSV의 tag/level 확인)")
    st.stop()

# ============================================================
# ✅ Build choices (고정)
# ============================================================
def build_choices(row: dict, pool_answers: list[str]) -> list[str]:
    correct = str(row.get("answer_jp","")).strip()
    # distractors: CSV의 d1~d3 우선, 부족하면 pool에서 보충
    dcols = [c for c in ['d1_jp','d2_jp','d3_jp'] if c in row]
    picks = []
    for c in dcols:
        v = str(row.get(c,'')).strip()
        if v and v != correct:
            picks.append(v)
    picks = picks[:3]
    if len(picks) < 3:
        cand = [a for a in pool_answers if a and a != correct and a not in picks]
        random.shuffle(cand)
        picks += cand[:(3-len(picks))]
    choices = picks + [correct]
    random.shuffle(choices)
    # 고정: qid별로 저장해서 렌더가 흔들리지 않게
    return choices

pool_answers = pool_df["answer_jp"].astype(str).tolist()

# ============================================================
# ✅ Initialize set (10 questions)
# ============================================================
if f"{NS}_set_qids" not in st.session_state:
    n = min(QUIZ_LEN, len(pool_df))
    sample = pool_df.sample(n=n, replace=False).reset_index(drop=True)
    qids = sample["qid"].astype(str).tolist()
    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_answers"] = {qid: None for qid in qids}
    st.session_state[f"{NS}_submitted"] = False

qids = st.session_state[f"{NS}_set_qids"]
submitted = bool(st.session_state.get(f"{NS}_submitted"))
answers: dict = st.session_state.get(f"{NS}_answers") or {qid: None for qid in qids}

# ============================================================
# ✅ Goal reminder (from last self-eval)
# ============================================================
prog = load_progress()
talk_prog = prog.get("talk") or {}
last_goal = (talk_prog.get("last_goal") or "").strip()
if last_goal:
    st.info(f"🎯 오늘의 말하기 목표: **{last_goal}**")

# ============================================================
# ✅ Render 10 questions
# ============================================================
st.markdown("### 10문제 세트")

for i, qid in enumerate(qids):
    row = pool_df[pool_df["qid"].astype(str) == str(qid)].iloc[0].to_dict()

    # fixed choices
    ck = f"{NS}_choices_{qid}"
    if ck not in st.session_state:
        st.session_state[ck] = build_choices(row, pool_answers)
    choices = st.session_state[ck]

    # placeholder to avoid auto-select
    placeholder = "— 선택 —"
    opts = [placeholder] + choices

    # stable widget key
    wkey = f"{NS}_q_{qid}"

    # default index based on current answer
    cur = answers.get(qid)
    idx = 0
    if cur and cur in choices:
        idx = opts.index(cur)

    with st.container(border=True):
        st.markdown(f"**{i+1}. 상황**: {row.get('situation_kr','')}")
        st.markdown(f"**상대**: {row.get('partner_jp','')}")

        # audio (PRO only)
        if IS_PRO:
            # text-to-speech is not built-in; we reuse the 'audio_partner' base64/url if provided (best-effort)
            # If not provided, we simply show the 🔊 button placeholder.
            ap = str(row.get("audio_partner","")).strip()
            if ap:
                st.audio(ap)
            else:
                st.caption("🔊 (PRO) 발음 데이터가 있으면 여기서 재생됩니다.")
        else:
            st.caption("🔒 발음 듣기(🔊)는 PRO에서 제공됩니다.")

        picked = st.radio(
            "보기",
            options=opts,
            index=idx,
            key=wkey,
            label_visibility="collapsed",
            disabled=submitted,
        )
        if picked == placeholder:
            answers[qid] = None
        else:
            answers[qid] = picked

# persist answers
st.session_state[f"{NS}_answers"] = answers

# ============================================================
# ✅ Controls
# ============================================================
c1, c2 = st.columns(2)
with c1:
    if st.button("새 문제(10문제)", use_container_width=True, disabled=False):
        reset_set()
        st.rerun()

with c2:
    can_submit = (not submitted) and all(answers.get(qid) for qid in qids)
    if st.button("정답 제출", use_container_width=True, disabled=not can_submit):
        st.session_state[f"{NS}_submitted"] = True
        submitted = True

# ============================================================
# ✅ After submit: results + audio + explanation + self-eval summary
# ============================================================
if submitted:
    score = 0
    wrong_list = []
    st.markdown("---")
    st.subheader("채점 결과")

    for i, qid in enumerate(qids):
        row = pool_df[pool_df["qid"].astype(str) == str(qid)].iloc[0].to_dict()
        correct = str(row.get("answer_jp","")).strip()
        selected = str(answers.get(qid) or "").strip()

        ok = (selected == correct)
        score += 1 if ok else 0
        if not ok:
            wrong_list.append({"qid": qid, "selected": selected, "correct": correct})

        with st.expander(f"{i+1}. {'정답 ✅' if ok else '오답 ❌'}", expanded=not ok):
            st.markdown(f"**상황**: {row.get('situation_kr','')}")
            st.markdown(f"**상대 스크립트**: {row.get('partner_jp','')}")
            if IS_PRO:
                ap = str(row.get("audio_partner","")).strip()
                if ap:
                    st.audio(ap)
            st.markdown(f"**정답 스크립트**: {correct}")
            if IS_PRO:
                aa = str(row.get("audio_answer","")).strip()
                if aa:
                    st.audio(aa)

            # explanation / hint
            hint = str(row.get("hint_kr","")).strip()
            if hint:
                st.info(hint)
            else:
                st.info("정답은 ‘상황’에 가장 자연스럽게 맞는 반응입니다. 상대의 의도(요청/사과/확인/거절)를 먼저 잡고 고르는 것이 포인트예요.")

    wrong_count = len(wrong_list)
    st.success(f"점수: {score}/{QUIZ_LEN}  ·  오답: {wrong_count}")

    # =========================
    # ✅ One-line coach feedback
    # =========================
    # Use the latest self-eval (if exists), else use score
    talk_prog = (load_progress().get("talk") or {})
    hist = talk_prog.get("self_eval_history") or []
    coach = ""
    if hist:
        last = hist[-1]
        pron = int(last.get("pron") or 0)
        inton = int(last.get("inton") or 0)
        speed = int(last.get("speed") or 0)
        if pron >= 4 and inton >= 4:
            coach = "코치: 발음과 억양이 아주 좋아요. 오늘은 ‘속도’를 조금 더 자연스럽게만 다듬어 봅시다."
        elif pron >= 4:
            coach = "코치: 발음이 안정적이에요. 다음은 억양을 ‘끝을 올려 말하기/내려 말하기’로 조절해 보세요."
        elif speed >= 4:
            coach = "코치: 속도는 좋아요. 발음은 ‘모음 길이’와 ‘탁음(っ)’만 더 신경 쓰면 금방 좋아져요."
        else:
            coach = "코치: 오늘은 ‘짧게 끊어 말하기’로 정확도를 올려봅시다. 한 문장을 2~3덩어리로 나누면 훨씬 편해요."
    else:
        if score >= 9:
            coach = "코치: 흐름이 아주 좋습니다. 내일은 같은 태그로 한 번 더 가볍게 반복해요."
        elif score >= 7:
            coach = "코치: 좋습니다. 오답만 3개 골라 ‘상황→의도→반응’ 순서로 다시 확인해 보세요."
        else:
            coach = "코치: 괜찮아요. 오늘은 ‘상황 키워드(감사/사과/요청/거절)’만 먼저 잡는 연습을 해봅시다."

    st.markdown(f"**{coach}**")

    # =========================
    # ✅ Save progress + attempts
    # =========================
    prog = load_progress()
    talk_prog = prog.get("talk") or {}
    talk_prog["attempts"] = int(talk_prog.get("attempts") or 0) + QUIZ_LEN
    talk_prog["correct"]  = int(talk_prog.get("correct") or 0) + score
    talk_prog["wrongs"]   = int(talk_prog.get("wrongs") or 0) + wrong_count

    # store last set
    talk_prog["last_set"] = {
        "ts": datetime.utcnow().isoformat(),
        "tag": tag,
        "level": level,
        "score": score,
        "wrong_count": wrong_count,
        "qids": qids,
        "wrongs": wrong_list,
    }
    prog["talk"] = talk_prog
    save_progress(prog)
    log_attempt(level=level, score=score, wrong_count=wrong_count, wrong_list=wrong_list)

# ============================================================
# ✅ Speaking mode: record + self-eval
# ============================================================
with st.expander("🎙️ 말하기 모드", expanded=False):
    st.caption("정답을 확인한 뒤, 똑같이 말해 보세요. (녹음은 본인 확인용)")
    try:
        audio = st.audio_input("녹음하기")
        if audio is not None:
            st.audio(audio)
    except Exception:
        st.info("현재 환경에서 녹음 기능을 사용할 수 없습니다.")

with st.expander("🎯 자기평가(말하기 체크)", expanded=False):
    pron = st.slider("발음(정확도)", 1, 5, 3, key=f"{NS}_se_pron")
    inton = st.slider("억양(자연스러움)", 1, 5, 3, key=f"{NS}_se_inton")
    speed = st.slider("속도(적절함)", 1, 5, 3, key=f"{NS}_se_speed")
    conf  = st.slider("자신감", 1, 5, 3, key=f"{NS}_se_conf")
    goal  = st.text_input("다음 목표(한 줄)", value=last_goal or "", key=f"{NS}_se_goal")

    if st.button("자기평가 저장", use_container_width=True, key=f"{NS}_se_save"):
        prog = load_progress()
        talk_prog = prog.get("talk") or {}
        hist = talk_prog.get("self_eval_history") or []
        hist.append({
            "ts": datetime.utcnow().isoformat(),
            "pron": pron,
            "inton": inton,
            "speed": speed,
            "conf": conf,
        })
        talk_prog["self_eval_history"] = hist[-200:]  # cap
        talk_prog["last_goal"] = (goal or "").strip()
        prog["talk"] = talk_prog
        save_progress(prog)
        st.success("저장했습니다. 마이페이지(말하기)에서 최근 7일 평균/추이를 확인할 수 있어요.")
