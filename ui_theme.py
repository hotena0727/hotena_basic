# ui_theme.py
import streamlit as st

def apply_ui_theme():
    if st.session_state.get("_theme_done"):
        return
    st.session_state["_theme_done"] = True
    st.markdown(
        """
<style>
.block-container{max-width:760px !important; padding-top: 1.0rem !important;}
section[data-testid="stSidebar"], div[data-testid="collapsedControl"]{display:none !important;}
div[data-testid="stToolbar"], footer{visibility:hidden; height:0;}
</style>
""", unsafe_allow_html=True
    )
