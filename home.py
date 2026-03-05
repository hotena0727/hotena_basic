
# --- HOTENA HOME (stable layout version) ---
import streamlit as st
import core

# 1️⃣ Always first
st.set_page_config(
    page_title="HOTENA",
    page_icon="🇯🇵",
    layout="centered"
)

# 2️⃣ Apply CSS immediately
core.apply_global_ui_css()

# 3️⃣ Initialize core
core.ensure_core()

# 4️⃣ Render navigation
core.render_top_nav("home")

# 5️⃣ Page content
st.title("HOTENA")
st.write("Hotena platform is running.")
