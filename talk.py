
import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="centered")

st.title("회화 훈련")

# Load CSV
df = pd.read_csv("talk.csv")

if "talk_idx" not in st.session_state:
    st.session_state.talk_idx = 0

row = df.iloc[st.session_state.talk_idx % len(df)]

st.markdown(f"### [상황: {row.get('scene','일상')}]")
st.markdown(f"**{row['prompt_jp']}**")

# 보기 구성
def build_choices(df, row):
    correct = row["answer_jp"]
    unrelated_pool = [
        "明日は雨です。",
        "コーヒーをください。",
        "駅はどこですか。",
        "今日は暑いですね。"
    ]
    opposite = "はい、わかりました。"
    mismatch = random.choice(df[df.index != row.name]["answer_jp"].tolist())
    unrelated = random.choice(unrelated_pool)
    choices = [correct, opposite, mismatch, unrelated]
    random.shuffle(choices)
    return choices

key = f"choices_{st.session_state.talk_idx}"
if key not in st.session_state:
    st.session_state[key] = build_choices(df, row)

choice = st.radio("보기", st.session_state[key], index=None)

if st.button("정답 제출"):
    if choice == row["answer_jp"]:
        st.success("정답입니다!")
    else:
        st.error("오답입니다.")
        st.markdown(f"정답: {row['answer_jp']}")

    st.markdown("### 🔊 발음 듣기")
    st.write("문제:", row["prompt_jp"])
    st.write("정답:", row["answer_jp"])

if st.button("다음 문제"):
    st.session_state.talk_idx += 1
    st.rerun()
