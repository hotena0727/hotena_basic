# landing.py - Hotena Landing (fullscreen hero) v3 (no-scroll on PC)
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
    title: str = "시작하기",
    subtitle: str = "로그인 후 바로 홈허브로 이동합니다.",
    show_mode_toggle: bool = True,
    default_mode: str = "로그인",  # or "회원가입"
):
    """Fullscreen landing UI (Hotena).
    Compatible with home.py calling: landing_ui(assets_dir='assets')
    Returns: (email, password, mode, submitted)
    """
    ASSETS_DIR = Path(assets_dir)

    # If home.py already called set_page_config, Streamlit may warn; it's fine.
    try:
        st.set_page_config(page_title="Hotena", layout="wide")
    except Exception:
        pass

    bg_path = ASSETS_DIR / "landing_bg.png"
    bg64 = _b64(bg_path)
    bg_css = ""
    if bg64:
        bg_css = f"""
        .stApp {{
            background-image: url('data:image/png;base64,{bg64}');
            background-size: cover;
            background-position: center 84%;
            background-repeat: no-repeat;
        }}
        """

    st.markdown(
        f"""
<style>
html, body {{
  height: 100%;
  margin: 0 !important;
  padding: 0 !important;
}}

/* hide streamlit chrome */
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
  visibility: hidden !important;
  height: 0 !important;
}}

/* remove container padding */
.block-container {{
  padding: 0 !important;
  margin: 0 !important;
  max-width: 100% !important;
}}

[data-testid="stAppViewContainer"] {{
  padding: 0 !important;
  margin: 0 !important;
}}

{bg_css}

/* ---- Landing layout ---- */
.landing-wrapper {{
  height: 100vh;                 /* exact viewport height */
  overflow: hidden;              /* prevent scroll by wrapper */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(14px, 2.6vh, 40px) clamp(14px, 3.2vw, 64px);
  box-sizing: border-box;
  position: relative;
}}

.landing-inner {{
  width: 100%;
  max-width: 1240px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 52px;
}}

.hero-copy h1 {{
  margin: 0 0 10px 0;
  font-size: 2.05rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}}
.hero-copy p {{
  margin: 0 0 16px 0;
  font-size: 1.05rem;
  opacity: .85;
}}

.login-card {{
  width: min(520px, 92vw);
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 20px;
  padding: 24px 24px 18px 24px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.08);
}}
.login-topbar {{
  height: 14px;
  border-radius: 999px;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(0,0,0,0.06);
  margin-bottom: 14px;
}}

/* notes pinned inside hero so height doesn't grow */
.landing-notes {{
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 10px;
  width: min(1240px, calc(100vw - 24px));
  opacity: .74;
  font-size: .92rem;
}}
.landing-notes ul {{
  margin: 0;
  padding-left: 18px;
}}

/* mobile */
@media (max-width: 980px) {{
  .landing-wrapper {{
    height: auto;
    min-height: 100vh;
    overflow: visible;
    padding-bottom: 22px;
  }}
  .landing-inner {{
    flex-direction: column;
    gap: 22px;
    text-align: center;
  }}
  .login-card {{
    width: min(560px, 94vw);
  }}
  .landing-notes {{
    position: static;
    transform: none;
    left: auto;
    bottom: auto;
    width: min(560px, 94vw);
    margin: 6px auto 0 auto;
  }}
}}

/* hard stop scrolling on desktop: Streamlit sometimes scrolls a container */
@media (min-width: 981px) {{
  body, html {{
    overflow: hidden !important;
  }}
  [data-testid="stAppViewContainer"] {{
    overflow: hidden !important;
  }}
}}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="landing-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="landing-inner">', unsafe_allow_html=True)

    left, right = st.columns([1.05, 1.0], gap="large")

    with left:
        st.markdown('<div class="hero-copy">', unsafe_allow_html=True)
        st.markdown("<h1>하테나쌤과 함께<br/>하루 5분, 회화 루틴</h1>", unsafe_allow_html=True)
        st.markdown("<p>짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        sensei_path = ASSETS_DIR / "hotena_sensei.png"
        if sensei_path.exists():
            st.image(str(sensei_path), width=420)
        else:
            st.info(f"{sensei_path.as_posix()} 파일이 없습니다.")

    with right:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-topbar"></div>', unsafe_allow_html=True)
        st.markdown(f"## {title}")
        st.caption(subtitle)

        with st.form("landing_login_form", clear_on_submit=False):
            email = st.text_input("이메일", key="landing_email")
            password = st.text_input("비밀번호", type="password", key="landing_pw")
            if show_mode_toggle:
                mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True, index=0 if default_mode=="로그인" else 1)
            else:
                mode = default_mode
            submitted = st.form_submit_button("확인", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # landing-inner

    st.markdown(
        """
<div class="landing-notes">
  <ul>
    <li>회원가입 후 이메일 인증이 필요할 수 있어요.</li>
    <li>비밀번호는 6자 이상을 권장합니다.</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # landing-wrapper

    return email, password, mode, submitted
