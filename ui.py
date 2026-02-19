from __future__ import annotations
import streamlit as st

APP_TITLE = "왕초보 탈출 하테나일본어"
APP_SLOGAN = "오늘도 10문제만."

def apply_global_styles():
    st.markdown(
        r"""
<style>
/* ✅ Layout width + top clipping fix */
.block-container{
  max-width: min(820px, 92vw) !important;
  padding-top: 2.7rem !important;
  padding-bottom: 2.0rem !important;
}

/* ✅ Hide Streamlit chrome */
header[data-testid="stHeader"]{visibility:hidden;height:0;}
footer{visibility:hidden;height:0;}
#MainMenu{visibility:hidden;}
[data-testid="stSidebar"]{display:none !important;}

/* ✅ Buttons - consistent */
.stButton > button{
  height: 52px;
  font-size: 16px;
  border-radius: 12px;
}

/* ✅ Header blocks */
.hub-title{text-align:center;font-size:26px;font-weight:700;margin:0 0 6px;}
.hub-subtitle{text-align:center;font-size:15px;color:rgba(0,0,0,0.62);margin:0 0 28px;}
.slimbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 12px;}
.slim-left{font-size:16px;font-weight:700;}
.slim-right{font-size:13px;color:rgba(0,0,0,0.55);}
.hr{height:1px;background:rgba(0,0,0,0.08);margin:14px 0 16px;}

/* ✅ Top nav */
.topnav{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin:0 0 10px;
}
.topnav button{
  height: 36px !important;
  font-size: 13px !important;
  border-radius: 999px !important;
  padding: 0 12px !important;
}
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

def top_menu(active: str | None = None):
    """
    Common menu for all training pages.
    active: one of "home","word","kanji","talk","mypage"
    """
    items = [
        ("home", "홈"),
        ("word", "단어"),
        ("kanji", "한자"),
        ("talk", "회화"),
        ("mypage", "마이페이지"),
        ("logout", "로그아웃"),
    ]

    # Use simple columns (no extra HTML wrappers) for maximum reliability.
    cols = st.columns(len(items))
    clicked = None
    for i, (key, label) in enumerate(items):
        disabled = (active == key)
        with cols[i]:
            if st.button(label, key=f"topnav_{key}", use_container_width=True, disabled=disabled):
                clicked = key
    return clicked
