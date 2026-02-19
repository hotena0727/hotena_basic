# mypage.py
from __future__ import annotations

from pathlib import Path
import runpy
import streamlit as st
from theme_hotena import apply_hotena_theme
apply_hotena_theme()

# This file intentionally reuses the existing Kanji app (app.py) My Page UI/logic
# without duplicating code. It acts as an independent entry for the HUB.
st.session_state["HUB_MODE"] = True
st.session_state["hub_target"] = "my"
st.session_state["page"] = "my"

runpy.run_path(str((Path(__file__).resolve().parent / "app.py")), run_name="__main__")