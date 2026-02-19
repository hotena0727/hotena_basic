# hotena.py
from __future__ import annotations

import streamlit as st

import words
import kanji

st.set_page_config(page_title="하테나 통합 (hotena)", layout="centered", page_icon="🟦")

# ------------------------------------------------------------
# Unified launcher state
# ------------------------------------------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "home"

def _reset_common_state():
    # Prevent collisions between sub-apps that both use generic keys like 'page'
    for k in [
        "page",
        "quiz_page",
        "mode_in_app",
        "current_question",
        "q_idx",
        "idx",
        "selected",
        "answer",
        "score",
        "wrong_list",
        "wrongs",
        "last_result",
    ]:
        if k in st.session_state:
            st.session_state.pop(k, None)

def go(mode: str):
    if st.session_state.mode != mode:
        _reset_common_state()
    st.session_state.mode = mode
    st.rerun()

# ------------------------------------------------------------
# Simple home (NO sidebar)
# ------------------------------------------------------------
if st.session_state.mode == "home":
    st.markdown("## 🎯 훈련 선택")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.button("📘 단어 훈련", use_container_width=True, on_click=go, args=("words",))
    with c2:
        st.button("🈶 한자 훈련", use_container_width=True, on_click=go, args=("kanji",))
    with c3:
        st.button("💬 회화 훈련", use_container_width=True, on_click=go, args=("talk",))

    st.caption("표기 통일: 영문은 hotena, 한글은 하테나.")
    st.stop()

# ------------------------------------------------------------
# Top bar
# ------------------------------------------------------------
top1, top2 = st.columns([1, 3])
with top1:
    st.button("⬅️ 홈", use_container_width=True, on_click=go, args=("home",))
with top2:
    if st.session_state.mode == "words":
        st.markdown("### 📘 단어 훈련")
    elif st.session_state.mode == "kanji":
        st.markdown("### 🈶 한자 훈련")
    else:
        st.markdown("### 💬 회화 훈련")

# ------------------------------------------------------------
# Sub-app mounting
# ------------------------------------------------------------
if st.session_state.mode == "words":
    st.session_state["page"] = "home"
    words.render_words_app()
    st.stop()

if st.session_state.mode == "kanji":
    st.session_state["page"] = "home"
    kanji.render_kanji_app()
    st.stop()

# talk (placeholder)
st.info("회화 훈련은 아직 준비 중입니다 🙂")
st.button("⬅️ 홈으로", use_container_width=True, on_click=go, args=("home",))
