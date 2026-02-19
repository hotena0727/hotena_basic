from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
from ui import top_nav
from gate import gate, consume

_RECORDER = """<div style="font-family: system-ui; line-height:1.4">
  <p style="margin:0 0 10px 0; opacity:0.75;">Start → Speak → Stop. (브라우저 마이크 권한 필요)</p>
  <div style="display:flex; gap:8px; margin:8px 0;">
    <button id="s">Start</button>
    <button id="t" disabled>Stop</button>
  </div>
  <canvas id="c" width="640" height="120" style="width:100%; border:1px solid rgba(0,0,0,.12); border-radius:10px;"></canvas>
  <audio id="p" controls style="width:100%; margin-top:10px;"></audio>
<script>
const s=document.getElementById('s'), t=document.getElementById('t');
const c=document.getElementById('c'), x=c.getContext('2d');
const p=document.getElementById('p');
let mr, chunks=[], ac, an, src, st;

function draw(){
  if(!an) return;
  const n=an.fftSize, a=new Uint8Array(n);
  an.getByteTimeDomainData(a);
  x.clearRect(0,0,c.width,c.height);
  x.beginPath();
  const w=c.width/n; let px=0;
  for(let i=0;i<n;i++){
    const v=a[i]/128.0, y=v*c.height/2;
    if(i===0) x.moveTo(px,y); else x.lineTo(px,y);
    px+=w;
  }
  x.strokeStyle='rgba(0,0,0,.7)'; x.lineWidth=2; x.stroke();
  requestAnimationFrame(draw);
}

async function start(){
  st = await navigator.mediaDevices.getUserMedia({audio:true});
  ac = new (window.AudioContext||window.webkitAudioContext)();
  an = ac.createAnalyser(); an.fftSize=2048;
  src = ac.createMediaStreamSource(st); src.connect(an);
  chunks=[];
  mr = new MediaRecorder(st);
  mr.ondataavailable = e => chunks.push(e.data);
  mr.onstop = () => {
    const b=new Blob(chunks,{type:'audio/webm'});
    p.src = URL.createObjectURL(b);
  };
  mr.start(); draw();
  s.disabled=true; t.disabled=false;
}
function stop(){
  if(mr && mr.state!=='inactive') mr.stop();
  if(st) st.getTracks().forEach(tr=>tr.stop());
  s.disabled=false; t.disabled=true;
}
s.onclick=()=>start().catch(e=>alert(e));
t.onclick=()=>stop();
</script>
</div>
"""


def render_talk():
    top_nav()
    st.markdown("## 🗣️ 회화 훈련")

    gate("talk")

    if st.button("녹음 시작 준비", use_container_width=True):
        consume("talk")
        st.session_state["talk_started"] = True
        st.rerun()

    if st.session_state.get("talk_started"):
        components.html(_RECORDER, height=320)
        st.info("HTTPS 환경(예: Streamlit Cloud)에서 마이크 권한이 더 안정적입니다.")
