# landing.py
from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st


def _img_to_data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    b = p.read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")


def landing_ui(
    *,
    assets_dir: str = "assets",
    bg_filename: str = "landing_bg.png",
    char_filename: str = "hotena_sensei.png",
) -> tuple[str, str, str, bool]:
    """
    Returns: (email, password, mode, submitted)
      - mode: "로그인" or "회원가입"
    """
    bg_uri = _img_to_data_uri(str(Path(assets_dir) / bg_filename))
    char_path = str(Path(assets_dir) / char_filename)

    # --- Full-bleed landing look (no Streamlit chrome) ---
    st.markdown(
        f"""
<style>
/* Hide Streamlit chrome */
header, footer, [data-testid="stToolbar"] {{ display:none !important; }}
/* Remove top padding */
section.main > div {{ padding-top: 0rem !important; }}

/* Background */
.stApp {{
  background: {"url(" + bg_uri + ") center/cover no-repeat fixed" if bg_uri else "linear-gradient(180deg,#FAF8F4,#F2EEE7)"};
}}

/* Landing wrapper */
.landing-wrap {{
  min-height: 100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  padding: 2.2rem 1.2rem;
}}

.landing-inner {{
  width: min(1120px, 100%);
  display:flex;
  gap: 56px;
  align-items:center;
  justify-content:space-between;
}}

.landing-left {{
  flex: 1 1 52%;
}}
.landing-right {{
  flex: 1 1 48%;
}}

/* Card */
.landing-card {{
  width: 100%;
  border-radius: 22px;
  padding: 26px 26px 18px;
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(0,0,0,0.07);
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
  backdrop-filter: blur(8px);
}}

.landing-h1 {{
  font-size: 1.55rem;
  font-weight: 900;
  margin: 0 0 .25rem 0;
}}
.landing-sub {{
  font-size: 0.98rem;
  opacity: .75;
  margin: 0 0 1.0rem 0;
}}
.landing-kicker {{
  font-size: 1.15rem;
  font-weight: 850;
  margin: 0 0 .35rem 0;
}}
.landing-desc {{
  font-size: 0.98rem;
  opacity: .80;
  margin: 0 0 1.0rem 0;
}}

.pillrow {{
  display:flex; gap:10px; flex-wrap:wrap;
  margin-top: 14px;
}}
.pill {{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.70);
  border: 1px solid rgba(0,0,0,0.06);
  font-size: 0.92rem;
  opacity: .92;
}}

.smallnote {{
  font-size: 0.85rem;
  opacity: .70;
  margin-top: .6rem;
}}

/* Make Streamlit inputs a bit rounder inside this page */
.landing-card [data-baseweb="input"] input {{
  border-radius: 14px !important;
}}
.landing-card button {{
  border-radius: 14px !important;
  font-weight: 800 !important;
}}

/* Responsive: stack */
@media (max-width: 860px) {{
  .landing-inner {{
    flex-direction: column;
    gap: 22px;
    align-items: stretch;
  }}
  .landing-left, .landing-right {{ flex: 1 1 auto; }}
}}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="landing-wrap"><div class="landing-inner">', unsafe_allow_html=True)

    # LEFT
    st.markdown('<div class="landing-left">', unsafe_allow_html=True)
    st.markdown('<div class="landing-kicker">하테나쌤과 함께<br/>하루 5분, 회화 루틴</div>', unsafe_allow_html=True)
    st.markdown('<div class="landing-desc">짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.</div>', unsafe_allow_html=True)
    if Path(char_path).exists():
        st.image(char_path, use_container_width=False, width=310)
    st.markdown(
        """
<div class="pillrow">
  <div class="pill">🎧 듣기</div>
  <div class="pill">🗣️ 말하기</div>
  <div class="pill">🧠 스마트코치</div>
  <div class="pill">✅ 오늘의 루틴</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT
    st.markdown('<div class="landing-right"><div class="landing-card">', unsafe_allow_html=True)
    st.markdown('<div class="landing-h1">시작하기</div>', unsafe_allow_html=True)
    st.markdown('<div class="landing-sub">로그인 후 바로 홈 허브로 이동합니다.</div>', unsafe_allow_html=True)

    with st.form("landing_login_form", clear_on_submit=False):
        email = st.text_input("이메일", key="landing_email")
        pw = st.text_input("비밀번호", type="password", key="landing_pw")
        mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True, key="landing_mode")
        submitted = st.form_submit_button("확인", use_container_width=True)

    st.markdown(
        """
<div class="smallnote">
  * 회원가입 후 이메일 인증이 필요할 수 있어요.<br/>
  * 비밀번호는 6자 이상을 권장합니다.
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

    return email, pw, mode, submitted
