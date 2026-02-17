# talk.py
from __future__ import annotations

from pathlib import Path
import random
from datetime import datetime, date

import pandas as pd
import streamlit as st
from supabase import create_client

# ============================================================
# ✅ Session gate (공통 로그인은 home.py에서)
# ============================================================
if "user" not in st.session_state:
    st.warning("홈에서 로그인 후 이용해 주세요.")
    st.stop()

st.title("회화 훈련 (상황판단)")
st.caption("CSV 기반 출제 + DB 저장(단어/한자와 동일한 profiles.progress 방식)")

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "talk_situations.csv"

if not CSV_PATH.exists():
    st.error(f"CSV 파일이 없습니다: {CSV_PATH}")
    st.caption("data/talk_situations.csv 를 만들어서 올려주세요.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_talk_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = ["qid", "level", "scene_kr", "answer_jp"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    df = df[df["answer_jp"].astype(str).str.len() > 0].reset_index(drop=True)
    return df

try:
    df = load_talk_csv(CSV_PATH)
except Exception as e:
    st.error("CSV 로딩 중 오류")
    st.code(repr(e))
    st.stop()

# ============================================================
# ✅ DB helpers (hub에서 공유한 방식)
# ============================================================
def get_authed_sb():
    token = st.session_state.get("access_token")
    cfg = st.session_state.get("cfg", {}) or {}
    if not token:
        return None
    sb2 = st.session_state.get("sb_authed")
    if sb2 is not None and st.session_state.get("sb_authed_token") == token:
        return sb2
    sb2 = create_client(cfg.get("SUPABASE_URL"), cfg.get("SUPABASE_ANON_KEY"))
    sb2.postgrest.auth(token)
    st.session_state["sb_authed"] = sb2
    st.session_state["sb_authed_token"] = token
    return sb2

def save_progress(sb_authed, user_id: str, progress: dict):
    sb_authed.table("profiles").update({"progress": progress}).eq("id", user_id).execute()

def save_attempt(sb_authed, user_id: str, user_email: str, score: int, wrong_list: list):
    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "level": "talk",           # ✅ level 컬럼에 talk 저장
        "pos_mode": "situation",   # ✅ pos_mode 컬럼에 유형 저장
        "quiz_len": 1,
        "score": int(score),
        "wrong_count": int(len(wrong_list)),
        "wrong_list": wrong_list,
    }
    sb_authed.table("quiz_attempts").insert(payload).execute()

sb_authed = get_authed_sb()
if sb_authed is None:
    st.error("세션이 없습니다. 홈에서 다시 로그인해 주세요.")
    st.stop()

user = st.session_state["user"]
user_id = getattr(user, "id", None) or user.get("id")
user_email = getattr(user, "email", None) or user.get("email", "")

# ============================================================
# ✅ Filters
# ============================================================
col1, col2 = st.columns([1, 1])
with col1:
    levels = sorted(df["level"].astype(str).unique().tolist())
    level = st.selectbox("레벨", levels, index=0)
with col2:
    if "tag" in df.columns:
        tags = ["전체"] + sorted([t for t in df["tag"].astype(str).unique().tolist() if t and t != "nan"])
        tag = st.selectbox("태그", tags, index=0)
    else:
        tag = "전체"

df2 = df[df["level"].astype(str) == str(level)]
if tag != "전체" and "tag" in df2.columns:
    df2 = df2[df2["tag"].astype(str) == str(tag)]

if len(df2) < 4:
    st.warning("이 필터 조건에서는 문제가 너무 적습니다. (보기 4개 구성이 어려움)")
    st.caption("tag=전체로 바꾸거나 CSV에 문제를 더 추가해 주세요.")

# ============================================================
# ✅ Progress (profiles.progress['talk'])
# ============================================================
progress_all = st.session_state.get("progress_all", {}) or {}
talk_prog = progress_all.get("talk") or {}
seen = talk_prog.get("seen_qids") or []
if not isinstance(seen, list):
    seen = []
total = int(talk_prog.get("total", 0))
correct = int(talk_prog.get("correct", 0))
streak = int(talk_prog.get("streak", 0))
last_date = talk_prog.get("last_date", "")

def pick_question() -> dict:
    # 가능한 한 미풀이 우선
    pool = df2.copy()
    if "qid" in pool.columns and len(seen) > 0:
        unseen = pool[~pool["qid"].isin(seen)]
        if len(unseen) >= 1:
            pool = unseen
    row = pool.sample(1).iloc[0].to_dict()
    ans = str(row.get("answer_jp", "")).strip()

    distractors = []
    for k in ["d1_jp", "d2_jp", "d3_jp"]:
        if k in row:
            v = str(row.get(k, "")).strip()
            if v and v.lower() != "nan":
                distractors.append(v)

    # 부족하면 전체 정답풀에서 섞어 채우기 (쌩뚱맞게 가리기)
    all_pool = [x.strip() for x in df["answer_jp"].astype(str).tolist() if x and x.strip() and x.strip() != ans]
    random.shuffle(all_pool)
    while len(distractors) < 3 and all_pool:
        v = all_pool.pop()
        if v != ans and v not in distractors:
            distractors.append(v)

    choices = distractors[:3] + [ans]
    random.shuffle(choices)

    return {
        "qid": str(row.get("qid", "")),
        "scene_kr": str(row.get("scene_kr", "")).strip(),
        "scene_jp": str(row.get("scene_jp", "")).strip() if "scene_jp" in row else "",
        "answer_jp": ans,
        "answer_kr": str(row.get("answer_kr", "")).strip() if "answer_kr" in row else "",
        "hint_kr": str(row.get("hint_kr", "")).strip() if "hint_kr" in row else "",
        "choices": choices,
    }

if "talk_q" not in st.session_state:
    st.session_state.talk_q = pick_question()
if "talk_last" not in st.session_state:
    st.session_state.talk_last = None

q = st.session_state.talk_q

# ============================================================
# ✅ UI
# ============================================================
st.markdown("### 상황")
st.write(q["scene_kr"])
if q.get("scene_jp"):
    st.caption(q["scene_jp"])

st.markdown("### 보기")
selected = st.radio("정답을 고르세요.", q["choices"], key="talk_choice")

c1, c2, c3 = st.columns([1,1,1])
with c1:
    submit = st.button("제출", use_container_width=True)
with c2:
    if st.button("새 문제", use_container_width=True):
        st.session_state.talk_last = None
        st.session_state.talk_q = pick_question()
        st.rerun()
with c3:
    if st.button("힌트", use_container_width=True):
        if q.get("hint_kr"):
            st.info(q["hint_kr"])
        else:
            st.info("힌트가 없어요. (CSV에 hint_kr 컬럼 추가 가능)")

if submit:
    ok = (selected == q["answer_jp"])
    st.session_state.talk_last = {"ok": ok, "selected": selected}
    # DB save
    today = date.today().isoformat()
    new_seen = seen[:]  # copy
    if q["qid"] and q["qid"] not in new_seen:
        new_seen.append(q["qid"])
        # cap
        if len(new_seen) > 2000:
            new_seen = new_seen[-2000:]

    total2 = total + 1
    correct2 = correct + (1 if ok else 0)

    if last_date == today:
        streak2 = streak  # already counted today
    else:
        streak2 = (streak + 1) if ok else 0

    progress_all["talk"] = {
        "seen_qids": new_seen,
        "total": total2,
        "correct": correct2,
        "streak": streak2,
        "last_date": today,
        "last_qid": q["qid"],
        "last_ok": bool(ok),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    st.session_state["progress_all"] = progress_all

    try:
        save_progress(sb_authed, user_id, progress_all)
    except Exception:
        pass

    try:
        wrong_list = [] if ok else [{"qid": q["qid"], "selected": selected, "answer": q["answer_jp"]}]
        save_attempt(sb_authed, user_id, user_email, 1 if ok else 0, wrong_list)
    except Exception:
        pass

    st.rerun()

if st.session_state.talk_last:
    res = st.session_state.talk_last
    if res["ok"]:
        st.success("정답입니다.")
    else:
        st.error("오답입니다.")

    st.markdown("### 정답")
    st.write(q["answer_jp"])
    if q.get("answer_kr"):
        st.caption(q["answer_kr"])
