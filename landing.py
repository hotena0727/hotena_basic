
# landing.py - Hotena Landing (fullscreen hero) v2 (assets_dir compatible)
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

    # NOTE: If home.py already called set_page_config, Streamlit may warn; it's OK.
    try:
        st.set_page_config(page_title="Hotena", layout="wide")
    except Exception:
        pass

    bg_path = ASSETS_DIR / "landing_bg.png"
    bg64 = _b64(bg_path)
    bg_css = ""
    if bg64:
        # ✅ show more "ground/cloud" initially: bias background to bottom
        bg_css = f"""
        .stApp {{
            background-image: url('data:image/png;base64,{bg64}');
            background-size: cover;
            background-position: center 82%;
            background-repeat: no-repeat;
        }}
        """

    st.markdown(
        f"""
<style>
html, body {{ height: 100%; }}

/* hide streamlit chrome */
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
  visibility: hidden !important;
  height: 0 !important;
}}

/* remove container padding */
.block-container {{
  padding-top: 0rem !important;
  padding-bottom: 0rem !important;
  padding-left: 0rem !important;
  padding-right: 0rem !important;
  max-width: 100% !important;
}}

[data-testid="stAppViewContainer"] {{
  padding: 0 !important;
  margin: 0 !important;
}}

{bg_css}

/* landing hero */
.landing-wrapper {{
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(18px, 4vh, 56px) clamp(14px, 4vw, 72px);
  box-sizing: border-box;
}}
.landing-inner {{
  width: 100%;
  max-width: 1240px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 56px;
}}

.hero-copy h1 {{
  margin: 0 0 10px 0;
  font-size: 2.05rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}}
.hero-copy p {{
  margin: 0 0 18px 0;
  font-size: 1.05rem;
  opacity: .85;
}}

.login-card {{
  width: min(520px, 92vw);
  background: rgba(255,255,255,0.74);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0,0,0,0.10);
  border-radius: 20px;
  padding: 26px 26px 20px 26px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.08);
}}
.login-topbar {{
  height: 16px;
  border-radius: 999px;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(0,0,0,0.06);
  margin-bottom: 16px;
}}

@media (max-width: 980px) {{
  .landing-inner {{
    flex-direction: column;
    gap: 26px;
    text-align: center;
  }}
  .login-card {{
    width: min(560px, 94vw);
  }}
}}

@media (min-width: 981px) {{
  body {{ overflow: hidden; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="landing-wrapper"><div class="landing-inner">', unsafe_allow_html=True)

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

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown(
        """
<div style="max-width:1240px;margin: 10px auto 0 auto; padding: 0 18px; opacity:.75; font-size:.92rem;">
  <ul style="margin:0; padding-left: 18px;">
    <li>회원가입 후 이메일 인증이 필요할 수 있어요.</li>
    <li>비밀번호는 6자 이상을 권장합니다.</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

    return email, password, mode, submitted
