# BUILD_STAMP: v35 2026-02-19 22:23:41 KST (+09:00)
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

HUB_MODE = bool(st.session_state.get("HUB_MODE", False))

if not HUB_MODE:
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
    # 10문 뽑기(가능한 만큼)
    n = min(QUIZ_LEN, len(pool_df))
    sample = pool_df.sample(n=n, replace=False)
    qids = sample["qid"].astype(str).tolist()

    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = 0
    st.session_state[f"{NS}_results"] = {}  # qid -> {"selected":..., "correct":bool}
    st.session_state["talk_submitted"] = False
    # ✅ 이전 문제의 보기/선택/녹음 키 정리
    for k in list(st.session_state.keys()):
        if str(k).startswith(f"{NS}_choices_") or str(k).startswith(f"{NS}_choice_") or str(k).startswith(f"{NS}_rec_"):
            st.session_state.pop(k, None)
    
        # (qid별 key를 쓰므로 별도 pop 불필요)

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
    progress_all["talk"] = talk
    save_progress(progress_all)
    log_attempt(sel_level, sel_tag or "all", len(qids), score, wrong_list)

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
                components.html(speak_buttons_html([("상대 발화", pj)], block_id=f"w_p_{r['qid']}"), height=60)
            st.write(f"정답: {aj}")
            if aj:
                components.html(speak_buttons_html([("정답", aj)], block_id=f"w_a_{r['qid']}"), height=60)

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
# 보기 구성(✅ 문제당 1회만 생성해 고정: 선택해도 보기 순서가 바뀌지 않게)
_choices_key = f"{NS}_choices_{qid}"
if _choices_key not in st.session_state:
    st.session_state[_choices_key] = build_choices(row, pool_answers)
choices = st.session_state[_choices_key]


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
    components.html(
        speak_buttons_html([("상대 발화 듣기", partner_jp)], block_id=f"p_{qid}_{idx}"),
        height=60
    )
else:
    st.caption("상대 발화가 비어 있습니다. (CSV의 partner_jp 확인)")

if partner_kr:
    st.caption(partner_kr)

st.markdown("#### 보기")
selected = st.radio("정답을 고르세요.", choices, key=f"{NS}_choice_{qid}")

submitted = st.session_state.get("talk_submitted", False)

b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("제출", use_container_width=True, key=f"talk_submit_{qid}_{idx}"):
        st.session_state["talk_submitted"] = True
        submitted = True

        ans = str(row["answer_jp"]).strip()
        ok = (selected == ans)

        results = st.session_state.get(f"{NS}_results", {}) or {}
        results[str(qid)] = {"selected": selected, "correct": bool(ok)}
        st.session_state[f"{NS}_results"] = results

        st.rerun()

with b2:
    # 제출 없이도 다음으로 넘어가면 '10문 세트' 의미가 약해져서,
    # 제출 후에만 다음 활성화(기존 유지)
    if st.button("다음", use_container_width=True, disabled=not submitted, key=f"talk_next_{qid}_{idx}"):
        st.session_state[f"{NS}_idx"] = idx + 1
        st.session_state["talk_submitted"] = False
        # ✅ 현재 문제의 보기/선택/녹음 상태 정리
        st.session_state.pop(f"{NS}_choices_{qid}", None)
        st.session_state.pop(f"{NS}_choice_{qid}", None)
        st.session_state.pop(f"{NS}_rec_{qid}_{idx}", None)
        # (qid별 key를 쓰므로 별도 pop 불필요)
        st.rerun()

with b3:
    if st.button("오답노트", use_container_width=True, key=f"talk_to_wrongs_{qid}_{idx}"):
        st.session_state[f"{NS}_view"] = "wrongs"
        st.rerun()

# ============================================================
# ✅ 제출 후: 정답/오답 + 정답 발음(보기 발음은 제공하지 않음)
# ============================================================
if submitted:
    ans = str(row["answer_jp"]).strip()
    if selected == ans:
        st.success("정답입니다.")
    else:
        st.error("오답입니다.")

    st.markdown("#### 정답")
    st.write(ans)

    # ✅ 정답 발음만
    if ans:
        components.html(
            speak_buttons_html([("정답 듣기", ans)], block_id=f"a_{qid}_{idx}"),
            height=60
        )

    if str(row.get("answer_kr","")).strip():
        st.caption(str(row.get("answer_kr","")).strip())

    # 힌트는 제출 후에만 보여줘도 됨
    hint = str(row.get("hint_kr","")).strip()
    if hint:
        st.info(hint)

# ============================================================
# ✅ 제출 후: 내 발음 녹음 (파형 UI) 
# - Streamlit >= 1.32: st.audio_input 사용 (권장)
# - 구버전/미지원 환경: HTML MediaRecorder + 간단 파형(저장은 브라우저 내)
# ============================================================
st.markdown('#### 내 발음 녹음')
if hasattr(st, 'audio_input'):
    rec = st.audio_input('마이크로 녹음하세요 (파형 표시)', key=f"{NS}_rec_{qid}_{idx}")
    if rec is not None:
        try:
            audio_bytes = rec.getvalue()
        except Exception:
            audio_bytes = None
        if audio_bytes:
            st.success('녹음이 저장되었습니다.')
            st.audio(audio_bytes, format='audio/wav')
else:
    # ✅ CSP-safe: inline JS 최소화(버튼 클릭 기반).
    components.html("""
<div style='margin-top:6px;'>
  <div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px;'>
    <button id='recBtn' style='padding:8px 12px;border-radius:999px;border:1px solid #ddd;background:white;cursor:pointer;'>🎤 녹음 시작</button>
    <button id='stopBtn' disabled style='padding:8px 12px;border-radius:999px;border:1px solid #ddd;background:#f7f7f7;cursor:pointer;'>⏹ 정지</button>
    <span style='font-size:0.9rem;opacity:0.75;'>표시:</span>
    <button id='modeWave' style='padding:6px 10px;border-radius:999px;border:1px solid #ddd;background:#111;color:#fff;cursor:pointer;'>파형</button>
    <button id='modeBars' style='padding:6px 10px;border-radius:999px;border:1px solid #ddd;background:white;cursor:pointer;'>음파</button>
    <a id='dl' style='margin-left:8px; display:none;'>⬇️ 녹음 다운로드</a>
  </div>

  <canvas id='viz' width='520' height='90'
    style='display:block;margin-top:2px;width:100%;max-width:520px;background:#111;border-radius:10px;'></canvas>

  <div id='hint' style='margin-top:6px;font-size:0.85rem;opacity:0.65;'>
    녹음 중에는 시각화가 실시간으로 움직입니다. (환경에 따라 마이크 권한 요청이 뜰 수 있어요.)
  </div>
</div>

<script>
let mediaRecorder; let chunks=[];
let audioCtx, analyser, dataArray, srcNode, streamRef;
let rafId=null;
let mode="wave"; // wave | bars

const recBtn=document.getElementById('recBtn');
const stopBtn=document.getElementById('stopBtn');
const dl=document.getElementById('dl');
const canvas=document.getElementById('viz');
const ctx=canvas.getContext('2d');

const modeWave=document.getElementById('modeWave');
const modeBars=document.getElementById('modeBars');

function setMode(m){
  mode=m;
  if(mode==="wave"){
    modeWave.style.background="#111"; modeWave.style.color="#fff";
    modeBars.style.background="#fff"; modeBars.style.color="#111";
  }else{
    modeBars.style.background="#111"; modeBars.style.color="#fff";
    modeWave.style.background="#fff"; modeWave.style.color="#111";
  }
}
modeWave.onclick=()=>setMode("wave");
modeBars.onclick=()=>setMode("bars");

function draw(){
  if(!analyser){ return; }

  ctx.fillStyle="#111";
  ctx.fillRect(0,0,canvas.width,canvas.height);

  if(mode==="wave"){
    // Oscilloscope line (time domain)
    analyser.getByteTimeDomainData(dataArray);
    ctx.lineWidth=2;
    ctx.strokeStyle="#00ff99";
    ctx.beginPath();
    const slice=canvas.width/dataArray.length;
    let x=0;
    for(let i=0;i<dataArray.length;i++){
      const v=dataArray[i]/128.0;
      const y=v*canvas.height/2;
      if(i===0){ ctx.moveTo(x,y); } else { ctx.lineTo(x,y); }
      x += slice;
    }
    ctx.stroke();
  } else {
    // "음파" 느낌: spectrum bars (frequency domain)
    analyser.getByteFrequencyData(dataArray);
    const barCount = Math.min(dataArray.length, 64);
    const step = Math.floor(dataArray.length / barCount);
    const barW = canvas.width / barCount;

    for(let i=0;i<barCount;i++){
      const v = dataArray[i*step] / 255.0;
      const h = Math.max(2, v * (canvas.height-8));
      const x = i * barW;
      const y = canvas.height - h;
      ctx.fillStyle="#00ff99";
      ctx.fillRect(x+1, y, Math.max(1, barW-2), h);
    }
  }

  rafId=requestAnimationFrame(draw);
}

async function start(){
  dl.style.display='none';
  dl.removeAttribute('href');
  dl.removeAttribute('download');

  streamRef = await navigator.mediaDevices.getUserMedia({audio:true});

  audioCtx = new (window.AudioContext||window.webkitAudioContext)();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;

  dataArray = new Uint8Array(analyser.frequencyBinCount);

  srcNode = audioCtx.createMediaStreamSource(streamRef);
  srcNode.connect(analyser);

  mediaRecorder = new MediaRecorder(streamRef);
  chunks = [];

  mediaRecorder.ondataavailable = (e)=>{ if(e.data && e.data.size>0) chunks.push(e.data); };
  mediaRecorder.onstop = ()=>{
    try{
      const blob = new Blob(chunks, {type:'audio/webm'});
      const url = URL.createObjectURL(blob);
      dl.href = url;
      dl.download = "talk_record.webm";
      dl.style.display = "inline-block";
    }catch(err){}
    cleanupStream();
  };

  mediaRecorder.start();
  recBtn.disabled=true;
  stopBtn.disabled=false;

  if(rafId) cancelAnimationFrame(rafId);
  rafId=requestAnimationFrame(draw);
}

function cleanupStream(){
  try{
    if(rafId){ cancelAnimationFrame(rafId); rafId=null; }
    if(audioCtx){ audioCtx.close(); audioCtx=null; }
    if(streamRef){
      streamRef.getTracks().forEach(t=>t.stop());
      streamRef=null;
    }
  }catch(e){}
}

function stop(){
  try{
    stopBtn.disabled=true;
    recBtn.disabled=false;
    if(mediaRecorder && mediaRecorder.state!=="inactive"){
      mediaRecorder.stop();
    } else {
      cleanupStream();
    }
  }catch(e){
    cleanupStream();
  }
}

recBtn.onclick = ()=>start();
stopBtn.onclick = ()=>stop();

// initial mode
setMode("wave");
</script>
""", height=260)

