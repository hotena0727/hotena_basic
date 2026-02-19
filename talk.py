# talk.py (PATCH: waveform recorder after answer submission)
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# ✅ Waveform Recorder Component (no upload / no DB save)
# - Uses MediaRecorder + WebAudio AnalyserNode + Canvas waveform
# - Runs fully in browser (page-local). Nothing is stored server-side.
# ============================================================

_WAVEFORM_COMPONENT_HTML = r"""
<div id="rec_wrap" style="border:1px solid rgba(0,0,0,.08);border-radius:16px;padding:14px 14px 10px 14px;background:rgba(255,255,255,.70);backdrop-filter: blur(6px);">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
    <div style="font-weight:700;font-size:16px;">🎤 내 발음 연습 (파형 표시)</div>
    <div id="rec_state" style="font-size:13px;opacity:.75;">대기 중</div>
  </div>

  <div style="height:10px"></div>

  <canvas id="wf" width="900" height="160" style="width:100%;height:120px;border-radius:12px;background:rgba(0,0,0,.03);"></canvas>

  <div style="height:10px"></div>

  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <button id="btn_start" style="flex:1;min-height:46px;border-radius:12px;border:1px solid rgba(0,0,0,.12);background:white;font-size:15px;font-weight:700;">● 녹음 시작</button>
    <button id="btn_stop"  disabled style="flex:1;min-height:46px;border-radius:12px;border:1px solid rgba(0,0,0,.12);background:white;font-size:15px;font-weight:700;opacity:.55;">■ 정지</button>
    <button id="btn_clear" disabled style="flex:1;min-height:46px;border-radius:12px;border:1px solid rgba(0,0,0,.12);background:white;font-size:15px;font-weight:700;opacity:.55;">✕ 삭제</button>
  </div>

  <div style="height:10px"></div>

  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
    <audio id="player" controls style="width:100%;"></audio>
    <div id="hint" style="font-size:13px;opacity:.75;">
      정답 제출 후, 녹음해서 바로 들어보세요. (저장되지 않습니다)
    </div>
  </div>
</div>

<script>
(function(){
  // Prevent duplicate init when Streamlit re-renders this HTML
  const root = document.currentScript && document.currentScript.parentElement;
  if(!root) return;
  if(root.dataset.__wf_inited === "1") return;
  root.dataset.__wf_inited = "1";

  const canvas = root.querySelector("#wf");
  const ctx = canvas.getContext("2d");
  const stateEl = root.querySelector("#rec_state");
  const btnStart = root.querySelector("#btn_start");
  const btnStop  = root.querySelector("#btn_stop");
  const btnClear = root.querySelector("#btn_clear");
  const player   = root.querySelector("#player");

  let mediaRecorder = null;
  let chunks = [];
  let stream = null;

  let audioCtx = null;
  let analyser = null;
  let sourceNode = null;

  let rafId = null;

  function resizeCanvas(){
    const cssW = canvas.clientWidth;
    const cssH = canvas.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = Math.max(300, Math.floor(cssW * dpr));
    canvas.height = Math.max(120, Math.floor(cssH * dpr));
  }

  function clearWave(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = "rgba(0,0,0,.08)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height/2);
    ctx.lineTo(canvas.width, canvas.height/2);
    ctx.stroke();
  }

  function drawWave(){
    if(!analyser) { clearWave(); return; }
    const bufferLength = analyser.fftSize;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle = "rgba(0,0,0,.03)";
    ctx.fillRect(0,0,canvas.width,canvas.height);

    ctx.lineWidth = Math.max(2, Math.floor(canvas.width/450));
    ctx.strokeStyle = "rgba(0,0,0,.65)";
    ctx.beginPath();

    const sliceWidth = canvas.width * 1.0 / bufferLength;
    let x = 0;
    for(let i=0;i<bufferLength;i++){
      const v = dataArray[i] / 128.0;
      const y = v * canvas.height/2;
      if(i === 0) ctx.moveTo(x,y);
      else ctx.lineTo(x,y);
      x += sliceWidth;
    }
    ctx.lineTo(canvas.width, canvas.height/2);
    ctx.stroke();

    rafId = requestAnimationFrame(drawWave);
  }

  function stopDrawing(){
    if(rafId){ cancelAnimationFrame(rafId); rafId = null; }
  }

  function setButtons(recording, hasAudio){
    if(recording){
      btnStart.disabled = true;
      btnStop.disabled = false;
      btnClear.disabled = true;
      btnStart.style.opacity = .55;
      btnStop.style.opacity = 1;
      btnClear.style.opacity = .55;
    }else{
      btnStart.disabled = false;
      btnStop.disabled = true;
      btnStart.style.opacity = 1;
      btnStop.style.opacity = .55;
      btnClear.disabled = !hasAudio;
      btnClear.style.opacity = hasAudio ? 1 : .55;
    }
  }

  async function ensureAudioCtx(){
    if(!audioCtx){
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 2048;
    }
  }

  async function startRecording(){
    try{
      resizeCanvas();
      clearWave();
      await ensureAudioCtx();

      stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // live waveform from mic
      if(sourceNode) { try{ sourceNode.disconnect(); }catch(e){} sourceNode=null; }
      sourceNode = audioCtx.createMediaStreamSource(stream);
      sourceNode.connect(analyser);

      chunks = [];
      // Some browsers may not accept audio/webm; fallback handled by default type
      try{
        mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      }catch(e){
        mediaRecorder = new MediaRecorder(stream);
      }

      mediaRecorder.ondataavailable = (e) => { if(e.data && e.data.size>0) chunks.push(e.data); };
      mediaRecorder.onstop = () => {
        try{
          const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
          const url = URL.createObjectURL(blob);
          player.src = url;
          player.load();

          // connect player to analyser for playback waveform
          try{
            if(player.__wf_source){
              player.__wf_source.disconnect();
              player.__wf_source = null;
            }
          }catch(e){}

          const elSource = audioCtx.createMediaElementSource(player);
          elSource.connect(analyser);
          elSource.connect(audioCtx.destination);
          player.__wf_source = elSource;

          stateEl.textContent = "녹음 완료 · 재생해서 확인해보세요";
          setButtons(false, true);
          stopDrawing();
          drawWave();
        }catch(e){
          console.error(e);
        }
      };

      mediaRecorder.start(120);
      stateEl.textContent = "녹음 중…";
      setButtons(true, false);
      stopDrawing();
      drawWave();

    }catch(err){
      console.error(err);
      stateEl.textContent = "마이크 권한을 확인해주세요";
      setButtons(false, false);
      stopDrawing();
      clearWave();
      if(stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; }
    }
  }

  function stopRecording(){
    try{
      if(mediaRecorder && mediaRecorder.state !== "inactive"){
        mediaRecorder.stop();
      }
    }catch(e){}
    try{
      if(stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; }
    }catch(e){}
    stateEl.textContent = "처리 중…";
  }

  function clearRecording(){
    try{
      if(player && player.src){
        URL.revokeObjectURL(player.src);
      }
    }catch(e){}
    player.removeAttribute("src");
    player.load();
    stateEl.textContent = "대기 중";
    setButtons(false, false);
    stopDrawing();
    clearWave();
  }

  btnStart.addEventListener("click", async () => { await startRecording(); });
  btnStop.addEventListener("click", () => stopRecording());
  btnClear.addEventListener("click", () => clearRecording());

  // iOS: resume audio context on gesture
  document.addEventListener("click", () => {
    if(audioCtx && audioCtx.state === "suspended"){ audioCtx.resume(); }
  }, { once:false });

  window.addEventListener("resize", () => { resizeCanvas(); clearWave(); });

  resizeCanvas();
  clearWave();
  setButtons(false, false);
})();
</script>
"""

def _talk_has_submitted_result() -> bool:
    """
    Heuristic: show recorder only after '정답 제출' occurred.
    We avoid touching other parts; we infer from common flags in session_state.
    """
    keys = [
        "talk_submitted", "talk_checked", "talk_answer_checked", "talk_result_shown",
        "_talk_submitted", "_talk_checked",
        "submitted", "checked", "answer_submitted", "show_answer", "result_shown",
        "is_submitted", "is_checked",
    ]
    for k in keys:
        v = st.session_state.get(k, None)
        if isinstance(v, bool) and v:
            return True
    for k in ["talk_last_result", "last_result", "talk_is_correct", "is_correct", "talk_correct"]:
        if st.session_state.get(k, None) is not None:
            return True
    return False

def render_waveform_recorder(key: str = "talk_waveform_recorder"):
    components.html(_WAVEFORM_COMPONENT_HTML, height=320, scrolling=False, key=key)

def inject_recorder_after_submit():
    # Only show after submit (A requirement)
    if _talk_has_submitted_result():
        st.markdown("---")
        render_waveform_recorder(key="talk_waveform_recorder_v1")
