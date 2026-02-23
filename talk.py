# talk.py (v10) - Hotena 회화 훈련 안정판
from __future__ import annotations
import json, random
from pathlib import Path
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

CSV_CANDIDATES = [
    BASE_DIR / "talk_situations.csv",
    BASE_DIR / "talk.csv",
    BASE_DIR / "data" / "talk_situations.csv",
    BASE_DIR / "data" / "talk.csv",
]

def find_csv():
    for p in CSV_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("talk_situations.csv 또는 talk.csv를 찾을 수 없습니다.")

def _norm(c):
    return str(c).replace("\ufeff","").strip()

@st.cache_data(show_spinner=False)
def load_csv(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [_norm(c) for c in df.columns]

    required = ["qid","level","tag","partner_jp","answer_jp","d1_jp","d2_jp","d3_jp"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")

    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).fillna("").str.strip()

    df["level"] = df["level"].str.lower().str.replace(" ","")
    df["tag"] = df["tag"].str.strip()

    return df

def get_fixed_options(qid, answer, d1, d2, d3):
    key = f"_opts_{qid}"
    if key in st.session_state:
        return st.session_state[key]

    opts = [answer,d1,d2,d3]
    seed = f"{qid}_seed"
    rng = random.Random(seed)
    rng.shuffle(opts)

    st.session_state[key] = opts
    return opts

def render():
    path = find_csv()
    df = load_csv(path)

    st.title("💬 회화 훈련")

    mode_map = {"business":"비즈니스","real":"실전"}
    tag_map = {"daily":"일상","travel":"여행","food":"식당","business":"비즈니스"}

    if "mode" in df.columns:
        modes = sorted(df["mode"].unique())
        mode_label = st.selectbox("모드",[mode_map.get(m,m) for m in modes])
        mode = [k for k,v in mode_map.items() if v==mode_label]
        if mode:
            df = df[df["mode"]==mode[0]]

    tags = sorted(df["tag"].unique())
    tag_label = st.selectbox("상황",[tag_map.get(t,t) for t in tags])
    tag = [k for k,v in tag_map.items() if v==tag_label]
    if tag:
        df = df[df["tag"]==tag[0]]

    levels = sorted(df["level"].unique())
    level_label = st.selectbox("레벨",[l.upper() for l in levels])
    df = df[df["level"]==level_label.lower()]

    if df.empty:
        st.error("해당 조건의 회화 문제가 없습니다.")
        return

    idx = st.session_state.get("talk_idx",0)
    row = df.iloc[idx]

    st.subheader(row["partner_jp"])

    options = get_fixed_options(row["qid"],row["answer_jp"],row["d1_jp"],row["d2_jp"],row["d3_jp"])
    choice = st.radio("정답을 고르세요",options)

    if st.button("정답 확인"):
        if choice==row["answer_jp"]:
            st.success("✅ 정답입니다.")
        else:
            st.error("❌ 오답입니다.")
            st.write("정답:",row["answer_jp"])

if __name__ == "__main__":
    render()
