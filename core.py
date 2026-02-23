# ============================================================
# ✅ HOTENA CORE (v2) - 통합 공통 UI 모듈
# - 상단 네비(통합 메뉴) 렌더
# - 좌측 사이드바/플로팅 강제 숨김(CSS)
#
# ⚠️ 중요:
# - core.py는 "공통 모듈"이라 자동으로 화면에 나타나지 않습니다.
# - 각 페이지의 "첫 Streamlit 출력 전에" 아래 2줄을 호출해야 합니다.
#
#   import core
#   core.render_top_nav()
#
# ============================================================

from __future__ import annotations
import streamlit as st


def _inject_css():
    # ✅ 여러 번 호출되어도 안전(중복 주입 OK)
    st.markdown(
        """
<style>
/* ✅ Streamlit 기본 Sidebar 제거 */
section[data-testid="stSidebar"] { display:none !important; }
div[data-testid="stSidebarNav"] { display:none !important; }

/* ✅ 레거시/커스텀 좌측 플로팅(이름 모를 때 대비) */
#floating-menu, .floating-menu, .left-floating, .left-menu, .sidebar-float { display:none !important; }

/* ✅ '왼쪽에 고정된 fixed 요소'를 강하게 숨김 (플로팅이 DOM으로 박혀 있을 때) */
div[style*="position: fixed"][style*="left"] { display:none !important; }
div[style*="position:fixed"][style*="left"] { display:none !important; }

/* ✅ 본문 상단 여백 */
.main .block-container { padding-top: 0.8rem; }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_top_nav():
    """상단 통합 네비 + 좌측 메뉴 제거 CSS 주입"""
    _inject_css()

    st.markdown(
        """
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
        """,
        unsafe_allow_html=True,
    )


def debug_badge(text: str = "CORE LOADED"):
    """적용 확인용(원할 때만 호출)"""
    _inject_css()
    st.caption(f"✅ {text}")
