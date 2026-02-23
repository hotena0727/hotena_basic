# ============================================================
# ✅ HOTENA CORE - 통합 공통 UI 모듈
# - 상단 네비 (통합 메뉴)
# - 좌측 사이드바/플로팅 완전 제거
# ============================================================

from __future__ import annotations
import streamlit as st


# ------------------------------------------------------------
# 1️⃣ 전역 UI 주입 (사이드바 제거 + 공통 스타일)
# ------------------------------------------------------------
def inject_global_ui():
    if st.session_state.get("_global_ui_injected"):
        return
    st.session_state["_global_ui_injected"] = True

    st.markdown("""
    <style>
    /* ✅ Streamlit 기본 사이드바 제거 */
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="stSidebarNav"] { display: none !important; }

    /* ✅ 혹시 남아있는 좌측 플로팅 메뉴 제거 */
    #floating-menu, .floating-menu, .left-floating, .left-menu, .sidebar-float {
        display: none !important;
    }

    /* 본문 상단 여백 안정화 */
    .main .block-container {
        padding-top: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------
# 2️⃣ 상단 통합 네비
# ------------------------------------------------------------
def render_top_nav():
    inject_global_ui()

    st.markdown("""
    <style>
    .top-nav {
        position: sticky;
        top: 0;
        z-index: 9999;
        background: rgba(255,255,255,0.96);
        backdrop-filter: blur(8px);
        border-bottom: 1px solid rgba(0,0,0,0.06);
    }
    .top-nav .inner {
        max-width: 1100px;
        margin: 0 auto;
        padding: 10px 14px 8px 14px;
        display: flex;
        justify-content: center;
        gap: 34px;
        font-weight: 700;
        font-size: 15px;
    }
    .top-nav a {
        text-decoration: none;
        color: #222;
        padding: 6px 12px;
        border-radius: 10px;
    }
    .top-nav a:hover {
        background: rgba(47,128,237,0.10);
        color: #2f80ed;
    }
    </style>

    <div class="top-nav">
      <div class="inner">
        <a href="?page=home">홈</a>
        <a href="?page=word">단어</a>
        <a href="?page=kanji">한자</a>
        <a href="?page=talk">회화</a>
        <a href="?page=mypage">마이페이지</a>
      </div>
    </div>
    """, unsafe_allow_html=True)
