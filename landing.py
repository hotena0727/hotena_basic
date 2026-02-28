# landing.py - Hotena Landing (design-match) v4
from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

def _b64(path: Path) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception:
        return ""

def landing_ui(
    *,
    assets_dir: str | Path = "assets",
    title_left: str = "하테나쌤과 함께",
    headline: str = "하루 5분, 회화 루틴",
    tagline: str = "짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.",
    card_title: str = "시작하기",
    card_subtitle: str = "로그인 후 바로 홈허브로 이동합니다.",
    show_mode_toggle: bool = True,
    default_mode: str = "로그인",   # "회원가입"
):
    """
    Landing page UI.
    Compatible with home.py calling: landing_ui(assets_dir='assets')
    Returns: (email, password, mode, submitted)
    """
    ASSETS = Path(assets_dir)

    # Streamlit config (safe if already set)
    try:
        st.set_page_config(page_title="Hotena", layout="wide")
    except Exception:
        pass

    bg64 = _b64(ASSETS / "landing_bg.png")
    sensei_path = ASSETS / "hotena_sensei.png"

    bg_css = ""
    if bg64:
        bg_css = f"""
        .stApp {{
          background-image: url('data:image/png;base64,{bg64}');
          background-size: cover;
          /* ✅ keep clouds visible on first view */
          background-position: center 82%;
          background-repeat: no-repeat;
        }}
        """

    st.markdown(
        f"""
<style>
/* ---- hard reset ---- */
html, body {{
  height: 100%;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;  /* ✅ no scroll on desktop */
}}

[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
  visibility: hidden !important;
  height: 0 !important;
}}

.block-container {{
  padding: 0 !important;
  margin: 0 !important;
  max-width: 100% !important;
}}

[data-testid="stAppViewContainer"] {{
  padding: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
}}

{bg_css}

/* ---- page frame ---- */
.h-landing {{
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: clamp(18px, 3vh, 42px) clamp(18px, 3.2vw, 64px);
  position: relative;
}}

.h-inner {{
  width: min(1320px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: clamp(22px, 3.4vw, 54px);
  align-items: center;
}}

@media (max-width: 980px) {{
  html, body {{ overflow: auto !important; }}
  [data-testid="stAppViewContainer"] {{ overflow: auto !important; }}
  .h-landing {{ height: auto; min-height: 100vh; padding-bottom: 22px; }}
  .h-inner {{ grid-template-columns: 1fr; gap: 18px; }}
}}

.h-cap {{
  height: 16px;
  width: min(520px, 100%);
  border-radius: 999px;
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 10px 30px rgba(0,0,0,0.06);
  margin-bottom: 14px;
}}

.h-left h1 {{
  margin: 0;
  font-size: clamp(34px, 3.4vw, 54px);
  font-weight: 900;
  letter-spacing: -0.02em;
  line-height: 1.06;
}}
.h-left h2 {{
  margin: 10px 0 12px 0;
  font-size: clamp(22px, 2.1vw, 32px);
  font-weight: 900;
  letter-spacing: -0.02em;
  opacity: .95;
}}
.h-left p {{
  margin: 0 0 18px 0;
  font-size: 1.02rem;
  opacity: .86;
}}

.h-sensei {{
  margin-top: 10px;
  width: min(460px, 92%);
}}

.h-pills {{
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}}
.h-pill {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.70);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 10px 24px rgba(0,0,0,0.05);
  font-size: .95rem;
  opacity: .92;
}}
.h-dot {{
  width: 10px;
  height: 10px;
  border-radius: 99px;
  background: rgba(0,0,0,0.25);
}}

/* ---- right card ---- */
.h-card {{
  width: min(720px, 100%);
  background: rgba(255,255,255,0.58);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 22px;
  padding: 26px 26px 20px 26px;
  box-shadow: 0 22px 70px rgba(0,0,0,0.10);
}}

.h-card h3 {{
  margin: 0 0 6px 0;
  font-size: 1.9rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}}
.h-card .sub {{
  margin: 0 0 18px 0;
  opacity: .78;
  font-size: .98rem;
}}

.h-notes {{
  margin-top: 12px;
  opacity: .72;
  font-size: .92rem;
}}
.h-notes ul {{
  margin: 0;
  padding-left: 18px;
}}
.h-notes li {{
  margin: 6px 0;
}}

/* ---- Streamlit widget skinning (inside card) ---- */
.h-card [data-testid="stForm"] {{
  padding: 0 !important;
  border: 0 !important;
}}

.h-card label {{
  font-weight: 700 !important;
  opacity: .88;
}}

.h-card input {{
  height: 46px !important;
  border-radius: 12px !important;
  border: 1px solid rgba(0,0,0,0.10) !important;
  background: rgba(255,255,255,0.62) !important;
}}

.h-card input:focus {{
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(50, 50, 50, 0.08) !important;
}}

.h-card [data-testid="stTextInput"] > div {{
  padding: 0 !important;
}}

.h-card [data-testid="stRadio"] {{
  padding-top: 4px;
}}

.h-card [data-testid="stRadio"] label {{
  font-weight: 700 !important;
}}

.h-card button[kind="primary"] {{
  height: 48px !important;
  border-radius: 12px !important;
  border: 1px solid rgba(0,0,0,0.10) !important;
  background: rgba(255,255,255,0.72) !important;
  color: rgba(0,0,0,0.84) !important;
  font-weight: 900 !important;
  box-shadow: 0 12px 26px rgba(0,0,0,0.08) !important;
}}

.h-card button[kind="primary"]:hover {{
  transform: translateY(-1px);
}}

</style>
""",
        unsafe_allow_html=True,
    )

    # ---- layout ----
    st.markdown('<div class="h-landing"><div class="h-inner">', unsafe_allow_html=True)

    left, right = st.columns([1.05, 1.0], gap="large")

    with left:
        st.markdown('<div class="h-left">', unsafe_allow_html=True)
        st.markdown('<div class="h-cap"></div>', unsafe_allow_html=True)
        st.markdown(f"<h1>{title_left}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h2>{headline}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p>{tagline}</p>", unsafe_allow_html=True)

        if sensei_path.exists():
            st.image(str(sensei_path), width=430)
        else:
            st.warning(f"assets/hotena_sensei.png 파일이 없습니다: {sensei_path.as_posix()}")

        st.markdown(
            """
<div class="h-pills">
  <div class="h-pill"><span class="h-dot"></span> 듣기</div>
  <div class="h-pill"><span class="h-dot"></span> 말하기</div>
  <div class="h-pill"><span class="h-dot"></span> 스마트코치</div>
  <div class="h-pill"><span class="h-dot"></span> 오늘의 루틴</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="h-card">', unsafe_allow_html=True)
        st.markdown('<div class="h-cap"></div>', unsafe_allow_html=True)
        st.markdown(f"<h3>{card_title}</h3>", unsafe_allow_html=True)
        st.markdown(f'<div class="sub">{card_subtitle}</div>', unsafe_allow_html=True)

        with st.form("landing_login_form", clear_on_submit=False):
            email = st.text_input("이메일", key="landing_email")
            password = st.text_input("비밀번호", type="password", key="landing_pw")
            mode = default_mode
            if show_mode_toggle:
                mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True, index=0 if default_mode=="로그인" else 1)
            submitted = st.form_submit_button("확인", use_container_width=True)

        st.markdown(
            """
<div class="h-notes">
  <ul>
    <li>회원가입 후 이메일 인증이 필요할 수 있어요.</li>
    <li>비밀번호는 6자 이상을 권장합니다.</li>
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    return email, password, mode, submitted
