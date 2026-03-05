
import streamlit as st
import core

st.set_page_config(
    page_title="HOTENA",
    page_icon="🇯🇵",
    layout="centered"
)

core.apply_global_ui_css()
core.ensure_core()

core.render_top_nav("home")

st.title("HOTENA Home")
st.write("Hotena platform is running.")
