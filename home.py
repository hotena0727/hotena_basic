# ============================================================
# ✅ 왕초보 탈출 하테나일본어 - V39 (안정 + 회화 데이터 확장)
# - HOME: 탑메뉴 없음 / 버튼 이동
# - TRAIN: 상단 탭 + 플랜(좌측) / 10문제 세트
# - TALK: 1문제씩 + 보기 4종(정답/의도반대/단계불일치/무관)
# - 발음: PRO만
# ============================================================
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import altair as alt
except Exception:
    alt = None

APP_TITLE = "왕초보 탈출 하테나일본어"
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

if "_page_config_set" not in st.session_state:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.session_state["_page_config_set"] = True

st.markdown(
    """
<style>
:root{
  --navy:#1c2a3a;
  --muted:#6b7280;
  --bg:#f5f7fa;
  --card:#ffffff;
  --line:#e5e7eb;
  --sky:#7dd3fc;
  --pink:#f9a8d4;
  --mint:#86efac;
  --violet:#c4b5fd;
  --amber:#fcd34d;
}
.block-container{ padding-top: 1.05rem; padding-bottom: 2.6rem; }
.stApp{ background: var(--bg); }
.h-card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px;box-shadow:0 2px 12px rgba(17,24,39,0.045);}
.h-topbar{background:rgba(255,255,255,0.93);border:1px solid var(--line);border-radius:18px;padding:10px 12px;box-shadow:0 2px 14px rgba(17,24,39,0.055);}
.h-plan{display:inline-block;padding:6px 10px;border-radius:999px;border:1px solid rgba(28,42,58,0.14);background:rgba(134,239,172,0.18);color:var(--navy);font-weight:800;font-size:13px;}
.h-muted{color:var(--muted);font-size:13px;}
.h-title{font-size:20px;font-weight:950;color:var(--navy);}
.h-sub{color:var(--muted);font-size:13px;margin-top:-4px;}
.h-chip{display:inline-block;padding:6px 10px;border-radius:999px;border:1px solid rgba(28,42,58,0.12);background:rgba(125,211,252,0.14);color:var(--navy);font-weight:800;font-size:13px;}
.stButton>button{border-radius:14px;border:1px solid rgba(28,42,58,0.15);background:white;}
.stButton>button:hover{background:rgba(249,168,212,0.13);}
</style>
""",
    unsafe_allow_html=True,
)

TZ_OFFSET_HOURS = 9  # Asia/Seoul (간단)

def today_seoul() -> str:
    return (datetime.utcnow() + timedelta(hours=TZ_OFFSET_HOURS)).strftime("%Y-%m-%d")

def get_plan() -> str:
    p = st.session_state.get("plan")
    if p in ("free", "pro"):
        return p
    try:
        p2 = str(st.secrets.get("PLAN", "")).strip().lower()
        if p2 in ("free", "pro"):
            st.session_state["plan"] = p2
            return p2
    except Exception:
        pass
    st.session_state["plan"] = "free"
    return "free"

def set_view(v: str):
    st.session_state["view"] = v
    st.rerun()

def init_meta():
    if "meta" not in st.session_state:
        st.session_state["meta"] = {
            "day": today_seoul(),
            "streak": 1,
            "today": {"WORD": [], "KANJI": [], "TALK": []},
            "history": [],
        }
    meta = st.session_state["meta"]
    d = today_seoul()
    if meta.get("day") != d:
        meta["day"] = d
        meta["today"] = {"WORD": [], "KANJI": [], "TALK": []}

def log_attempt(mode: str, score: int, total: int):
    init_meta()
    meta = st.session_state["meta"]
    rec = {"day": meta["day"], "mode": mode, "score": score, "total": total}
    meta["today"][mode].append(rec)
    meta["history"].append(rec)

def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, encoding="utf-8")

def section_header(title: str, subtitle: str | None = None):
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="h-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="h-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def daily_report():
    init_meta()
    meta = st.session_state["meta"]
    def _acc(mode):
        items = meta["today"][mode]
        if not items:
            return (0, None)
        s = sum(i["score"] for i in items)
        t = sum(i["total"] for i in items)
        return (len(items), None if t == 0 else (s/t*100.0))
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown("**오늘의 학습 리포트**")
    cols = st.columns(3)
    for i, (label, mode) in enumerate([("단어","WORD"),("한자","KANJI"),("회화","TALK")]):
        sets, acc = _acc(mode)
        with cols[i]:
            st.markdown(f"**{label}**")
            st.markdown(f"{sets} 세트 · " + ("-" if acc is None else f"{acc:.0f}%"))
    st.markdown('<div class="h-muted">하루 기준으로 자동 집계돼요.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def last_7_days():
    init_meta()
    meta = st.session_state["meta"]
    today = datetime.strptime(meta["day"], "%Y-%m-%d")
    keys = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6,-1,-1)]
    labels = [(today - timedelta(days=i)).strftime("%m/%d") for i in range(6,-1,-1)]
    counts = {k:0 for k in keys}
    for r in meta["history"]:
        if r["day"] in counts:
            counts[r["day"]] += 1
    return [{"date": labels[i], "count": counts[keys[i]]} for i in range(7)]

def render_7day_chart():
    rows = last_7_days()
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown("**최근 7일 학습 흐름**")
    if alt is None:
        st.caption("  ".join([f"{r['date']}:{r['count']}" for r in rows]))
    else:
        df = pd.DataFrame(rows)
        ch = (alt.Chart(df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
              .encode(x=alt.X("date:N", title=None, axis=alt.Axis(labelAngle=0)),
                      y=alt.Y("count:Q", title=None),
                      tooltip=["date:N","count:Q"])
              .properties(height=140)
              .configure_view(strokeWidth=0)
              .configure_axis(grid=False))
        st.altair_chart(ch, use_container_width=True)
    st.markdown('<div class="h-muted">오늘은 “한 세트”면 충분해요.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def tts_button(text: str, key: str):
    if get_plan() != "pro":
        st.button("🔒 발음(프로)", disabled=True, key=key+"_lock")
        return
    safe = str(text).replace("\\", "\\\\").replace('"', '\\"')
    html = f"""
    <button style="width:100%;padding:10px 12px;border-radius:14px;border:1px solid rgba(28,42,58,0.16);background:white;cursor:pointer;font-weight:800;color:#1c2a3a;"
    onclick='try{{const u=new SpeechSynthesisUtterance("{safe}");u.lang="ja-JP";u.rate=0.95;u.pitch=1.05;window.speechSynthesis.cancel();window.speechSynthesis.speak(u);}}catch(e){{}}'>
    🔊 발음 듣기</button>
    """
    st.components.v1.html(html, height=56)

def top_nav(active: str):
    plan = get_plan().upper()
    st.markdown('<div class="h-topbar">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 8])
    with c1:
        st.markdown(f'<span class="h-plan">{plan}</span>', unsafe_allow_html=True)
    with c2:
        cols = st.columns(4)
        for i, (label, v) in enumerate([("단어","WORD"),("한자","KANJI"),("회화","TALK"),("마이페이지","MYPAGE")]):
            with cols[i]:
                if st.button(label, use_container_width=True, key=f"top_{v}"):
                    set_view(v)
    st.markdown("</div>", unsafe_allow_html=True)

def home():
    section_header(APP_TITLE, "오늘도 가볍게 한 걸음.")
    daily_report()
    render_7day_chart()
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown("**훈련 선택**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("단어", use_container_width=True, key="go_word"):
            for k in ["word_set","word_ans","word_submitted"]:
                st.session_state.pop(k, None)
            set_view("WORD")
    with c2:
        if st.button("한자", use_container_width=True, key="go_kanji"):
            for k in ["kanji_set","kanji_ans","kanji_submitted","kanji_level"]:
                st.session_state.pop(k, None)
            set_view("KANJI")
    with c3:
        if st.button("회화", use_container_width=True, key="go_talk"):
            for k in ["talk_set","talk_choices","talk_selected","talk_submitted","talk_i","talk_scene"]:
                st.session_state.pop(k, None)
            set_view("TALK")
    with c4:
        if st.button("마이페이지", use_container_width=True, key="go_mypage"):
            set_view("MYPAGE")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- WORD ----------------
def word_new_set():
    df = load_csv("words.csv")
    qs = df.sample(n=min(10, len(df)), random_state=random.randint(0, 10**9)).to_dict("records")
    st.session_state["word_set"] = qs
    st.session_state["word_ans"] = {}
    st.session_state["word_submitted"] = False

def word():
    top_nav("WORD")
    section_header("단어 훈련", "10문제 한 세트.")
    daily_report()
    if "word_set" not in st.session_state:
        word_new_set()
    qs = st.session_state["word_set"]
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    for idx, q in enumerate(qs, start=1):
        qid = q["id"]
        choices = str(q["choices"]).split("|")
        sel = st.radio(f"{idx}. {q['jp']}", choices, index=None, key=f"w_{qid}")
        st.session_state["word_ans"][qid] = sel
        st.markdown("---")
    st.markdown("</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("정답 제출", use_container_width=True, key="w_submit"):
            st.session_state["word_submitted"] = True
    with c2:
        if st.button("새 세트", use_container_width=True, key="w_new"):
            word_new_set()
            st.rerun()
    if st.session_state.get("word_submitted"):
        score = 0
        wrong = []
        for q in qs:
            sel = st.session_state["word_ans"].get(q["id"])
            if sel == q["answer"]:
                score += 1
            else:
                wrong.append((q["jp"], sel, q["answer"]))
        log_attempt("WORD", score, len(qs))
        st.markdown('<div class="h-card">', unsafe_allow_html=True)
        st.markdown(f"**결과** · {score}/{len(qs)}")
        for jp, s, a in wrong[:6]:
            st.markdown(f"- {jp} → 내 답: {s} / 정답: **{a}**")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- KANJI ----------------
def kanji_new_set(level: str):
    df = load_csv("kanji.csv")
    df = df[df["level"] == level]
    qs = df.sample(n=min(10, len(df)), random_state=random.randint(0, 10**9)).to_dict("records")
    st.session_state["kanji_level"] = level
    st.session_state["kanji_set"] = qs
    st.session_state["kanji_ans"] = {}
    st.session_state["kanji_submitted"] = False

def kanji():
    top_nav("KANJI")
    section_header("한자 훈련", "N5~N3 (쉬운 N3)")
    daily_report()
    level = st.session_state.get("kanji_level", "N5")
    level = st.radio("레벨", ["N5","N4","N3"], index=["N5","N4","N3"].index(level), horizontal=True, key="k_level")
    if ("kanji_set" not in st.session_state) or (st.session_state.get("kanji_level") != level):
        kanji_new_set(level)
    qs = st.session_state["kanji_set"]
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    for idx, q in enumerate(qs, start=1):
        qid = q["id"]
        choices = str(q["choices"]).split("|")
        sel = st.radio(f"{idx}. {q['word']}", choices, index=None, key=f"k_{qid}")
        st.session_state["kanji_ans"][qid] = sel
        st.markdown("---")
    st.markdown("</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("정답 제출", use_container_width=True, key="k_submit"):
            st.session_state["kanji_submitted"] = True
    with c2:
        if st.button("새 세트", use_container_width=True, key="k_new"):
            kanji_new_set(level)
            st.rerun()
    if st.session_state.get("kanji_submitted"):
        score = 0
        wrong = []
        for q in qs:
            sel = st.session_state["kanji_ans"].get(q["id"])
            if sel == q["answer"]:
                score += 1
            else:
                wrong.append((q["word"], sel, q["answer"]))
        log_attempt("KANJI", score, len(qs))
        st.markdown('<div class="h-card">', unsafe_allow_html=True)
        st.markdown(f"**결과** · {score}/{len(qs)}")
        for w, s, a in wrong[:6]:
            st.markdown(f"- {w} → 내 답: {s} / 정답: **{a}**")
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- TALK ----------------
UNRELATED_POOL = [
    "明日は雨です。","コーヒーをください。","駅はどこですか。","今日は暑いですね。",
    "すみません、トイレはありますか。","これ、いくらですか。","今、時間がありますか。","大丈夫です。"
]
OPPOSITE_BY_INTENT = {
    "ask_repeat":"はい、わかりました。",
    "confirm_ok":"すみません、もう一度説明していただけますか。",
    "request":"結構です。",
    "apologize":"気にしません。",
    "thanks":"いえ、結構です。",
    "refuse":"はい、お願いします。",
    "confirm":"大丈夫です。",
}

def talk_new_set(scene: str):
    df = load_csv("talk.csv")
    if scene != "전체":
        df = df[df["scene"] == scene]
    qs = df.sample(n=min(10, len(df)), random_state=random.randint(0, 10**9)).to_dict("records")
    st.session_state["talk_scene"] = scene
    st.session_state["talk_set"] = qs
    st.session_state["talk_i"] = 0
    st.session_state["talk_choices"] = {}
    st.session_state["talk_selected"] = {}
    st.session_state["talk_submitted"] = {}

def build_choices(df_all: pd.DataFrame, row: dict) -> list[str]:
    # 정답
    correct = str(row["answer_jp"])

    # 의미 반대(의도 반대)
    intent = str(row.get("intent","")).strip()
    opposite = OPPOSITE_BY_INTENT.get(intent) or "はい、わかりました。"

    # 단계 불일치: 같은 scene지만 intent가 다른 답(또는 레벨 다른 답)
    scene = str(row.get("scene","")).strip()
    level = str(row.get("level","")).strip()
    cand = df_all[(df_all["scene"] == scene) & ((df_all["intent"] != intent) | (df_all["level"] != level))]
    if len(cand) == 0:
        cand = df_all[df_all["intent"] != intent]
    mismatch = str(cand.sample(1).iloc[0]["answer_jp"]) if len(cand) else random.choice(UNRELATED_POOL)

    # 완전 무관
    unrelated = random.choice(UNRELATED_POOL)

    # 중복 제거 + 4개 채우기
    opts = []
    for o in [correct, opposite, mismatch, unrelated]:
        if o not in opts:
            opts.append(o)
    while len(opts) < 4:
        x = random.choice(UNRELATED_POOL)
        if x not in opts:
            opts.append(x)

    random.shuffle(opts)  # 보기 순서는 문항 생성 시 1번만 섞고 고정
    return opts[:4]

def talk():
    top_nav("TALK")
    section_header("회화 훈련", "1문제씩, 10문제 한 세트.")
    daily_report()
    df_all = load_csv("talk.csv")
    scenes = ["전체"] + sorted(df_all["scene"].dropna().unique().tolist())
    scene = st.session_state.get("talk_scene", "회사")
    if scene not in scenes:
        scene = scenes[1] if len(scenes) > 1 else "전체"
    scene = st.radio("상황", scenes, index=scenes.index(scene), horizontal=True, key="t_scene")
    if ("talk_set" not in st.session_state) or (st.session_state.get("talk_scene") != scene):
        talk_new_set(scene)

    qs = st.session_state["talk_set"]
    i = st.session_state.get("talk_i", 0)
    i = max(0, min(i, len(qs)-1))
    row = qs[i]
    qid = str(row["id"])

    # 보기 고정 (문항별 1회 생성)
    if qid not in st.session_state["talk_choices"]:
        st.session_state["talk_choices"][qid] = build_choices(df_all, row)
    choices = st.session_state["talk_choices"][qid]

    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown(f"**[상황: {row['scene']}]**")
    st.markdown(f"### {row['prompt_jp']}")
    tts_button(row["prompt_jp"], key=f"tq_{qid}")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    sel = st.radio("보기", choices, index=None, key=f"ts_{qid}")
    st.session_state["talk_selected"][qid] = sel
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("정답 제출", use_container_width=True, key=f"t_submit_{qid}"):
            st.session_state["talk_submitted"][qid] = True
    with c2:
        if st.button("이전", use_container_width=True, disabled=(i==0), key=f"t_prev_{qid}"):
            st.session_state["talk_i"] = i-1
            st.rerun()
    with c3:
        if st.button("다음", use_container_width=True, disabled=(i==len(qs)-1), key=f"t_next_{qid}"):
            st.session_state["talk_i"] = i+1
            st.rerun()

    if st.session_state["talk_submitted"].get(qid):
        correct = str(row["answer_jp"])
        ok = (sel == correct)
        st.markdown('<div class="h-card">', unsafe_allow_html=True)
        st.markdown("**피드백**")
        st.markdown("✅ 좋아요. 이 답이 가장 자연스럽습니다." if ok else "❗ 아쉬워요. ‘의도’가 맞는지 먼저 확인해 보세요.")
        st.markdown("---")
        st.markdown("**상대 스크립트**")
        st.markdown(row["prompt_jp"])
        tts_button(row["prompt_jp"], key=f"tq2_{qid}")
        st.markdown("---")
        st.markdown("**정답 스크립트**")
        st.markdown(f"**{correct}**")
        tts_button(correct, key=f"ta_{qid}")
        kr = str(row.get("answer_kr","")).strip()
        if kr:
            st.markdown(f"<div class='h-muted'>{kr}</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**납득 포인트**")
        st.markdown("- 정답은 ‘상황’과 ‘의도’가 정확히 맞습니다.")
        st.markdown("- 나머지 보기는 의도 반대/단계 불일치/주제 무관으로 구성돼요.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 세트 완료 체크
    if len(st.session_state["talk_submitted"]) == len(qs):
        score = 0
        for rr in qs:
            qid2 = str(rr["id"])
            if st.session_state["talk_selected"].get(qid2) == str(rr["answer_jp"]):
                score += 1
        log_attempt("TALK", score, len(qs))
        st.markdown('<div class="h-card">', unsafe_allow_html=True)
        st.markdown(f"**세트 완료** · {score}/{len(qs)}")
        if st.button("새 세트", use_container_width=True, key="t_newset"):
            talk_new_set(scene)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- MYPAGE ----------------
def mypage():
    top_nav("MYPAGE")
    init_meta()
    meta = st.session_state["meta"]
    section_header("마이페이지", "내 학습 흐름을 한눈에.")
    st.markdown('<div class="h-card">', unsafe_allow_html=True)
    st.markdown(f"**연속 학습** · {meta.get('streak',1)}일")
    st.markdown(f"**총 기록** · {len(meta.get('history',[]))}건")
    st.markdown("</div>", unsafe_allow_html=True)
    render_7day_chart()
    with st.expander("상세 기록(표) 보기"):
        st.dataframe(pd.DataFrame(meta.get("history", [])), use_container_width=True, hide_index=True)

def main():
    init_meta()
    if "view" not in st.session_state:
        st.session_state["view"] = "HOME"
    v = st.session_state["view"]
    if v == "HOME":
        home()
    elif v == "WORD":
        word()
    elif v == "KANJI":
        kanji()
    elif v == "TALK":
        talk()
    elif v == "MYPAGE":
        mypage()
    else:
        st.session_state["view"] = "HOME"
        st.rerun()

main()
