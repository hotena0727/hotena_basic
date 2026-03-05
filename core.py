
# --- HOTENA CORE (stable UI version) ---
import streamlit as st

def apply_global_ui_css():
    st.markdown("""
<style>

/* Hide Streamlit header */
header {visibility:hidden;}
header[data-testid="stHeader"] {display:none !important;}

/* Remove top spacing */
[data-testid="stAppViewContainer"]{
    padding-top:0rem !important;
}

[data-testid="block-container"]{
    padding-top:0rem !important;
    margin-top:0rem !important;
}

/* Older Streamlit compatibility */
.block-container{
    padding-top:0rem !important;
    margin-top:0rem !important;
}

/* Hide footer */
footer {visibility:hidden;}

/* Prevent layout jump */
html, body, [class*="css"]  {
    margin-top:0px !important;
    padding-top:0px !important;
}

</style>
""", unsafe_allow_html=True)


def render_top_nav(active="home"):
    nav_html = f"""
<div style="
position:sticky;
top:0;
z-index:999;
background:white;
border-bottom:1px solid #eee;
padding:10px 0;
font-weight:600;
">
&nbsp;&nbsp;HOTENA &nbsp;&nbsp;|&nbsp;&nbsp; {active}
</div>
"""
    st.markdown(nav_html, unsafe_allow_html=True)


def ensure_core():
    # placeholder for compatibility with existing modules
    pass
