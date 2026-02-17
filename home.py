# home.py
# ============================================================
# ✅ Hotena Basic Hub (no sidebar)
# - 3 buttons: 단어 / 한자 / 회화(준비중)
# - 단어: hotena_basic.py 실행
# - 한자: app.py 실행
# - 같은 Supabase/쿠키(=동일 로그인 세션) 공유를 위해
#   하위 앱의 cookies prefix를 "hotena_beginner_"로 통일합니다.
# ============================================================

from __future__ import annotations

from pathlib import Path
import runpy
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

WORD_APP = BASE_DIR / "hotena_basic.py"
KANJI_APP = BASE_DIR / "app.py"

# ✅ page_config는 앱 전체에서 1번만
if not st.session_state.get("_page_config_done"):
    st.set_page_config(page_title="하테나 훈련", layout="centered")
    st.session_state["_page_config_done"] = True

def _set_route(route: str):
    st.session_state["route"] = route
    st.rerun()

def _render_home():
    st.markdown("## 🏁 훈련을 선택해 주세요")
    st.caption("단어 · 한자 · 회화 3가지 중에서 골라 시작합니다.")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📘 단어 훈련", use_container_width=True):
            _set_route("word")
    with c2:
        if st.button("🈶 한자 훈련", use_container_width=True):
            _set_route("kanji")
    with c3:
        if st.button("💬 회화 훈련", use_container_width=True):
            _set_route("talk")

    st.divider()
    st.caption("※ 회화 훈련은 제작 중입니다.")

def _run_app(path: Path):
    if not path.exists():
        st.error(f"파일을 찾을 수 없습니다: {path.name}")
        st.stop()

    # ✅ 하위 앱이 st.set_page_config()를 다시 호출하지 않도록
    st.session_state["_page_config_done"] = True

    # ✅ 실행 (각 앱은 단일파일이라 runpy로 안전하게 라우팅)
    runpy.run_path(str(path), run_name="__main__")

route = st.session_state.get("route", "home")

if route == "home":
    _render_home()
    st.stop()

# 상단 Back 버튼(사이드바 없이)
if st.button("← 홈으로", use_container_width=True, key="btn_back_home"):
    _set_route("home")

st.divider()

if route == "word":
    _run_app(WORD_APP)
elif route == "kanji":
    _run_app(KANJI_APP)
else:
    st.markdown("## 💬 회화 훈련")
    st.info("준비 중입니다. 조금만 기다려 주세요 🙂")
    st.stop()
