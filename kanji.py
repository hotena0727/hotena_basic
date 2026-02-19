from __future__ import annotations
import streamlit as st
from ui import top_nav
from gate import gate, consume

def render_kanji():
    top_nav()
    st.markdown("## 🈶 한자 훈련")

    gate("kanji")

    if st.button("새 문제 (10문)", use_container_width=True):
        consume("kanji")
        st.session_state["kanji_started"] = True
        st.rerun()

    if st.session_state.get("kanji_started"):
        for i in range(1, 11):
            st.radio(f"Q{i}. 漢字の読みは？", ["あ","い","う","え"], key=f"k_{i}")
        st.button("제출", use_container_width=True)
