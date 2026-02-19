# talk.py
from __future__ import annotations

from pathlib import Path
import random
from datetime import datetime, date
import hashlib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ============================================================
# ✅ Namespace (session_state keys)
# ============================================================
NS = "talk"
QUIZ_LEN = 10

# ============================================================
# ✅ Session gate (공통 로그인은 home.py에서)
# ============================================================
if "user" not in st.session_state:
    st.warning("홈에서 로그인 후 이용해 주세요.")
    st.stop()

USER = st.session_state["user"]
USER_ID = USER.get("id") if isinstance(USER, dict) else None
USER_EMAIL = USER.get("email") if isinstance(USER, dict) else None

USER_PLAN = st.session_state.get("user_plan", "free")
IS_PRO = str(USER_PLAN).lower() == "pro"


st.title("회화 훈련 · 상황판단")
st.caption("상황 → 상대 발화(🔊) → 쌩뚱맞은 보기 속에서 정답 선택 → 제출 후 정답(🔊)")

# ============================================================
# ✅ Supabase client (hub 재사용)
# ============================================================
def _sb():
    sb = st.session_state.get("supabase")
    if sb is not None:
        return sb

    # fallback(단독 실행)
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
            df[c] = df[c].replace({"nan": "", "NaN": "", "None": ""})

    # 빈값 정리(실제 NaN도 제거)
    df = df.fillna("")

    # answer 없는 행 제거
    df = df[df["answer_jp"].astype(str).str.len() > 0].reset_index(drop=True)
    return df

try:
    DF = load_csv(CSV_PATH)
except Exception as e:
    st.error("talk_situations.csv 로딩 실패")
    st.code(repr(e))
    st.stop()

# ============================================================
# ✅ Tag 표시명(사용자 UI)
# ============================================================
TAG_LABELS = {
    "business": "비즈니스",
    "daily": "일상",
    "call": "전화/온라인",
    "interview": "면접",
    "travel": "여행",
    "shopping": "쇼핑",
    "food": "음식/카페",
    "emergency": "트러블/긴급",
}

def tag_to_label(tag: str) -> str:
    t = (tag or "").strip()
    return TAG_LABELS.get(t, t if t else "기타")

def label_to_tag(label: str, available_tags: list[str]) -> str:
    # label -> tag 역매핑
    for t in available_tags:
        if tag_to_label(t) == label:
            return t
    return ""

# ============================================================
# ✅ Helpers (progress 저장: profiles.progress["talk"])
# ============================================================
def ensure_progress():
    progress_all = st.session_state.get("progress_all") or {}
    talk = progress_all.get("talk") or {}
    talk.setdefault("mastered_ids", [])
    talk.setdefault("wrong_ids", [])
    talk.setdefault("attempts", 0)
    talk.setdefault("correct", 0)
    talk.setdefault("last_set", {})  # {"qids":[], "results":{qid:{...}}, "finished_at":""}
    progress_all["talk"] = talk
    st.session_state["progress_all"] = progress_all
    return progress_all, talk

def save_progress(progress_all: dict):
    if not USER_ID:
        return
    try:
        _sb().table("profiles").update({"progress": progress_all}).eq("id", USER_ID).execute()
    except Exception:
        pass

def log_attempt(level: str, tag: str, quiz_len: int, score: int, wrong_list: list[str]):
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
        _sb().table("quiz_attempts").insert(payload).execute()
    except Exception:
        pass

def build_choices(row: dict, pool_answers: list[str]) -> list[str]:
    ans = str(row["answer_jp"]).strip()
    distractors = []
    for k in ["d1_jp", "d2_jp", "d3_jp"]:
        v = str(row.get(k, "")).strip()
        if v and v.lower() != "nan":
            distractors.append(v)

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
    """SpeechSynthesis 버튼 (가능하면 parent window 사용)"""
    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    btns = []
    for label, text in items:
        btns.append(f'<button class="tts-btn" data-text="{esc(text)}" type="button">🔊 {esc(label)}</button>')

    return f"""
    <style>
      #tts_{block_id} {{
        display:flex;
        flex-wrap:wrap;
        gap:0.45rem;
        margin:0.25rem 0 0.25rem;
      }}
      #tts_{block_id} .tts-btn {{
        border: 1px solid rgba(49, 51, 63, 0.2);
        background: white;
        padding: 0.45rem 0.65rem;
        border-radius: 999px;
        cursor:pointer;
        font-size: 0.95rem;
      }}
    </style>
    <div id="tts_{block_id}">
      {''.join(btns)}
    </div>
    <script>
    (function() {{
      const root = document.getElementById("tts_{block_id}");
      if (!root) return;

      const win = (window.parent && window.parent.speechSynthesis) ? window.parent : window;

      function pickJaVoice() {{
        const voices = win.speechSynthesis.getVoices ? win.speechSynthesis.getVoices() : [];
        const ja = voices.filter(v => (v.lang || "").toLowerCase().startsWith("ja"));
        return ja.length ? ja[0] : null;
      }}

      function speak(text) {{
        try {{
          if (!text) return;
          const u = new win.SpeechSynthesisUtterance(text);
          u.lang = "ja-JP";
          const v = pickJaVoice();
          if (v) u.voice = v;
          win.speechSynthesis.cancel();
          win.speechSynthesis.speak(u);
        }} catch (e) {{}}
      }}

      root.querySelectorAll("button.tts-btn").forEach(btn => {{
        btn.addEventListener("click", () => {{
          const text = btn.getAttribute("data-text") || "";
          speak(text);
        }});
      }});
    }})();
    </script>
    """

def stable_daily_tip(user_id: str) -> str:
    tips = [
        "오늘은 10문제만! (루틴 유지가 이깁니다)",
        "정답이 티 나지 않게 보기들을 일부러 섞었습니다.",
        "틀려도 OK. ‘상황에 맞는 한마디’가 핵심이에요.",
    ]
    seed = f"{user_id}:{date.today().isoformat()}".encode("utf-8")
    idx = int(hashlib.sha256(seed).hexdigest()[:8], 16) % len(tips)
    return tips[idx]

# ============================================================
# ✅ 필터 UI (레벨/상황 태그)
# ============================================================
levels = sorted(DF["level"].astype(str).unique().tolist())

available_tags = sorted([t for t in DF.get("tag", pd.Series([""])).astype(str).unique().tolist() if t and t != "nan"])
tag_labels = ["전체"] + [tag_to_label(t) for t in available_tags]

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    sel_level = st.selectbox("레벨", levels, index=0, key="talk_level")
with c2:
    sel_tag_label = st.selectbox("상황", tag_labels, index=0, key="talk_tag_label")
with c3:
    exclude_mastered = st.toggle("정복 제외", value=True, key="talk_exclude_mastered")

sel_tag = "" if sel_tag_label == "전체" else label_to_tag(sel_tag_label, available_tags)

df2 = DF[DF["level"].astype(str) == str(sel_level)].copy()
if sel_tag and "tag" in df2.columns:
    df2 = df2[df2["tag"].astype(str) == str(sel_tag)].copy()

if len(df2) < 4:
    st.warning("이 조건에서는 문제가 너무 적습니다. (최소 4문항 이상 권장)")
    st.caption("상황을 ‘전체’로 바꾸거나 CSV 문항을 늘려주세요.")

st.info(stable_daily_tip(str(USER_ID or "guest")))

# ============================================================
# ✅ 세트(10문) 상태
# ============================================================
progress_all, talk = ensure_progress()
mastered_ids = set(talk.get("mastered_ids", []) or [])
wrong_ids = set(talk.get("wrong_ids", []) or [])

pool_df = df2
if exclude_mastered and mastered_ids:
    pool_df = pool_df[~pool_df["qid"].astype(str).isin(mastered_ids)]

if len(pool_df) == 0:
    st.warning("정복 제외로 인해 남은 문제가 없습니다. (정복 제외를 끄거나 정복 초기화가 필요)")
    # 정복 초기화 버튼
    if st.button("정복(맞힌 문제) 초기화", use_container_width=True):
        talk["mastered_ids"] = []
        progress_all["talk"] = talk
        save_progress(progress_all)
        st.success("초기화했습니다.")
        st.rerun()
    st.stop()

pool_answers = DF["answer_jp"].astype(str).fillna("").tolist()

def start_new_set():
    # cached choices clear (고정 보기용)
    for k in list(st.session_state.keys()):
        if k.startswith(f"{NS}_choices_"):
            st.session_state.pop(k, None)
    # 10문 뽑기(가능한 만큼)
    n = min(QUIZ_LEN, len(pool_df))
    sample = pool_df.sample(n=n, replace=False)
    qids = sample["qid"].astype(str).tolist()

    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = 0
    st.session_state[f"{NS}_results"] = {}  # qid -> {"selected":..., "correct":bool}
    st.session_state["talk_submitted"] = False
    st.session_state.pop("talk_choice", None)

# 세트가 없거나, 필터가 바뀌었으면 새로 시작
sig = f"{sel_level}|{sel_tag}|{int(exclude_mastered)}"
if st.session_state.get(f"{NS}_sig") != sig or f"{NS}_set_qids" not in st.session_state:
    st.session_state[f"{NS}_sig"] = sig
    start_new_set()

qids = st.session_state[f"{NS}_set_qids"]
idx = st.session_state[f"{NS}_idx"]
idx = max(0, min(idx, len(qids)))  # safety

# 세트 종료 처리
if idx >= len(qids):
    # 결과 집계
    results = st.session_state.get(f"{NS}_results", {}) or {}
    score = sum(1 for r in results.values() if r.get("correct"))
    wrong_list = [qid for qid, r in results.items() if not r.get("correct")]

    st.success(f"세트 완료! {score} / {len(qids)}")
    if wrong_list:
        st.caption(f"오답: {', '.join(wrong_list[:20])}{'…' if len(wrong_list)>20 else ''}")

    # progress 반영
    talk["attempts"] = int(talk.get("attempts", 0)) + len(qids)
    talk["correct"] = int(talk.get("correct", 0)) + score
    # 맞힌 문제는 mastered에 추가
    newly_mastered = [qid for qid, r in results.items() if r.get("correct")]
    talk["mastered_ids"] = list(dict.fromkeys((talk.get("mastered_ids", []) or []) + newly_mastered))
    # 틀린 문제는 wrong_ids에 추가
    talk["wrong_ids"] = list(dict.fromkeys((talk.get("wrong_ids", []) or []) + wrong_list))
    talk["last_set"] = {"qids": qids, "results": results, "finished_at": datetime.utcnow().isoformat()}
    # ✅ 말하기 자기평가 히스토리(마이페이지 요약용)
    try:
        hist = talk.get("self_eval_history") or []
        now_iso = datetime.utcnow().isoformat()
        for _qid, _r in (results or {}).items():
            _sev = (_r or {}).get("self_eval") or {}
            if not _sev:
                continue
            hist.append({
                "ts": now_iso,
                "qid": str(_qid),
                "pron": int(_sev.get("pron", 0) or 0),
                "inton": int(_sev.get("intonation", 0) or 0),
                "speed": int(_sev.get("speed", 0) or 0),
                "conf": int(_sev.get("confidence", 0) or 0),
            })
        # 너무 커지지 않게 최근 500개만 유지
        if len(hist) > 500:
            hist = hist[-500:]
        talk["self_eval_history"] = hist
    except Exception:
        pass

    progress_all["talk"] = talk
    save_progress(progress_all)
    log_attempt(sel_level, sel_tag or "all", len(qids), score, wrong_list)

    # ✅ 10문제 완주 보상(허브 공통)
    try:
        fn = st.session_state.get("hub_record_completion")
        if callable(fn):
            fn("talk", score, len(qids))
    except Exception:
        pass

    c_end1, c_end2 = st.columns([1, 1])
    with c_end1:
        if st.button("새 10문 세트", use_container_width=True):
            start_new_set()
            st.rerun()
    with c_end2:
        if st.button("오답노트 보기", use_container_width=True):
            st.session_state[f"{NS}_view"] = "wrongs"
            st.rerun()
    st.stop()

# ============================================================
# ✅ 오답노트 뷰
# ============================================================
view = st.session_state.get(f"{NS}_view", "quiz")
if view == "wrongs":
    st.subheader("오답노트")
    wrongs = talk.get("wrong_ids", []) or []
    if not wrongs:
        st.info("오답노트가 비어 있습니다.")
    else:
        # 필터 적용해서 표시
        show_df = DF[DF["qid"].astype(str).isin(wrongs)].copy()
        if sel_level:
            show_df = show_df[show_df["level"].astype(str) == str(sel_level)]
        if sel_tag and "tag" in show_df.columns:
            show_df = show_df[show_df["tag"].astype(str) == str(sel_tag)]
        show_df = show_df.reset_index(drop=True)

        for _, r in show_df.head(50).iterrows():
            st.markdown("---")
            st.write(f"**상황**: {r.get('situation_kr','')}")
            pj = str(r.get("partner_jp","")).strip()
            aj = str(r.get("answer_jp","")).strip()
            # 문제/정답 발음만
            if pj:
                (components.html(speak_buttons_html([("상대 발화", pj)], block_id=f"w_p_{r['qid']}"), height=40) if IS_PRO else st.caption("🔒 발음은 PRO 플랜에서 이용할 수 있어요."))
            st.write(f"정답: {aj}")
            if aj:
                (components.html(speak_buttons_html([("정답", aj)], block_id=f"w_a_{r['qid']}"), height=40) if IS_PRO else st.caption("🔒 발음은 PRO 플랜에서 이용할 수 있어요."))

    if st.button("퀴즈로 돌아가기", use_container_width=True):
        st.session_state[f"{NS}_view"] = "quiz"
        st.rerun()
    st.stop()

# ============================================================
# ✅ 현재 문제 로드
# ============================================================
qid = qids[idx]
row = DF[DF["qid"].astype(str) == str(qid)].iloc[0].to_dict()

# 보기 구성(쌩뚱맞게 가리기)
choices_key = f"{NS}_choices_{qid}"
if choices_key not in st.session_state:
    st.session_state[choices_key] = build_choices(row, pool_answers)
choices = st.session_state[choices_key]

# 상단 진행 표기: "1 / 10" (Q1 제거)
st.markdown(f"### {idx+1} / {len(qids)}")

# ============================================================
# ✅ 문제 카드
# ============================================================
st.markdown("#### 상황")
st.write(str(row.get("situation_kr","")).strip())

partner_jp = str(row.get("partner_jp","")).strip()
partner_kr = str(row.get("partner_kr","")).strip()

st.markdown("#### 상대 발화")
if partner_jp:
    st.write(partner_jp)
    # ✅ 문제 발음(상대 발화)만 제공
    (components.html(speak_buttons_html([("상대 발화 듣기", partner_jp)], block_id=f"p_{qid}_{idx}"), height=40) if IS_PRO else st.caption("🔒 발음은 PRO 플랜에서 이용할 수 있어요."))
else:
    st.caption("상대 발화가 비어 있습니다. (CSV의 partner_jp 확인)")

if partner_kr:
    st.caption(partner_kr)

# ============================================================
# ✅ 실제 말하기 모드(녹음)
# - 채점은 하지 않지만, 말해보는 경험을 제공
# ============================================================
with st.expander("🎙️ 말하기 모드(녹음)", expanded=False):
    st.caption("상대 발화를 듣고, 아래에서 직접 말해보세요. 녹음은 기기에서만 재생됩니다.")
    try:
        audio = st.audio_input("내 목소리 녹음하기")
        if audio is not None:
            st.audio(audio)
    except Exception:
        st.caption("현재 환경에서는 녹음 기능이 지원되지 않을 수 있어요.")

with st.expander("🎯 자기평가(말하기 체크)", expanded=False):
    st.caption("채점이 아니라 ‘스스로 점검’용입니다. 10문 세트가 끝나면 마이페이지 요약에 반영돼요.")
    sev_pron = st.slider("발음(정확도)", 1, 5, 3, key=f"{NS}_sev_pron_{qid}")
    sev_int  = st.slider("억양(자연스러움)", 1, 5, 3, key=f"{NS}_sev_int_{qid}")
    sev_spd  = st.slider("속도(적절함)", 1, 5, 3, key=f"{NS}_sev_spd_{qid}")
    sev_conf = st.slider("자신감", 1, 5, 3, key=f"{NS}_sev_conf_{qid}")
    sev_goal = st.text_input("다음 목표(한 줄)", value="", placeholder="예) 끝을 올리지 않고 차분하게 말하기", key=f"{NS}_sev_goal_{qid}")


st.markdown("#### 보기")
selected = st.radio("정답을 고르세요.", choices, key="talk_choice")

submitted = st.session_state.get("talk_submitted", False)

b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("제출", use_container_width=True, key=f"talk_submit_{qid}_{idx}"):
        st.session_state["talk_submitted"] = True
        submitted = True

        ans = str(row["answer_jp"]).strip()
        ok = (selected == ans)

        # ✅ 자기평가(말하기) 저장
        sev = {
            "pron": int(st.session_state.get(f"{NS}_sev_pron_{qid}", 3)),
            "intonation": int(st.session_state.get(f"{NS}_sev_int_{qid}", 3)),
            "speed": int(st.session_state.get(f"{NS}_sev_spd_{qid}", 3)),
            "confidence": int(st.session_state.get(f"{NS}_sev_conf_{qid}", 3)),
            "goal": str(st.session_state.get(f"{NS}_sev_goal_{qid}", "")).strip(),
        }

        results = st.session_state.get(f"{NS}_results", {}) or {}
        results[str(qid)] = {"selected": selected, "correct": bool(ok), "self_eval": sev}
        st.session_state[f"{NS}_results"] = results

        st.rerun()

with b2:
    # 제출 없이도 다음으로 넘어가면 '10문 세트' 의미가 약해져서,
    # 제출 후에만 다음 활성화(기존 유지)
    if st.button("다음", use_container_width=True, disabled=not submitted, key=f"talk_next_{qid}_{idx}"):
        st.session_state[f"{NS}_idx"] = idx + 1
        st.session_state["talk_submitted"] = False
        st.session_state.pop("talk_choice", None)
        st.rerun()

with b3:
    if st.button("오답노트", use_container_width=True, key=f"talk_to_wrongs_{qid}_{idx}"):
        st.session_state[f"{NS}_view"] = "wrongs"
        st.rerun()

# ============================================================
# ✅ 제출 후: 결과 + (문제/정답) 스크립트 + 발음 + 납득 안내
# ============================================================
if submitted:
    ans = str(row["answer_jp"]).strip()
    ok = (selected == ans)

    if ok:
        st.success("정답입니다.")
    else:
        st.error("오답입니다.")

    st.divider()

    # ✅ 제출 후에도 '문제(상대 발화)'를 다시 표시
    st.markdown("#### 문제(상대 발화)")
    if partner_jp:
        st.write(partner_jp)
        (components.html(
            speak_buttons_html([("상대 발화 듣기", partner_jp)], block_id=f"p_after_{qid}_{idx}"),
            height=40,
        ) if IS_PRO else st.caption("🔒 발음은 PRO 플랜에서 이용할 수 있어요."))
    else:
        st.caption("상대 발화가 비어 있습니다. (CSV의 partner_jp 확인)")

    if partner_kr:
        st.caption(partner_kr)

    st.markdown("#### 정답")
    st.write(ans)

    if ans:
        (components.html(
            speak_buttons_html([("정답 듣기", ans)], block_id=f"a_{qid}_{idx}"),
            height=40,
        ) if IS_PRO else st.caption("🔒 발음은 PRO 플랜에서 이용할 수 있어요."))

    answer_kr = str(row.get("answer_kr", "")).strip()
    if answer_kr:
        st.caption(answer_kr)

    # ✅ 납득할 만한 안내(설명)
    hint = str(row.get("hint_kr", "")).strip()
    if hint:
        st.info(hint)
    else:
        sit = str(row.get("situation_kr", "")).strip()
        if sit and answer_kr:
            st.info(f"상황이 '{sit}'이므로, '{answer_kr}'처럼 답하는 게 가장 자연스럽습니다.")
        elif sit:
            st.info(f"상황이 '{sit}'이므로, 이 정답이 가장 자연스럽습니다.")
        elif partner_kr:
            st.info("상대의 발화 의도에 가장 자연스럽게 이어지는 반응입니다.")
        else:
            st.info("대화 흐름에 가장 자연스럽게 이어지는 반응입니다.")

    # ✅ 내 자기평가 요약(제출 후)
    try:
        _res = (st.session_state.get(f"{NS}_results") or {}).get(str(qid), {}) or {}
        _sev = _res.get("self_eval") or {}
        if _sev:
            st.markdown("#### 내 말하기 자기평가(참고)")
            c_sev1, c_sev2, c_sev3, c_sev4 = st.columns(4)
            c_sev1.metric("발음", f"{int(_sev.get('pron',0))}/5")
            c_sev2.metric("억양", f"{int(_sev.get('intonation',0))}/5")
            c_sev3.metric("속도", f"{int(_sev.get('speed',0))}/5")
            c_sev4.metric("자신감", f"{int(_sev.get('confidence',0))}/5")
            goal = str(_sev.get("goal","")).strip()
            if goal:
                st.caption(f"다음 목표: {goal}")
    except Exception:
        pass


