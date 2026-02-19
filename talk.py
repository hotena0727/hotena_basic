# talk.py
from __future__ import annotations

from pathlib import Path
import random
from datetime import datetime, date
import hashlib

import pandas as pd
import streamlit as st

# ============================================================
# ✅ Theme (Hotena) - one-time CSS inject
# ============================================================
try:
    import theme_hotena
    theme_hotena.apply_hotena_theme()
except Exception:
    pass


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
def _user_field(obj, key: str):
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
USER_ID = _user_field(USER, "id")
USER_EMAIL = _user_field(USER, "email")
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
    # ✅ 각 qid별 UI 상태 초기화(제출 여부/선택지)
    for _qid in qids:
        st.session_state[f"talk_submitted_{_qid}"] = False
        st.session_state.pop(f"talk_choice_{_qid}", None)
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
# 보기 구성: rerun(라디오 클릭)에도 고정되도록 qid별 캐시
_ck = f"{NS}_choices_{qid}"
if _ck not in st.session_state:
    st.session_state[_ck] = build_choices(row, pool_answers)
choices = st.session_state[_ck]
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
selected = st.radio("정답을 고르세요.", choices, key=f"talk_choice_{qid}")

submitted = st.session_state.get(f"talk_submitted_{qid}", False)

b1, b2, b3 = st.columns([1, 1, 1])
with b1:
    if st.button("제출", use_container_width=True, key=f"talk_submit_{qid}_{idx}"):
        st.session_state[f"talk_submitted_{qid}"] = True
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
        st.session_state[f"talk_submitted_{qid}"] = False
        st.session_state.pop(f"talk_choice_{qid}", None)
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
        # ✅ 제출 직후: 정답 자동 TTS 1회 (문항당 1회만)
        _tts_once_key = f"{NS}_tts_once_{qid}"
        if not st.session_state.get(_tts_once_key, False):
            st.session_state[_tts_once_key] = True
            try:
                components.html(f"""
<script>
(function(){
  const text = {ans!r};
  if(!text) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "ja-JP";
  u.rate = 1.0;
  u.pitch = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
})();
</script>
""", height=0)
            except Exception:
                pass

        # ✅ 파형 포함 녹음(저장 없음): 정답 확인 후 따라 말하기
        st.markdown("#### 🎤 따라 말하기 (녹음 후 재생)")
        try:
            components.html("""
<style>
  .rec-wrap{border:1px solid rgba(49,51,63,.12); border-radius:16px; padding:12px; background:#fff;}
  .rec-top{display:flex; gap:10px; align-items:center; flex-wrap:wrap;}
  .rec-btn{border:0; border-radius:999px; padding:10px 14px; cursor:pointer; font-weight:800;}
  .rec-btn.primary{background:#1C2F5C; color:#fff;}
  .rec-btn.danger{background:#E5484D; color:#fff;}
  .rec-btn.ghost{background:rgba(28,47,92,.08); color:#1C2F5C;}
  .rec-ind{display:flex; align-items:center; gap:8px; font-size:0.95rem; opacity:0.9;}
  .dot{width:10px;height:10px;border-radius:50%; background:#E5484D; display:inline-block; animation:pulse 1.1s infinite;}
  @keyframes pulse{0%{transform:scale(1); opacity:.45}50%{transform:scale(1.35); opacity:1}100%{transform:scale(1); opacity:.45}}
  canvas{width:100%; height:86px; border-radius:12px; background:rgba(28,47,92,.04);}
  audio{width:100%; margin-top:10px;}
</style>

<div class="rec-wrap">
  <div class="rec-top">
    <button id="recStart" class="rec-btn primary" type="button">● 녹음 시작</button>
    <button id="recStop" class="rec-btn danger" type="button" disabled>■ 정지</button>
    <button id="recClear" class="rec-btn ghost" type="button" disabled>↺ 삭제</button>
    <span id="recStatus" class="rec-ind"></span>
  </div>
  <div style="margin-top:10px;">
    <canvas id="wave" height="86"></canvas>
    <audio id="play" controls></audio>
  </div>
</div>

<script>
(async function(){
  const startBtn = document.getElementById("recStart");
  const stopBtn  = document.getElementById("recStop");
  const clearBtn = document.getElementById("recClear");
  const statusEl = document.getElementById("recStatus");
  const canvas = document.getElementById("wave");
  const ctx = canvas.getContext("2d");
  const audioEl = document.getElementById("play");
  let mediaRecorder, chunks = [];
  let stream, audioCtx, analyser, dataArray, rafId;

  function draw(){
    if(!analyser) return;
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = 86;
    dataArray = dataArray || new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(dataArray);
    ctx.clearRect(0,0,w,h);

    ctx.beginPath();
    ctx.moveTo(0, h/2);
    ctx.lineTo(w, h/2);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(28,47,92,.12)";
    ctx.stroke();

    ctx.beginPath();
    const slice = w / dataArray.length;
    let x = 0;
    for(let i=0;i<dataArray.length;i++){
      const v = (dataArray[i] - 128) / 128.0;
      const y = (h/2) + v * (h/2 - 6);
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      x += slice;
    }
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#1C2F5C";
    ctx.stroke();
    rafId = requestAnimationFrame(draw);
  }

  function stopDraw(){
    if(rafId) cancelAnimationFrame(rafId);
    rafId = null;
  }

  function setStatus(rec){
    if(rec){
      statusEl.innerHTML = '<span class="dot"></span> 녹음 중…';
    }else{
      statusEl.innerHTML = '';
    }
  }

  startBtn.onclick = async () => {
    try{
      stream = await navigator.mediaDevices.getUserMedia({ audio:true });
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      draw();

      chunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e)=>{ if(e.data.size>0) chunks.push(e.data); };
      mediaRecorder.onstop = ()=> {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        audioEl.src = url;
        clearBtn.disabled = false;
      };
      mediaRecorder.start();

      startBtn.disabled = true;
      stopBtn.disabled = false;
      clearBtn.disabled = true;
      setStatus(true);
    }catch(e){
      alert("마이크 권한을 허용해 주세요.");
    }
  };

  stopBtn.onclick = () => {
    try{
      if(mediaRecorder && mediaRecorder.state !== "inactive"){
        mediaRecorder.stop();
      }
      if(stream){
        stream.getTracks().forEach(t=>t.stop());
      }
      if(audioCtx){ audioCtx.close(); }
      stopDraw();
    }catch(e){}
    startBtn.disabled = false;
    stopBtn.disabled = true;
    setStatus(false);
  };

  clearBtn.onclick = () => {
    audioEl.removeAttribute("src");
    audioEl.load();
    clearBtn.disabled = true;
  };
})();
</script>
""", height=260)
        except Exception:
            st.caption("녹음 UI를 불러오지 못했습니다. 브라우저 권한을 확인해 주세요.")


    if str(row.get("answer_kr","")).strip():
        st.caption(str(row.get("answer_kr","")).strip())

    # 힌트는 제출 후에만 보여줘도 됨
    hint = str(row.get("hint_kr","")).strip()
    if hint:
        st.info(hint)
