from __future__ import annotations
import streamlit as st

APP_TITLE = "왕초보 탈출 하테나일본어"
APP_SLOGAN = "오늘도 10문제만."

def apply_global_styles():
    # ✅ One place to lock the look & feel
    st.markdown(
        r"""
<style>
/* ✅ Layout width + top clipping fix */
.block-container{
  max-width: min(820px, 92vw) !important;
  padding-top: 3.0rem !important;
  padding-bottom: 2.0rem !important;
}

/* ✅ Hide Streamlit chrome */
header[data-testid="stHeader"]{visibility:hidden;height:0;}
footer{visibility:hidden;height:0;}
#MainMenu{visibility:hidden;}
[data-testid="stSidebar"]{display:none !important;}

/* ✅ Buttons - consistent */
.stButton > button{
  height: 54px;
  font-size: 16px;
  border-radius: 12px;
}

/* ✅ Subtle spacing helpers */
.hr{height:1px;background:rgba(0,0,0,0.08);margin:18px 0;}
.hub-title{text-align:center;font-size:26px;font-weight:700;margin:0 0 6px;}
.hub-subtitle{text-align:center;font-size:15px;color:rgba(0,0,0,0.62);margin:0 0 36px;}
.slimbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 16px;}
.slim-left{font-size:16px;font-weight:700;}
.slim-right{font-size:13px;color:rgba(0,0,0,0.55);}
</style>
""",
        unsafe_allow_html=True,
    )

def hub_header():
    st.markdown(f'<div class="hub-title">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hub-subtitle">{APP_SLOGAN}</div>', unsafe_allow_html=True)

def slim_header(section_title: str, right_text: str | None = None):
    rt = right_text or ""
    st.markdown(
        f'<div class="slimbar"><div class="slim-left">{section_title}</div><div class="slim-right">{rt}</div></div>',
        unsafe_allow_html=True,
    )

def hr():
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
