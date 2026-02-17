# home.py
# ============================================================
# ✅ Home page (Streamlit)
# - render_home(user, user_plan)
# - Designed for "왕초보 탈출 하테나일본어" single-file router style
# ============================================================

from __future__ import annotations

import streamlit as st


def render_home(user=None, user_plan: str = "free"):
    """
    홈 화면(홈페이지)

    Parameters
    ----------
    user : object | None
        로그인 사용자 객체(없으면 None). 보통 user.email 속성이 있으면 표시합니다.
    user_plan : str
        "free" | "pro"
    """

    # ----------------------------
    # Hero
    # ----------------------------
    st.markdown("## は  왕초보 탈출 · 하테나일본어")
    st.caption("매일 10문제, 가볍게. 꾸준함이 실력입니다.")

    # Login status badge
    if user:
        email = getattr(user, "email", "") or ""
        st.success(f"로그인됨: {email}  ·  플랜: {str(user_plan).upper()}")
    else:
        st.info("로그인하면 학습 기록/오답노트/정복(맞힌 단어 제외)이 저장됩니다.")

    st.markdown("---")

    # ----------------------------
    # Quick actions
    # ----------------------------
    st.markdown("### 🚀 오늘의 학습, 바로 시작")
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📝 퀴즈 시작", use_container_width=True):
            st.session_state["page"] = "quiz"
            st.rerun()

    with c2:
        if st.button("📒 오답노트", use_container_width=True):
            st.session_state["page"] = "mypage"
            st.session_state["mypage_tab"] = "wrongs"
            st.rerun()

    with c3:
        if st.button("⚙️ 학습 설정", use_container_width=True):
            st.session_state["page"] = "mypage"
            st.session_state["mypage_tab"] = "settings"
            st.rerun()

    st.markdown("---")

    # ----------------------------
    # How to use
    # ----------------------------
    st.markdown("### 📌 사용 방법 (딱 3단계)")
    st.markdown(
        """
- **1) 품사 선택**: 명사/동사/형용사 등  
- **2) 유형 선택**: 발음 / 뜻 / 한→일  
- **3) 10문제 풀이**: 오늘 분량을 가볍게 끝내기
        """.strip()
    )

    # ----------------------------
    # Feature highlights
    # ----------------------------
    st.markdown("### ✨ 들어있는 기능")
    f1, f2 = st.columns(2)

    with f1:
        st.markdown(
            """
**✅ 정복(맞힌 단어 제외)**  
한 번 맞힌 단어는 자동으로 줄여서 “새 단어” 위주로 반복하게 합니다.
            """.strip()
        )
        st.markdown(
            """
**✅ 오답노트 + 오답만 다시풀기**  
틀린 것만 따로 모아서 재학습 → 점수가 빠르게 오릅니다.
            """.strip()
        )

    with f2:
        st.markdown(
            """
**✅ 모바일 최적화 + 사운드**  
짧은 시간에 집중하기 좋게 구성합니다.
            """.strip()
        )
        st.markdown(
            """
**✅ 로그인/기록 저장**  
학습 기록이 쌓이면 “꾸준함”이 눈으로 보입니다.
            """.strip()
        )

    st.markdown("---")

    # ----------------------------
    # Plan (FREE/PRO) notice
    # ----------------------------
    st.markdown("### 🧩 이용 플랜")
    p1, p2 = st.columns(2)

    with p1:
        st.markdown("**FREE**")
        st.markdown("- 하루 1페이지(10문) 학습")
        st.markdown("- 기본 퀴즈 기능")
        st.markdown("- (선택) 로그인 시 기록 저장")

    with p2:
        st.markdown("**PRO**")
        st.markdown("- 무제한 페이지(새 문제 계속)")
        st.markdown("- 오답노트 전체/오답만 반복 강화")
        st.markdown("- 정복(맞힌 단어 제외) 고도화")

    if str(user_plan).lower() == "free":
        st.warning("FREE는 딱 10문제(1페이지)만 풀 수 있어요. 더 풀려면 PRO가 필요합니다.")
        if st.button("⭐ PRO 안내 보기", use_container_width=True):
            st.session_state["page"] = "mypage"
            st.session_state["mypage_tab"] = "plan"
            st.rerun()

    st.markdown("---")

    # ----------------------------
    # Motivational footer
    # ----------------------------
    st.markdown("### ☑️ 오늘의 한마디")
    st.write("공부는 길게가 아니라, **매일** 가는 게 이깁니다. 오늘 10문제면 충분합니다.")
