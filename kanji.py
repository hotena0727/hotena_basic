# kanji.py
from __future__ import annotations
import streamlit as st
from pathlib import Path

def render_kanji():
    # Runs the original kanji app (copied as kanji_impl.py)
    impl = Path(__file__).with_name("kanji_impl.py")
    g = {"__name__": "__main__", "__file__": str(impl)}
    st.session_state["_HUB_EMBED"] = True
    code = impl.read_text(encoding="utf-8", errors="replace")
    code = code.replace(
        "st.set_page_config(",
        "if not st.session_state.get('_embedded_set_page_config_done'):\n    st.session_state['_embedded_set_page_config_done']=True\n    st.set_page_config("
    )
    exec(compile(code, str(impl), "exec"), g, g)
