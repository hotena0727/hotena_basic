# main.py
# ============================================================
# ✅ Hatena Trainer Launcher (No sidebar)
# - Home with 3 buttons: Word / Kanji / Talk(coming soon)
# - Runs existing apps via runpy.run_path in the same Streamlit process
# - Sub-apps must avoid st.set_page_config when launched here (handled by __SUBAPP__ flag)
# ============================================================

from __future__ import annotations

from pathlib import Path
import runpy
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
WORD_APP = BASE_DIR / "hotena_basic_patched.py"
KANJI_APP = BASE_DIR / "app_patched.py"

st.set_page_config(page_title="하테나 트레이닝", layout="centered", page_icon="🟦")

# ✅ (선택) 사이드바 완전 숨김 + 상단 툴바 최소화
st.markdown(
    """
<style>
/* sidebar 완전 숨김 */
section[data-testid="stSidebar"]{ display:none !important; }
div[data-testid="stSidebarNav"]{ display:none !important; }

/* 상단 헤더 얇게 */
header[data-testid="stHeader"]{ height: 0rem !important; }
div[data-testid="stToolbar"]{ visibility: hidden !important; height: 0 !important; }

/* 컨테이너 위 여백 */
div[data-testid="stAppViewContainer"] .block-container{ padding-top: 1.1rem !important; }

/* 홈 버튼 스타일 */
.home-btn div.stButton > button{
  height: 54px !important;
  border-radius: 16px !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  border: 1px solid rgba(120,120,120,0.22) !important;
  background: rgba(255,255,255,0.04) !important;
}
.home-sub{ opacity:.75; font-size:13px; margin-top:6px; }
</style>
""",
    unsafe_allow_html=True,
)

def go_home():
    st.session_state["_launcher_app"] = "home"
    st.rerun()

def go_word():
    st.session_state["_launcher_app"] = "word"
    st.rerun()

def go_kanji():
    st.session_state["_launcher_app"] = "kanji"
    st.rerun()

def go_talk():
    st.session_state["_launcher_app"] = "talk"
    st.rerun()

app = st.session_state.get("_launcher_app", "home")

# ============================================================
# ✅ Home
# ============================================================
if app == "home":
    st.markdown("## 오늘의 훈련을 선택하세요")
    st.caption("단어 / 한자 / 회화(준비중)")
    st.markdown("<div class='home-btn'>", unsafe_allow_html=True)
    st.button("📘 단어 훈련", use_container_width=True, on_click=go_word)
    st.button("🀄 한자 훈련", use_container_width=True, on_click=go_kanji)
    st.button("💬 회화 훈련 (준비중)", use_container_width=True, on_click=go_talk)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# ✅ Talk (coming soon)
# ============================================================
if app == "talk":
    st.button("← 홈으로", on_click=go_home)
    st.markdown("## 💬 회화 훈련은 준비중입니다.")
    st.caption("조금만 더 다듬어서 곧 연결해둘게요 🙂")
    st.stop()

# ============================================================
# ✅ Sub-app runner
# ============================================================
st.button("← 홈으로", on_click=go_home)

target = WORD_APP if app == "word" else KANJI_APP

if not target.exists():
    st.error(f"파일을 찾지 못했습니다: {target.name}")
    st.stop()

# ✅ run sub app in the same process
runpy.run_path(str(target), run_name="__main__", init_globals={"__SUBAPP__": True})
