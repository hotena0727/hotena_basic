from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import streamlit as st

# ============================================================
# ✅ 회화 훈련 (V37 디자인 유지용: 최소 침습 / 1문제씩)
# - CSV 기반: data/talk_situations.csv (없으면 talk.csv도 탐색)
# - 보기 구성(4):
#   1) 정답
#   2) 의미 반대(의도 반대/이해했다 계열)
#   3) 단계 불일치(같은 태그의 다른 정답)
#   4) 완전 무관(다른 태그의 정답 or 고정 풀)
# - 보기 순서: 문제당 1회 생성 → rerun에도 고정
# - 발음: 현행 유지(추후 교체 예정) — PRO에서만 노출
# ============================================================

CANDIDATE_CSVS = [
    Path("data/talk_situations.csv"),
    Path("data/talk.csv"),
    Path("talk.csv"),
]

UNRELATED_POOL = [
    "明日は雨です。",
    "コーヒーをください。",
    "駅はどこですか。",
    "今日は暑いですね。",
    "すみません、トイレはどこですか。",
]

def _find_csv() -> Path | None:
    for p in CANDIDATE_CSVS:
        if p.exists():
            return p
    return None

def load_talk_df() -> pd.DataFrame:
    path = _find_csv()
    if not path:
        raise FileNotFoundError("talk csv not found (data/talk_situations.csv)")
    df = pd.read_csv(path, encoding="utf-8-sig").fillna("")
    return df

def opposite_answer(scene_tag: str) -> str:
    # 의미 반대(예: "다시 설명해 주세요" ↔ "네, 괜찮습니다")
    # 초보에게 안전한 반대 의도
    return "はい、大丈夫です。"

def build_choices(df: pd.DataFrame, row: pd.Series) -> list[str]:
    correct = str(row.get("answer_jp", "")).strip()
    tag = str(row.get("tag", "")).strip()

    opp = opposite_answer(tag)

    # 단계 불일치: 같은 tag의 다른 정답을 우선
    mismatch = ""
    same_tag = df[(df.get("tag", "") == tag) & (df.index != row.name)]
    pool = same_tag if len(same_tag) >= 1 else df[df.index != row.name]
    for _ in range(30):
        cand = str(pool.sample(1).iloc[0].get("answer_jp", "")).strip()
        if cand and cand not in {correct, opp}:
            mismatch = cand
            break
    if not mismatch:
        mismatch = "少々お待ちください。"

    # 완전 무관: 다른 tag 정답 or 고정 풀
    unrelated = ""
    other_tag = df[(df.get("tag", "") != tag) & (df.index != row.name)]
    if len(other_tag) >= 1:
        for _ in range(30):
            cand = str(other_tag.sample(1).iloc[0].get("answer_jp", "")).strip()
            if cand and cand not in {correct, opp, mismatch}:
                unrelated = cand
                break
    if not unrelated:
        unrelated = random.choice(UNRELATED_POOL)

    choices = [correct, opp, mismatch, unrelated]
    # de-dupe, pad
    uniq = []
    for c in choices:
        c = str(c).strip()
        if c and c not in uniq:
            uniq.append(c)
    while len(uniq) < 4:
        filler = random.choice(UNRELATED_POOL)
        if filler not in uniq:
            uniq.append(filler)
    uniq = uniq[:4]
    random.shuffle(uniq)
    return uniq

def render_talk_page(user_plan: str = "free"):
    st.markdown("## 회화 훈련")

    df = load_talk_df()
    if df.empty:
        st.info("회화 데이터가 비어 있습니다.")
        return

    # 태그(상황) 선택
    tags = [t for t in sorted({str(x).strip() for x in df.get("tag", "").tolist()}) if t]
    if "talk_tag" not in st.session_state:
        st.session_state["talk_tag"] = tags[0] if tags else ""
    if tags:
        sel = st.selectbox("상황 선택", options=tags, index=tags.index(st.session_state["talk_tag"]) if st.session_state["talk_tag"] in tags else 0)
        st.session_state["talk_tag"] = sel
        dfv = df[df.get("tag", "") == sel].reset_index(drop=True)
    else:
        dfv = df.reset_index(drop=True)

    if "talk_idx" not in st.session_state:
        st.session_state["talk_idx"] = 0

    idx = st.session_state["talk_idx"] % len(dfv)
    row = dfv.iloc[idx]

    # 표시 요소
    scene = str(row.get("tag", "일상")).strip()
    partner_jp = str(row.get("partner_jp", "")).strip()
    situation_kr = str(row.get("situation_kr", "")).strip()
    hint_kr = str(row.get("hint_kr", "")).strip()
    answer_jp = str(row.get("answer_jp", "")).strip()
    answer_kr = str(row.get("answer_kr", "")).strip()

    st.markdown(f"**[상황: {scene}]**")
    if partner_jp:
        st.markdown(f"### {partner_jp}")
    if situation_kr:
        st.caption(f"👉 {situation_kr}")

    # 🔊 발음(현행 유지): PRO만 노출 (구현은 이후 교체)
    if (user_plan or "free") != "free":
        with st.expander("🔊 발음 듣기", expanded=False):
            st.write("문제:", partner_jp)
    else:
        st.caption("※ 발음 듣기는 PRO 플랜에서 제공됩니다.")

    # 보기: 문제당 1회 생성(고정)
    qkey = f"talk_choices_{st.session_state['talk_tag']}_{idx}_{partner_jp}"
    if qkey not in st.session_state:
        rnd_state = random.getstate()
        random.seed(f"{st.session_state['talk_tag']}-{idx}-{partner_jp}")
        st.session_state[qkey] = build_choices(dfv, row)
        random.setstate(rnd_state)

    choices = st.session_state[qkey]
    pick = st.radio("보기", choices, index=None, key=f"talk_pick_{st.session_state['talk_tag']}_{idx}")

    if st.button("정답 제출", use_container_width=True):
        if pick == answer_jp:
            st.success("정답입니다!")
            st.markdown("**이런 답이 맞아요:** 상대가 이해했는지 확인했기 때문에, 이해가 안 됐으면 정중하게 다시 설명을 요청하는 게 자연스럽습니다.")
        else:
            st.error("오답입니다.")
            st.markdown(f"**정답:** {answer_jp}")

        if hint_kr:
            st.caption(hint_kr)
        if answer_kr:
            st.caption(f"정답 해석: {answer_kr}")

        # 제출 후 발음(현행 유지): PRO만 노출
        if (user_plan or "free") != "free":
            st.markdown("#### 🔊 제출 후 발음")
            c1, c2 = st.columns(2)
            with c1:
                st.write("문제")
                st.write(partner_jp)
            with c2:
                st.write("정답")
                st.write(answer_jp)

    if st.button("다음 문제", use_container_width=True):
        st.session_state["talk_idx"] += 1
        st.rerun()


if __name__ == "__main__":
    render_talk_page(st.session_state.get("user_plan", "free"))
