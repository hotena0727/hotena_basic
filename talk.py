from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import streamlit as st

from ui_components import render_header, nav_to
# ============================================================
# ✅ Talk (Conversation) training - V37 style safe patch
# - 1 question at a time (better for recording / self-check)
# - Options: 1 correct, 1 opposite-intent, 1 mismatch-level, 1 unrelated
# - Options are generated ONCE per question and never reshuffled on rerun
# ============================================================

CSV_PATH = Path("talk.csv")

def load_talk_df() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    # Normalize common NaNs
    df = df.fillna("")
    # Expected columns (flexible): scene, prompt_jp, prompt_kr, intent_kr, answer_jp, answer_kr, tag(optional)
    return df

def pick_opposite_intent_answer(scene: str) -> str:
    # A safe, beginner-friendly "opposite" response: understands / accepts without asking again
    # (Opposite of "I didn't understand, please explain again")
    # Keep short and natural.
    return "はい、大丈夫です。"

UNRELATED_POOL = [
    "明日は雨です。",
    "コーヒーをください。",
    "駅はどこですか。",
    "今日は暑いですね。",
    "すみません、トイレはどこですか。",
]

def build_choices(df: pd.DataFrame, row: pd.Series) -> list[str]:
    correct = (row.get("answer_jp") or "").strip()
    scene = (row.get("scene") or "").strip()

    opposite = pick_opposite_intent_answer(scene)

    # mismatch-level: pick another answer from SAME scene if possible, otherwise any other answer
    same_scene = df[(df.get("scene","") == scene) & (df.index != row.name)]
    pool = same_scene if len(same_scene) >= 1 else df[df.index != row.name]
    mismatch = ""
    for _ in range(20):
        cand = (pool.sample(1).iloc[0].get("answer_jp") or "").strip()
        if cand and cand != correct and cand != opposite:
            mismatch = cand
            break
    if not mismatch:
        mismatch = "すみません、少々お待ちください。"

    unrelated = random.choice(UNRELATED_POOL)
    # Ensure unrelated isn't accidentally correct
    if unrelated == correct:
        unrelated = "コーヒーをください。"

    choices = [correct, opposite, mismatch, unrelated]
    # De-dupe while preserving, then pad if needed
    uniq = []
    for c in choices:
        c = (c or "").strip()
        if c and c not in uniq:
            uniq.append(c)
    while len(uniq) < 4:
        filler = random.choice(UNRELATED_POOL)
        if filler not in uniq:
            uniq.append(filler)
    uniq = uniq[:4]

    # Shuffle ONCE (deterministic per question)
    random.shuffle(uniq)
    return uniq

def render_talk_page(user_plan: str = "free"):
    apply_ui_theme()
    render_header(\"회화 훈련\", user_plan=user_plan, show_home=True, show_mypage=True)
    st.markdown("## 회화 훈련")

    df = load_talk_df()
    if df.empty:
        st.info("회화 데이터(talk.csv)가 비어 있습니다.")
        return

    # Category filter if exists
    tag_col = None
    for c in ["tag", "category", "mode"]:
        if c in df.columns:
            tag_col = c
            break

    if tag_col:
        tags = [t for t in sorted(set([x.strip() for x in df[tag_col].fillna("").tolist() if str(x).strip()])) if t]
        if "talk_tag" not in st.session_state:
            st.session_state["talk_tag"] = tags[0] if tags else ""
        sel = st.selectbox("상황 선택", options=tags, index=tags.index(st.session_state["talk_tag"]) if st.session_state["talk_tag"] in tags else 0)
        st.session_state["talk_tag"] = sel
        df_view = df[df[tag_col] == sel] if sel else df
    else:
        df_view = df

    if "talk_idx" not in st.session_state:
        st.session_state["talk_idx"] = 0

    idx = st.session_state["talk_idx"] % len(df_view)
    row = df_view.iloc[idx]

    scene = (row.get("scene") or "일상").strip()
    prompt_jp = (row.get("prompt_jp") or "").strip()
    intent_kr = (row.get("intent_kr") or "").strip()
    prompt_kr = (row.get("prompt_kr") or "").strip()
    answer_jp = (row.get("answer_jp") or "").strip()
    answer_kr = (row.get("answer_kr") or "").strip()

    st.markdown(f"**[상황: {scene}]**")
    if prompt_jp:
        st.markdown(f"### {prompt_jp}")
    if intent_kr:
        st.caption(f"👉 {intent_kr}")
    elif prompt_kr:
        st.caption(f"👉 {prompt_kr}")

    # PRO-only pronunciation button placeholder (keeps V37 design minimal)
    if (user_plan or "free") != "free":
        with st.expander("🔊 발음 듣기", expanded=False):
            st.write("문제:", prompt_jp)
    else:
        st.caption("※ 발음 듣기는 PRO 플랜에서 제공됩니다.")

    qkey = f"talk_choices_{scene}_{idx}"
    if qkey not in st.session_state:
        # Seed with stable seed per question to avoid reshuffle on rerun
        rnd_state = random.getstate()
        random.seed(f"{scene}-{idx}-{prompt_jp}")
        st.session_state[qkey] = build_choices(df_view, row)
        random.setstate(rnd_state)

    choices = st.session_state[qkey]
    # radio with no default selection
    pick = st.radio("보기", choices, index=None, key=f"talk_pick_{idx}")

    if st.button("정답 제출", use_container_width=True):
        if pick == answer_jp:
            st.success("정답입니다!")
            st.markdown("**이런 답이 맞아요:** 상대가 이해했는지 확인했기 때문에, 이해가 안 됐으면 정중하게 다시 설명을 요청하는 게 자연스럽습니다.")
        else:
            st.error("오답입니다.")
            st.markdown(f"**정답:** {answer_jp}")

        # After submit: show both pronunciations (PRO)
        if (user_plan or "free") != "free":
            st.markdown("#### 🔊 제출 후 발음")
            col1, col2 = st.columns(2)
            with col1:
                st.write("문제")
                st.write(prompt_jp)
            with col2:
                st.write("정답")
                st.write(answer_jp)

        if answer_kr:
            st.caption(f"정답 해석: {answer_kr}")

    if st.button("다음 문제", use_container_width=True):
        # Clear pick for next question
        st.session_state.pop(f"talk_pick_{idx}", None)
        st.session_state["talk_idx"] += 1
        st.rerun()


if __name__ == "__main__":
    # In hub environment, user_plan may be injected via session_state
    render_talk_page(st.session_state.get("user_plan", "free"))
