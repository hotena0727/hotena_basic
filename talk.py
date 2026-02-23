# talk.py (v9) - Hotena 회화 훈련 CSV 스키마 확정판
# - talk_situations.csv(선우님 업로드 스키마) 우선 지원
# - CSV 경로 자동 탐색 + 로드한 경로/컬럼 디버그 표시
# - 보기(4지선다) 순서가 클릭/리런마다 바뀌지 않게 qid별로 고정

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# =========================
# CSV 탐색
# =========================
BASE_DIR = Path(__file__).resolve().parent

CSV_CANDIDATES = [
    BASE_DIR / "talk_situations.csv",
    BASE_DIR / "talk.csv",
    BASE_DIR / "data" / "talk_situations.csv",
    BASE_DIR / "data" / "talk.csv",
]

def find_csv() -> Path:
    for p in CSV_CANDIDATES:
        if p.exists() and p.is_file():
            return p
    # 마지막 수단: 현재 폴더의 csv 중 talk 포함 파일
    for p in BASE_DIR.glob("*.csv"):
        if "talk" in p.name.lower():
            return p
    raise FileNotFoundError(
        "회화 CSV를 찾을 수 없습니다. "
        "talk_situations.csv 또는 talk.csv를 hotena_basic 폴더(또는 data/)에 넣어주세요."
    )

# =========================
# CSV 로드/정규화
# =========================
REQUIRED = [
    "qid",
    "level",
    "tag",
    "partner_jp",
    "answer_jp",
    "d1_jp",
    "d2_jp",
    "d3_jp",
]
OPTIONAL = ["situation_kr", "partner_kr", "answer_kr", "hint_kr", "mode", "section", "stage"]

def _norm_col(c: str) -> str:
    return str(c).replace("\ufeff", "").strip()

@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [_norm_col(c) for c in df.columns]

    # alias 흡수 (혹시 다른 이름으로 들어온 경우)
    alias = {
        "id": "qid",
        "q_id": "qid",
        "difficulty": "level",
        "category": "tag",
        "topic": "tag",
        "type": "tag",
        "question_jp": "partner_jp",
        "prompt_jp": "partner_jp",
        "answer": "answer_jp",
        "correct_jp": "answer_jp",
    }
    cols_by_lower = {c.lower(): c for c in df.columns}
    for src, dst in alias.items():
        if src in cols_by_lower and dst not in df.columns:
            df.rename(columns={cols_by_lower[src]: dst}, inplace=True)

    # 필수 컬럼 체크
    for c in REQUIRED:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")

    # 문자열 정리
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).fillna("").str.strip().replace({"nan": "", "NaN": "", "None": ""})

    # 정규화(필터용): 내부값은 소문자/공백제거로 통일
    df["level"] = df["level"].astype(str).str.strip().str.lower().str.replace(" ", "")
    # level 표준화: n4 / n3 / n2 형태로 맞춤
    df["level"] = df["level"].replace({
        "4": "n4", "n4": "n4", "jlptn4": "n4", "n-4": "n4", "n_4": "n4",
        "3": "n3", "n3": "n3", "jlptn3": "n3", "n-3": "n3", "n_3": "n3",
        "2": "n2", "n2": "n2", "jlptn2": "n2", "n-2": "n2", "n_2": "n2",
    })
    df["tag"] = df["tag"].astype(str).str.strip().str.lower()
    if "mode" in df.columns:
        df["mode"] = df["mode"].astype(str).str.strip().str.lower()
    if "section" in df.columns:
        df["section"] = df["section"].astype(str).str.strip().str.lower()

    # qid 중복 방지
    if df["qid"].duplicated().any():
        seen: Dict[str, int] = {}
        fixed = []
        for q in df["qid"].tolist():
            n = seen.get(q, 0)
            seen[q] = n + 1
            fixed.append(f"{q}_{n+1}" if n else q)
        df["qid"] = fixed

    return df

# =========================
# 보기 순서 고정(핵심)
# =========================
def get_fixed_options(qid: str, answer: str, d1: str, d2: str, d3: str) -> List[str]:
    """
    qid별로 보기 순서를 session_state에 고정 저장.
    - 같은 문제(qid)는 rerun/클릭해도 보기 순서가 절대 바뀌지 않음.
    - 다른 문제는 다른 셔플.
    """
    key = f"_talk_opts_{qid}"
    if key in st.session_state:
        return st.session_state[key]

    opts = [answer, d1, d2, d3]
    # 보기 중복 제거(혹시 데이터가 겹치면) → 그래도 4개 맞추기 위해 fallback
    uniq = []
    for x in opts:
        x = (x or "").strip()
        if x and x not in uniq:
            uniq.append(x)
    while len(uniq) < 4:
        uniq.append("（該当なし）")

    # 셔플 시드: 세션 시드 + qid
    if "_talk_seed" not in st.session_state:
        st.session_state["_talk_seed"] = random.randint(1, 10_000_000)
    seed = f"{st.session_state['_talk_seed']}::{qid}"
    rng = random.Random(seed)
    rng.shuffle(uniq)

    st.session_state[key] = uniq
    return uniq


# =========================
# Web Speech TTS (브라우저)
# =========================
def tts_button(text: str, label: str, key: str, rate: float = 1.0, pitch: float = 1.0, lang: str = "ja-JP"):
    """브라우저 내장 TTS(speechSynthesis) 버튼.
    - Streamlit 서버에 외부 API키 없이 동작
    - 사용자의 브라우저/OS 음성에 따라 품질 차이가 있습니다.
    """
    safe_text = (text or "").strip()
    if not safe_text:
        return
    btn_id = f"tts_{key}"
    html = f"""
<div style='display:inline-block;margin-right:8px'>
  <button id='{btn_id}' style='padding:6px 10px;border-radius:10px;border:1px solid rgba(0,0,0,.15);background:rgba(0,0,0,.02);cursor:pointer'>
    {label}
  </button>
</div>
<script>
(function(){{
  const btn = document.getElementById({json.dumps(btn_id)});
  if(!btn) return;
  btn.onclick = function(){{
    try{{
      const text = {json.dumps(safe_text)};
      const RATE = {json.dumps(float(rate))};
      const PITCH = {json.dumps(float(pitch))};
      const LANG = {json.dumps(lang)};
      const u = new SpeechSynthesisUtterance(text);
      u.lang = LANG;
      u.rate = RATE;
      u.pitch = PITCH;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }} catch(e) {{ console.log(e); }}
  }};
}})();
</script>
"""
    components.html(html, height=40, scrolling=False)

# =========================
# UI
# =========================
def _inject_jp_font():
    st.markdown(
        """
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root { --jp-font: "Noto Sans JP","Yu Gothic","Hiragino Kaku Gothic ProN","Meiryo",sans-serif; }
html, body, [class*="css"], .stApp { font-family: var(--jp-font) !important; }
</style>
""",
        unsafe_allow_html=True,
    )
# =========================
# 표시 라벨(한글) 매핑
# =========================
MODE_LABEL = {
    "business": "비즈니스",
    "real": "실전",
}
TAG_LABEL = {
    "daily": "일상",
    "travel": "여행",
    "food": "식당",
    "call": "전화",
    "business": "비즈니스",
    "general": "전체",
}
SECTION_LABEL = {
    "jobprep": "취업 준비",
    "interview": "면접",
    "newcomer": "신입 대응",
    "office": "직장 기본",
}

def _label(d: dict, v: str) -> str:
    v = (v or "").strip().lower()
    return d.get(v, v)

def _level_label(lv: str) -> str:
    lv = (lv or "").strip().lower()
    if lv.startswith("n") and len(lv) >= 2:
        return lv.upper()
    return lv.upper()
)

def render():
    _inject_jp_font()

    csv_path = find_csv()
    df = load_csv(csv_path)

    # 디버그(필요 시)
    with st.expander("🔎 회화 CSV 로드 정보(문제 발생 시 확인)", expanded=False):
        st.write("읽은 파일:", str(csv_path))
        st.write("컬럼:", list(df.columns))
        st.write("행 수:", len(df))

    st.title("💬 회화 훈련")

    # mode/section 있으면 활용
    has_mode = "mode" in df.columns
    has_section = "section" in df.columns

    if has_mode:
        modes = sorted(df["mode"].dropna().unique().tolist())
        mode_label = st.selectbox("모드", [ _label(MODE_LABEL, m) for m in modes ])
        # 역매핑
        mode = None
        for m in modes:
            if _label(MODE_LABEL, m) == mode_label:
                mode = m
                break
        df_m = df[df["mode"] == mode].copy() if mode else df.copy()
    else:
        mode = None
        df_m = df

    # tag
    tags = sorted(df_m["tag"].dropna().unique().tolist())
    tag_label = st.selectbox("상황", [ _label(TAG_LABEL, t) for t in tags ]) if tags else _label(TAG_LABEL, "general")
    tag = None
    for t in tags:
        if _label(TAG_LABEL, t) == tag_label:
            tag = t
            break
    if not tag:
        tag = "general"
    df_t = df_m[df_m["tag"] == tag].copy()

    # business일 때 section 필터(있으면)
    section = None
    if has_section and (mode == "business" or tag.lower() == "business"):
        secs = sorted([s for s in df_t["section"].dropna().unique().tolist() if s])
        if secs:
            section_label = st.selectbox("비즈니스 섹션", ["전체"] + [ _label(SECTION_LABEL, s) for s in secs ])
            section = None
            if section_label != "전체":
                for s in secs:
                    if _label(SECTION_LABEL, s) == section_label:
                        section = s
                        break
            if section:
                df_t = df_t[df_t["section"] == section].copy()

    # level 옵션은 현재 필터 결과 기준으로만
    levels = sorted(df_t["level"].dropna().unique().tolist())
    if not levels:
        st.error("해당 조건의 회화 문제가 없습니다. (CSV의 mode/tag/section/level 확인)")
        return
    level_label = st.selectbox("레벨", [ _level_label(lv) for lv in levels ])
    level = None
    for lv in levels:
        if _level_label(lv) == level_label:
            level = lv
            break
    if not level:
        level = levels[0]
    df_l = df_t[df_t["level"] == level].copy()

    if df_l.empty:
        st.error("해당 조건의 회화 문제가 없습니다. (CSV의 tag/level 확인)")
        return

    # 문제 선택
    qids = df_l["qid"].tolist()
    if "talk_idx" not in st.session_state:
        st.session_state["talk_idx"] = 0

    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("⬅️ 이전"):
            st.session_state["talk_idx"] = (st.session_state["talk_idx"] - 1) % len(qids)
    with col_next:
        if st.button("➡️ 다음"):
            st.session_state["talk_idx"] = (st.session_state["talk_idx"] + 1) % len(qids)

    cur_qid = qids[st.session_state["talk_idx"]]
    row = df_l[df_l["qid"] == cur_qid].iloc[0]

    # 표시
    if "situation_kr" in row and str(row.get("situation_kr", "")).strip():
        st.caption(f"상황: {row.get('situation_kr','')}")
    partner_text = str(row.get("partner_jp", ""))
    st.subheader(partner_text)

    # 🔊 발음 (브라우저 TTS)
    c1, c2 = st.columns([1,1])
    with c1:
        tts_button(partner_text, "🔊 질문 듣기", key=f"{cur_qid}_q", rate=1.0)
    with c2:
        # 정답은 제출 후에도 버튼이 보이도록 미리 준비
        tts_button(str(row.get("answer_jp","")), "🔊 정답 듣기", key=f"{cur_qid}_a", rate=1.0)


    if "hint_kr" in row and str(row.get("hint_kr", "")).strip():
        st.info(f"힌트: {row.get('hint_kr','')}")

    answer = str(row.get("answer_jp", "")).strip()
    d1 = str(row.get("d1_jp", "")).strip()
    d2 = str(row.get("d2_jp", "")).strip()
    d3 = str(row.get("d3_jp", "")).strip()

    options = get_fixed_options(cur_qid, answer, d1, d2, d3)

    # 선택(보기 순서 고정)
    pick_key = f"_talk_pick_{cur_qid}"
    picked = st.radio("정답을 고르세요", options, key=pick_key)

    if st.button("정답 확인"):
        if picked == answer:
            st.success("✅ 정답입니다.")
        else:
            st.error("❌ 오답입니다.")
            st.write("정답:", answer)

        if "answer_kr" in row and str(row.get("answer_kr","")).strip():
            st.caption(f"해석: {row.get('answer_kr','')}")

# 모듈로 import될 때를 대비
if __name__ == "__main__":
    render()
