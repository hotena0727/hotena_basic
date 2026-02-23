# ============================================================
# ✅ HOTENA HOME - 최종 안정판
# - 홈 허브 유지
# - 상단 네비 추가
# - 좌측 메뉴 제거
# ============================================================

from __future__ import annotations
import streamlit as st
import importlib

# ------------------------------------------------------------
# 1️⃣ 기본 설정 + 좌측 메뉴 제거
# ------------------------------------------------------------
st.set_page_config(page_title="Hotena", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="stSidebarNav"] { display: none !important; }

#floating-menu, .floating-menu, .left-floating, .left-menu {
    display: none !important;
}

.main .block-container {
    padding-top: 0.8rem;
}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# 2️⃣ 상단 네비
# ------------------------------------------------------------
def render_top_nav():
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
        background: rgba(47,128,237,0.1);
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


# ------------------------------------------------------------
# 3️⃣ 라우팅
# ------------------------------------------------------------
def get_page():
    page = st.query_params.get("page", "home")
    if isinstance(page, list):
        page = page[0]
    return page.lower()


def run_module(name):
    mod = importlib.import_module(name)

    for fn_name in ("render", "main", "run", "render_page",
                    "render_word", "render_kanji",
                    "render_talk", "render_mypage"):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            return fn()

    st.error(f"'{name}' 모듈에서 실행 함수(render/main/run 등)를 찾지 못했습니다.")


# ------------------------------------------------------------
# 4️⃣ 실행
# ------------------------------------------------------------
render_top_nav()

page = get_page()

if page == "home":
    # ✅ 여기에 기존 홈 허브 코드 그대로 붙여넣으세요
    st.markdown("<!-- 기존 홈 허브 코드 영역 -->", unsafe_allow_html=True)

else:
    module_map = {
        "word": "words",
        "kanji": "kanji",
        "talk": "talk",
        "mypage": "mypage",
    }

    run_module(module_map.get(page, "words"))
