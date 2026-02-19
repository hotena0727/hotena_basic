
# talk.py - v47 Custom Equalizer Recorder
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Talk Training", layout="centered")

st.title("🎤 회화 훈련 - Custom Recorder")

st.markdown("""
<style>
.rec-card{
    border:1px solid rgba(0,0,0,0.08);
    border-radius:16px;
    padding:20px;
    background:#ffffff;
    box-shadow:0 6px 18px rgba(0,0,0,0.05);
}
.eq-bars{
    display:flex;
    gap:4px;
    align-items:flex-end;
    height:60px;
    margin-bottom:15px;
}
.eq-bar{
    width:6px;
    background:#3B82F6;
    border-radius:4px;
    height:10px;
    transition:height 0.1s linear;
}
.rec-btn{
    background:#111;
    color:#fff;
    padding:10px 20px;
    border:none;
    border-radius:8px;
    cursor:pointer;
}
audio{
    width:100%;
    margin-top:15px;
}
</style>
""", unsafe_allow_html=True)

components.html("""
<div class="rec-card">
    <div id="bars" class="eq-bars"></div>
    <button id="recBtn" class="rec-btn">Start Recording</button>
    <audio id="player" controls></audio>
</div>

<script>
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
const barsContainer = document.getElementById("bars");
const recBtn = document.getElementById("recBtn");
const player = document.getElementById("player");

for(let i=0;i<24;i++){
    const bar=document.createElement("div");
    bar.className="eq-bar";
    barsContainer.appendChild(bar);
}

const bars = document.querySelectorAll(".eq-bar");

function animateBars(stream){
    const audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    source.connect(analyser);
    analyser.fftSize = 64;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    function draw(){
        if(!isRecording) return;
        analyser.getByteFrequencyData(dataArray);
        bars.forEach((bar,i)=>{
            const value = dataArray[i] || 0;
            bar.style.height = (value/255*60)+"px";
        });
        requestAnimationFrame(draw);
    }
    draw();
}

recBtn.onclick = async () => {
    if(!isRecording){
        const stream = await navigator.mediaDevices.getUserMedia({audio:true});
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];
        isRecording = true;
        recBtn.textContent="Stop Recording";

        animateBars(stream);

        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = e => {
            const blob = new Blob(audioChunks,{type:"audio/webm"});
            player.src = URL.createObjectURL(blob);
        };
    }else{
        mediaRecorder.stop();
        isRecording = false;
        recBtn.textContent="Start Recording";
        bars.forEach(bar=>bar.style.height="10px");
    }
};
</script>
""", height=260)
