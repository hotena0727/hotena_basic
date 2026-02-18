from stats import log_attempt
from __future__ import annotations

import random
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# ✅ 회화 훈련 (V37 안정판: 내용/로직만 개선)
# - 1문제씩 진행 (말하기/자가체크에 유리)
# - 보기 구성(4개): 정답 / 의미 반대 / 단계 불일치 / 완전 무관
# - 보기 순서: 문제당 1회만 생성 → rerun에도 고정
# - 발음: 현재 방식 유지(브라우저 TTS, PRO만)
# ============================================================

CSV_PATH = Path("talk.csv")

# --- TTS (browser speechSynthesis) ---
def _speak(text: str, key: str):
    if not text:
        return
    # components.html needs a unique key per render
    components.html(
        f"""
        <script>
        (function() {{
          const text = {text!r};
          if (!text) return;
          const u = new SpeechSynthesisUtterance(text);
          u.lang = "ja-JP";
          u.rate = 1.0;
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(u);
        }})();
        </script>
        """,
        height=0,
        key=key,
    )

def load_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df = df.fillna("")
    return df

UNRELATED_POOL = [
    "明日は雨です。",
    "コーヒーをください。",
    "駅はどこですか。",
    "今日は暑いですね。",
    "すみません、トイレはどこですか。",
]

def opposite_answer(row: pd.Series) -> str:
    # If CSV provides an explicit opposite response, use it.
    for col in ["opposite_jp", "wrong_opposite_jp"]:
        if col in row.index and str(row.get(col, "")).strip():
            return str(row[col]).strip()
    # Default opposite: "I understood / it's okay"
    return "はい、大丈夫です。"

def mismatch_answer(df: pd.DataFrame, row: pd.Series) -> str:
    # Prefer same scene/tag, otherwise any other answer
    answer_col = "answer_jp" if "answer_jp" in df.columns else None
    if not answer_col:
        return "すみません、少々お待ちください。"
    correct = str(row.get(answer_col, "")).strip()

    def _pick(pool: pd.DataFrame) -> str:
        for _ in range(30):
            cand = str(pool.sample(1).iloc[0].get(answer_col, "")).strip()
            if cand and cand != correct:
                return cand
        return ""

    pool = df[df.index != row.name]
    if "scene" in df.columns:
        same = df[(df.index != row.name) & (df["scene"].astype(str).str.strip() == str(row.get("scene","")).strip())]
        if len(same) >= 1:
            cand = _pick(same)
            if cand:
                return cand

    cand = _pick(pool)
    return cand if cand else "すみません、少々お待ちください。"

def build_choices(df: pd.DataFrame, row: pd.Series) -> list[str]:
    # Expect columns: prompt_jp, answer_jp (required). Optional: scene, intent_kr, answer_kr, tag/category, opposite_jp
    correct = str(row.get("answer_jp", "")).strip()
    opp = opposite_answer(row).strip()
    mis = mismatch_answer(df, row).strip()
    unrel = random.choice(UNRELATED_POOL).strip()

    # Ensure no accidental duplicates
    choices = [correct, opp, mis, unrel]
    uniq = []
    for c in choices:
        c = (c or "").strip()
        if c and c not in uniq:
            uniq.append(c)
    while len(uniq) < 4:
        f = random.choice(UNRELATED_POOL).strip()
        if f not in uniq:
            uniq.append(f)
    uniq = uniq[:4]

    random.shuffle(uniq)
    return uniq

def render_talk(user_plan: str = "free"):
    st.markdown("## 회화 훈련")

    if not CSV_PATH.exists():
        st.error("talk.csv 파일이 없습니다. (프로젝트 루트에 talk.csv를 두세요)")
        return

    df = load_df()
    if df.empty:
        st.info("talk.csv에 데이터가 없습니다.")
        return

    # Optional category/tag filter
    tag_col = None
    for c in ["tag", "category", "mode"]:
        if c in df.columns:
            tag_col = c
            break

    df_view = df
    if tag_col:
        tags = [t for t in sorted({str(x).strip() for x in df[tag_col].tolist() if str(x).strip()})]
        if tags:
            if "talk_tag" not in st.session_state:
                st.session_state["talk_tag"] = tags[0]
            sel = st.selectbox("상황 선택", tags, index=tags.index(st.session_state["talk_tag"]) if st.session_state["talk_tag"] in tags else 0)
            st.session_state["talk_tag"] = sel
            df_view = df[df[tag_col] == sel]

    if "talk_idx" not in st.session_state:
        st.session_state["talk_idx"] = 0

    idx = st.session_state["talk_idx"] % len(df_view)
    row = df_view.iloc[idx]

    scene = str(row.get("scene", "일상")).strip() or "일상"
    prompt_jp = str(row.get("prompt_jp", "")).strip()
    intent_kr = str(row.get("intent_kr", "")).strip()
    answer_jp = str(row.get("answer_jp", "")).strip()
    answer_kr = str(row.get("answer_kr", "")).strip()

    if not prompt_jp or not answer_jp:
        st.error("talk.csv 컬럼이 부족합니다. 최소 prompt_jp, answer_jp 컬럼이 필요합니다.")
        return

    st.markdown(f"**[상황: {scene}]**")
    st.markdown(f"### {prompt_jp}")

    if intent_kr:
        st.caption(f"👉 {intent_kr}")

    # Pronunciation button (PRO only)
    if (user_plan or "free") != "free":
        cols = st.columns([1, 1, 6])
        if cols[0].button("🔊 문제 듣기", key=f"tts_q_btn_{idx}", use_container_width=True):
            _speak(prompt_jp, key=f"tts_q_{idx}_{random.random()}")
    else:
        st.caption("※ 발음 듣기는 PRO 플랜에서 제공됩니다.")

    # Build fixed choices per question (stable across reruns)
    qkey = f"talk_choices_{idx}_{scene}_{prompt_jp}"
    if qkey not in st.session_state:
        # deterministic-ish shuffle per question
        state = random.getstate()
        random.seed(f"{idx}|{scene}|{prompt_jp}")
        st.session_state[qkey] = build_choices(df_view, row)
        random.setstate(state)

    choices = st.session_state[qkey]

    pick = st.radio("보기", choices, index=None, key=f"talk_pick_{idx}")

    submitted_key = f"talk_submitted_{idx}"
    if submitted_key not in st.session_state:
        st.session_state[submitted_key] = False

    if st.button("정답 제출", key=f"talk_submit_{idx}", use_container_width=True):
        st.session_state[submitted_key] = True

    if st.session_state[submitted_key]:
        if pick == answer_jp:
            st.success("정답입니다!")
        log_attempt('talk', 1, 1)
            st.markdown("**설명:** 상대가 이해했는지 확인했기 때문에, 이해가 안 됐다면 정중하게 다시 설명을 요청하는 답이 자연스럽습니다.")
        else:
            st.error("오답입니다.")
            st.markdown(f"**정답:** {answer_jp}")
            st.markdown("**설명:** 이 상황에서는 ‘다시 설명 부탁’처럼 대화 흐름에 맞는 반응이 가장 자연스럽습니다.")

        if answer_kr:
            st.caption(f"정답 해석: {answer_kr}")

        # After submit: PRO can hear both prompt + answer
        if (user_plan or "free") != "free":
            st.markdown("#### 🔊 제출 후 발음")
            c1, c2 = st.columns(2)
            if c1.button("🔊 문제", key=f"tts_q2_btn_{idx}"):
                _speak(prompt_jp, key=f"tts_q2_{idx}_{random.random()}")
            if c2.button("🔊 정답", key=f"tts_a_btn_{idx}"):
                _speak(answer_jp, key=f"tts_a_{idx}_{random.random()}")

    # Next question
    if st.button("다음 문제", key=f"talk_next_{idx}", use_container_width=True):
        # clear per-question pick/submitted (keep choices cache for stability not required)
        st.session_state.pop(f"talk_pick_{idx}", None)
        st.session_state["talk_idx"] += 1
        st.rerun()


if __name__ == "__main__":
    render_talk(st.session_state.get("user_plan", "free"))
