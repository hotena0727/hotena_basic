# talk.py
from __future__ import annotations

from pathlib import Path
import random
from datetime import datetime, date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ============================================================
# ✅ Session gate (공통 로그인은 home.py에서)
# ============================================================
if "user" not in st.session_state:
    st.warning("홈에서 로그인 후 이용해 주세요.")
    st.stop()

USER = st.session_state["user"]
USER_ID = USER.get("id") if isinstance(USER, dict) else None
USER_EMAIL = USER.get("email") if isinstance(USER, dict) else None

st.title("회화 훈련 · 상황판단 (CSV)")
st.caption("상황 → 상대의 한마디(발음 지원) → 쌩뚱맞은 보기 속에서 정답 선택 → 제출 후 보기 발음 지원")

# ============================================================
# ✅ Supabase client
# ============================================================
def _sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        st.error("Supabase secrets가 필요합니다: SUPABASE_URL, SUPABASE_ANON_KEY")
        st.stop()
    return create_client(url, key)

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
    required = ["qid", "level", "situation_kr", "partner_jp", "answer_jp"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    df = df[df["answer_jp"].astype(str).str.len() > 0].reset_index(drop=True)
    return df

try:
    DF = load_csv(CSV_PATH)
except Exception as e:
    st.error("talk_situations.csv 로딩 실패")
    st.code(repr(e))
    st.stop()

# ============================================================
# ✅ Helpers
# ============================================================
def pick_daily_message(user_id: str) -> str:
    # (홈 알림과는 별개) 회화 페이지 상단용 짧은 안내
    msgs = [
        "오늘은 상황판단 10문만!",
        "정답이 티 나지 않게 일부러 보기들을 섞어뒀어요.",
        "틀려도 OK. ‘상황에 맞는 한마디’가 핵심이에요.",
    ]
    seed = f"{user_id}:{date.today().isoformat()}"
    idx = abs(hash(seed)) % len(msgs)
    return msgs[idx]

def normalize_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return []

def ensure_progress():
    """profiles.progress 전체(progress_all)에서 talk 네임스페이스 보장."""
    progress_all = st.session_state.get("progress_all") or {}
    talk = progress_all.get("talk") or {}
    talk.setdefault("mastered_ids", [])
    talk.setdefault("wrong_ids", [])
    talk.setdefault("attempts", 0)
    talk.setdefault("correct", 0)
    talk.setdefault("last_set", {})
    progress_all["talk"] = talk
    st.session_state["progress_all"] = progress_all
    return progress_all, talk

def save_progress(progress_all: dict):
    """profiles.progress 저장"""
    if not USER_ID:
        return
    try:
        sb = _sb()
        sb.table("profiles").update({"progress": progress_all}).eq("id", USER_ID).execute()
    except Exception:
        # 저장 실패해도 UI는 진행되도록 (로그는 Cloud에서 확인)
        pass

def log_attempt(level: str, tag: str, quiz_len: int, score: int, wrong_list: list[str]):
    """quiz_attempts에 기록 (테이블이 없으면 무시)"""
    if not USER_ID:
        return
    payload = {
        "user_id": USER_ID,
        "user_email": USER_EMAIL,
        "level": "talk",
        "pos_mode": f"{level}:{tag}:situation",
        "quiz_len": quiz_len,
        "score": score,
        "wrong_count": len(wrong_list),
        "wrong_list": wrong_list,
        "created_at": datetime.utcnow().isoformat(),
    }
    try:
        sb = _sb()
        sb.table("quiz_attempts").insert(payload).execute()
    except Exception:
        pass

def build_choices(row: dict, pool_answers: list[str]) -> list[str]:
    ans = str(row["answer_jp"]).strip()
    distractors = []
    for k in ["d1_jp", "d2_jp", "d3_jp"]:
        if k in row and str(row.get(k, "")).strip() and str(row.get(k, "")).strip().lower() != "nan":
            distractors.append(str(row[k]).strip())
    # 부족하면 다른 문제의 정답을 섞어서 "쌩뚱맞게 가리기"
    pool = [p for p in pool_answers if p and p != ans]
    random.shuffle(pool)
    while len(distractors) < 3 and pool:
        d = pool.pop()
        if d != ans and d not in distractors:
            distractors.append(d)
    choices = distractors[:3] + [ans]
    random.shuffle(choices)
    return choices

def speak_buttons_html(items: list[tuple[str, str]], block_id: str) -> str:
    """
    items: [(label, text_to_speak), ...]
    block_id: unique id for this block
    """
    # Escape for JS string safely
    def js(s): 
        return s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    btns = []
    for i, (label, text) in enumerate(items):
        btns.append(f"""
        <button class="tts-btn" data-text="{js(text)}" type="button">
          🔊 {js(label)}
        </button>
        """)
    return f"""
    <div id="tts_{block_id}" style="display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px;">
      {''.join(btns)}
    </div>
    <script>
      (function(){{
        const root = document.getElementById("tts_{block_id}");
        if(!root) return;

        function speak(text){{
          if(!("speechSynthesis" in window)) {{
            alert("이 브라우저는 음성 합성을 지원하지 않아요.");
            return;
          }}
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "ja-JP";
          u.rate = 1.0;
          window.speechSynthesis.speak(u);
        }}

        root.querySelectorAll("button.tts-btn").forEach(btn => {{
          btn.addEventListener("click", () => {{
            const t = btn.getAttribute("data-text") || "";
            speak(t);
          }});
        }});
      }})();
    </script>
    <style>
      #tts_{block_id} .tts-btn {{
        padding: 8px 10px;
        border-radius: 12px;
        border: 1px solid rgba(49,51,63,0.2);
        background: rgba(255,255,255,0.04);
        cursor: pointer;
      }}
      #tts_{block_id} .tts-btn:hover {{
        border-color: rgba(49,51,63,0.35);
      }}
    </style>
    """

# ============================================================
# ✅ Filters
# ============================================================
progress_all, talk_prog = ensure_progress()
mastered_ids = set(normalize_list(talk_prog.get("mastered_ids")))
wrong_ids = set(normalize_list(talk_prog.get("wrong_ids")))

levels = sorted(DF["level"].astype(str).unique().tolist())
tags = ["전체"] + sorted([t for t in DF.get("tag", pd.Series(dtype=str)).astype(str).unique().tolist() if t and t != "nan"])

top1, top2, top3 = st.columns([1, 1, 1])
with top1:
    level = st.selectbox("레벨", levels, index=0, key="talk_level")
with top2:
    tag = st.selectbox("태그", tags, index=0, key="talk_tag")
with top3:
    exclude_mastered = st.toggle("정복(맞힌 문항) 제외", value=True, key="talk_exclude_mastered")

st.info(pick_daily_message(str(USER_ID or "guest")))

df2 = DF[DF["level"].astype(str) == str(level)]
if tag != "전체" and "tag" in df2.columns:
    df2 = df2[df2["tag"].astype(str) == str(tag)]

if exclude_mastered:
    df2 = df2[~df2["qid"].astype(str).isin(mastered_ids)]

if len(df2) < 4:
    st.warning("이 조건에서는 문제가 너무 적습니다. (최소 4문항 필요)")
    st.stop()

# ============================================================
# ✅ 10문 세트(단어/한자처럼)
# ============================================================
QUIZ_LEN = 10
NS = "talk"

def start_new_set():
    pool = df2.sample(n=min(QUIZ_LEN, len(df2)), replace=False)
    qids = pool["qid"].astype(str).tolist()
    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = 0
    st.session_state[f"{NS}_score"] = 0
    st.session_state[f"{NS}_wrongs"] = []
    st.session_state[f"{NS}_done"] = []
    st.session_state[f"{NS}_started_at"] = datetime.now().isoformat()
    # 선택 UI 초기화
    st.session_state.pop("talk_choice", None)
    st.session_state.pop("talk_submitted", None)

if f"{NS}_set_qids" not in st.session_state:
    start_new_set()

# Controls
cA, cB, cC = st.columns([1, 1, 1])
with cA:
    if st.button("새 세트(10문) 시작", use_container_width=True, key="talk_new_set"):
        start_new_set()
        st.rerun()
with cB:
    if st.button("오답노트 보기", use_container_width=True, key="talk_show_wrongs"):
        st.session_state["talk_view"] = "wrongs"
        st.rerun()
with cC:
    if st.button("문항 정복 초기화", use_container_width=True, key="talk_reset_mastered"):
        progress_all, talk_prog = ensure_progress()
        talk_prog["mastered_ids"] = []
        talk_prog["wrong_ids"] = []
        save_progress(progress_all)
        st.success("회화 정복/오답을 초기화했습니다.")
        st.rerun()

view = st.session_state.get("talk_view", "quiz")

# ============================================================
# ✅ 오답노트 뷰
# ============================================================
if view == "wrongs":
    st.subheader("오답노트 (회화)")
    wrong_list = normalize_list(talk_prog.get("wrong_ids"))
    if not wrong_list:
        st.info("오답이 없습니다.")
    else:
        wrong_df = DF[DF["qid"].astype(str).isin(set(wrong_list))].copy()
        for _, r in wrong_df.head(50).iterrows():
            st.markdown(f"**[{r['qid']}] {r.get('situation_kr','')}**")
            st.caption(str(r.get("partner_jp","")))
            components.html(
                speak_buttons_html(
                    [("상대", str(r.get("partner_jp",""))), ("정답", str(r.get("answer_jp","")))],
                    block_id=f"w_{r['qid']}"
                ),
                height=90
            )
            st.write(f"정답: {r.get('answer_jp','')}")
            if str(r.get("answer_kr","")).strip():
                st.caption(str(r.get("answer_kr","")).strip())
            st.divider()
    if st.button("← 퀴즈로 돌아가기", use_container_width=True, key="talk_back_quiz"):
        st.session_state["talk_view"] = "quiz"
        st.rerun()
    st.stop()

# ============================================================
# ✅ 퀴즈 뷰
# ============================================================
set_qids = st.session_state.get(f"{NS}_set_qids", [])
idx = int(st.session_state.get(f"{NS}_idx", 0))

if idx >= len(set_qids):
    # 세트 종료 처리
    score = int(st.session_state.get(f"{NS}_score", 0))
    wrongs = st.session_state.get(f"{NS}_wrongs", [])
    done = st.session_state.get(f"{NS}_done", [])
    st.success(f"세트 완료! 점수: {score}/{len(set_qids)}")

    # progress 업데이트(동일 방식)
    progress_all, talk_prog = ensure_progress()
    talk_prog["attempts"] = int(talk_prog.get("attempts", 0)) + len(set_qids)
    talk_prog["correct"] = int(talk_prog.get("correct", 0)) + score
    talk_prog["last_set"] = {
        "level": str(level),
        "tag": str(tag),
        "quiz_len": int(len(set_qids)),
        "score": int(score),
        "wrong_count": int(len(wrongs)),
        "ended_at": datetime.now().isoformat(),
    }

    # 정복/오답 반영
    mastered_now = set(done) - set(wrongs)
    talk_prog["mastered_ids"] = sorted(set(normalize_list(talk_prog.get("mastered_ids"))) | mastered_now)
    talk_prog["wrong_ids"] = sorted(set(normalize_list(talk_prog.get("wrong_ids"))) | set(wrongs))

    save_progress(progress_all)
    log_attempt(level=str(level), tag=str(tag), quiz_len=int(len(set_qids)), score=int(score), wrong_list=wrongs)

    st.button("새 세트 시작", use_container_width=True, on_click=start_new_set, key="talk_restart_set")
    st.stop()

qid = set_qids[idx]
row = DF[DF["qid"].astype(str) == str(qid)].iloc[0].to_dict()

pool_answers = DF["answer_jp"].astype(str).tolist()
choices = build_choices(row, pool_answers)

st.progress((idx) / max(1, len(set_qids)))
st.markdown(f"#### Q{idx+1} / {len(set_qids)}")

# 상황
st.markdown("### 상황")
st.write(str(row.get("situation_kr","")).strip())

# 상대 한마디 + 발음
partner_jp = str(row.get("partner_jp","")).strip()
partner_kr = str(row.get("partner_kr","")).strip()

st.markdown("### 상대의 한마디")
st.write(partner_jp if partner_jp else "（상대 발화가 비어 있습니다. CSV의 partner_jp를 채워주세요.）")
if partner_kr:
    st.caption(partner_kr)

components.html(
    speak_buttons_html([("상대 발화 듣기", partner_jp)], block_id=f"partner_{qid}_{idx}"),
    height=90
)

# 선택
st.markdown("### 보기")
selected = st.radio(
    "정답을 고르세요.",
    choices,
    key="talk_choice",
)

submitted = st.session_state.get("talk_submitted", False)

btn1, btn2, btn3 = st.columns([1, 1, 1])
with btn1:
    if st.button("제출", use_container_width=True, disabled=submitted, key=f"talk_submit_{qid}_{idx}"):
        st.session_state["talk_submitted"] = True
        # 채점
        ans = str(row["answer_jp"]).strip()
        ok = (selected == ans)

        done = st.session_state.get(f"{NS}_done", [])
        done.append(str(qid))
        st.session_state[f"{NS}_done"] = done

        if ok:
            st.session_state[f"{NS}_score"] = int(st.session_state.get(f"{NS}_score", 0)) + 1
        else:
            wrongs = st.session_state.get(f"{NS}_wrongs", [])
            wrongs.append(str(qid))
            st.session_state[f"{NS}_wrongs"] = list(dict.fromkeys(wrongs))  # unique

        st.rerun()

with btn2:
    if st.button("다음", use_container_width=True, disabled=not submitted, key=f"talk_next_{qid}_{idx}"):
        st.session_state[f"{NS}_idx"] = idx + 1
        st.session_state["talk_submitted"] = False
        # 다음 문제에서 선택 초기화
        st.session_state.pop("talk_choice", None)
        st.rerun()

with btn3:
    if st.button("힌트", use_container_width=True, key=f"talk_hint_{qid}_{idx}"):
        hint = str(row.get("hint_kr","")).strip()
        st.info(hint if hint else "힌트가 없습니다. (CSV에 hint_kr을 채워주세요.)")

# 제출 후 해설 + 보기 발음 지원
if submitted:
    ans = str(row["answer_jp"]).strip()
    if selected == ans:
        st.success("정답입니다.")
    else:
        st.error("오답입니다.")

    st.markdown("### 정답")
    st.write(ans)
    if str(row.get("answer_kr","")).strip():
        st.caption(str(row.get("answer_kr","")).strip())

    # 보기 발음 지원(제출 후)
    st.markdown("### 보기 발음")
    items = [(f"보기 {i+1}", t) for i, t in enumerate(choices)]
    components.html(
        speak_buttons_html(items, block_id=f"choices_{qid}_{idx}"),
        height=120
    )
