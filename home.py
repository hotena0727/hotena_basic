# home.py
# ============================================================
# ✅ Hotena Hub (A안: 상단 네비만 사용)
# - rt/at를 링크에 붙이지 않음 (URL 노출/길이 문제 방지)
# - core.py에서 로그인/쿠키/세션 복원은 "항상" 동일 위치에서 호출
# - active 처리 포함
# ============================================================

from __future__ import annotations

import importlib
import time
import streamlit as st

import core


# ----------------------------
# Page config (가장 먼저)
# ----------------------------
st.set_page_config(
    page_title="하테나일본어",
    page_icon="🟦",
    layout="centered",
)


# ----------------------------
# ✅ core 호출 위치: 여기 고정 (절대 아래로 내리지 않기)
# ----------------------------
core.ensure_core()
core.refresh_session_from_cookie_if_needed(force=True)
try:
    core._hide_streamlit_component_iframes()
except Exception:
    pass

# (디버그가 필요하면 활성화)
# st.write("DEBUG: home.py loaded", time.time())


# ----------------------------
# Router
# ----------------------------
def _get_page() -> str:
    try:
        p = st.query_params.get("p", "home")
        if isinstance(p, str) and p:
            return p
    except Exception:
        pass
    return "home"


def _set_page(p: str) -> None:
    try:
        st.query_params["p"] = p
    except Exception:
        pass


# ----------------------------
# Top Nav (A안)
# ----------------------------
def render_topnav(active: str) -> None:
    # ✅ 링크는 p만 (rt/at 없음)
    items = [
        ("home", "🏠", "홈"),
        ("word", "📘", "단어"),
        ("kanji", "🈶", "한자"),
        ("talk", "💬", "회화"),
        ("my", "👤", "마이"),
    ]

    st.markdown(
        """
<style>
/* 상단 네비 고정 */
#__HOTENA_TOPNAV__{
  position: sticky;
  top: 0;
  z-index: 2147483647;
  display:flex;
  gap: 6px;
  align-items:center;
  justify-content: space-between;
  padding: 10px 10px 8px 10px;
  margin: 0 0 8px 0;
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0,0,0,.06);
}

/* 왼쪽: 플랜 pill */
#__HOTENA_PLAN__{
  display:flex; align-items:center; gap:8px;
  padding:6px 10px;
  border-radius: 999px;
  border:1px solid rgba(0,0,0,.10);
  background: rgba(0,0,0,.02);
  font-size: .84rem;
  white-space: nowrap;
  user-select:none;
}

/* 오른쪽: 메뉴 */
.hub-topnav{
  display:flex;
  gap: 6px;
  align-items:center;
  justify-content:flex-end;
  flex-wrap: nowrap;
}

.hub-topnav a{
  display:flex;
  align-items:center;
  gap:6px;
  padding: 8px 10px;
  border-radius: 999px;
  text-decoration:none;
  border: 1px solid rgba(0,0,0,.08);
  background: rgba(0,0,0,.02);
  color: rgba(0,0,0,.88);
  font-weight: 700;
  font-size: .88rem;
}

.hub-topnav a .ic{ font-size: 1rem; }
.hub-topnav a.active{
  background: rgba(0,0,0,.08);
  border-color: rgba(0,0,0,.14);
}

@media (max-width: 480px){
  #__HOTENA_TOPNAV__{ padding: 10px 8px 8px 8px; }
  .hub-topnav a{ padding: 8px 9px; font-size:.86rem; }
  #__HOTENA_PLAN__{ font-size:.82rem; padding:6px 9px; }
}
</style>
        """,
        unsafe_allow_html=True,
    )

    # plan text
    plan = (st.session_state.get("user_plan") or "").strip().lower()
    if plan == "pro":
        plan_txt = "Pro 이용 중입니다"
    else:
        plan_txt = "Free 이용 중입니다"

    # nav html
    links = []
    for p, ic, label in items:
        cls = "active" if p == active else ""
        links.append(f'<a href="?p={p}" target="_self" class="{cls}"><span class="ic">{ic}</span><span>{label}</span></a>')

    st.markdown(
        f"""
<div id="__HOTENA_TOPNAV__">
  <div id="__HOTENA_PLAN__">{plan_txt}</div>
  <div class="hub-topnav">
    {''.join(links)}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------
# Pages
# ----------------------------
def render_home() -> None:
    st.markdown("## 하테나일본어")
    st.caption("상단 메뉴로 이동해 주세요.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("단어 훈련", use_container_width=True):
            _set_page("word")
            st.rerun()
    with c2:
        if st.button("한자 훈련", use_container_width=True):
            _set_page("kanji")
            st.rerun()
    with c3:
        if st.button("회화 훈련", use_container_width=True):
            _set_page("talk")
            st.rerun()


def _run_page(module_name: str, fn_candidates: tuple[str, ...]) -> None:
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        st.error(f"페이지 모듈을 불러오지 못했습니다: {module_name}")
        st.exception(e)
        return

    for fn in fn_candidates:
        if hasattr(mod, fn):
            try:
                getattr(mod, fn)()
                return
            except Exception as e:
                st.error(f"{module_name}.{fn} 실행 중 오류")
                st.exception(e)
                return

    st.error(f"{module_name} 안에서 실행 함수({', '.join(fn_candidates)})를 찾지 못했습니다.")


def main():
    page = _get_page()
    render_topnav(page)

    if page == "home":
        render_home()
    elif page == "word":
        _run_page("word", ("render", "render_word", "main"))
    elif page == "kanji":
        _run_page("kanji", ("render", "render_kanji", "main"))
    elif page == "talk":
        _run_page("talk", ("render", "render_talk", "main"))
    elif page == "my":
        _run_page("mypage", ("render", "render_mypage", "main"))
    else:
        _set_page("home")
        st.rerun()


if __name__ == "__main__":
    main()
