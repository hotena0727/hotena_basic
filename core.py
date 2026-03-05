
import streamlit as st

def apply_global_ui_css():
    st.markdown("""
<style>
header {visibility:hidden;}
header[data-testid="stHeader"]{display:none;}

[data-testid="stAppViewContainer"]{
    padding-top:0rem !important;
}

[data-testid="block-container"]{
    padding-top:0rem !important;
    margin-top:0rem !important;
}

.block-container{
    padding-top:0rem !important;
    margin-top:0rem !important;
}

footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

def ensure_core():
    pass

def render_top_nav(active="home"):
    st.markdown(
        f"""
        <div style="position:sticky;top:0;background:white;padding:8px 0;border-bottom:1px solid #eee;">
        <b>HOTENA</b> | <span style="color:#888;">{active}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
