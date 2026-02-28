# landing.py - Hotena Landing UI (v4 design-match, no-scroll on PC)
from __future__ import annotations

from pathlib import Path
import base64
import streamlit as st

def _b64_image(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("utf-8")

def landing_ui(assets_dir: str = "assets"):
    """
    Returns: (email, password, mode, submitted)
      - mode: '로그인' or '회원가입'
    """
    assets = Path(assets_dir)
    bg = assets / "landing_bg.png"
    sensei = assets / "hotena_sensei.png"

    # Fallback: if hotena_sensei.png doesn't exist, we simply hide the image box.
    has_sensei = sensei.exists()

    # Background image required
    bg_css = ""
    if bg.exists():
        # Use CSS background on the whole app
        bg_url = f"{assets_dir}/landing_bg.png"
        bg_css = f"""
        .h-landing-bg {{
          position: fixed;
          inset: 0;
          z-index: 0;
          background-image: url('{bg_url}');
          background-size: cover;
          background-repeat: no-repeat;
          /* 👇 show clouds area on first view (adjust if needed) */
          background-position: 50% 62%;
          filter: saturate(1.02);
        }}
        """
    else:
        bg_css = """
        .h-landing-bg { position: fixed; inset:0; z-index:0;
          background: radial-gradient(circle at 30% 20%, rgba(255,240,240,1), rgba(255,255,255,1));
        }
        """

    st.markdown(
        f"""
<style>
/* ====== Fullscreen landing reset ====== */
html, body, [data-testid="stAppViewContainer"], .stApp {{
  height: 100%;
}}
/* Remove default paddings and avoid scroll on desktop */
section.main > div.block-container {{
  padding: 0 !important;
  margin: 0 !important;
  max-width: 100% !important;
}}
header, footer {{ display:none !important; }}
/* Hide Streamlit menu */
#MainMenu {{ visibility: hidden; }}
/* Prevent page scroll (desktop). On mobile, browsers may still allow bounce. */
body {{ overflow: hidden; }}

{bg_css}

/* ====== Layout ====== */
.h-landing-wrap {{
  position: relative;
  z-index: 1;
  height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;     /* center vertically */
  justify-content: center; /* center horizontally */
  padding: 4vh 5vw;
  box-sizing: border-box;
}}

.h-landing-grid {{
  width: min(1200px, 94vw);
  height: min(720px, 92vh);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 4.2vw;
  align-items: center;
}}

@media (max-width: 980px) {{
  body {{ overflow: auto; }}
  .h-landing-wrap {{ padding: 28px 18px; height: auto; min-height: 100vh; }}
  .h-landing-grid {{ grid-template-columns: 1fr; height: auto; gap: 22px; }}
}}

.h-left h1 {{
  margin: 0 0 10px 0;
  font-size: clamp(28px, 3.2vw, 44px);
  font-weight: 900;
  letter-spacing: -0.02em;
  color: rgba(0,0,0,0.86);
}}
.h-left .sub {{
  font-size: 14px;
  color: rgba(0,0,0,0.62);
  line-height: 1.6;
}}
.h-sensei {{
  margin-top: 26px;
  display: flex;
  align-items: flex-end;
  gap: 14px;
}}
.h-sensei img {{
  width: min(320px, 36vw);
  max-width: 320px;
  height: auto;
  filter: drop-shadow(0 16px 30px rgba(0,0,0,.10));
}}
.h-chiprow {{
  margin-top: 22px;
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
}}
.h-chip {{
  display:inline-flex;
  align-items:center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.70);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 10px 28px rgba(0,0,0,0.06);
  font-size: 13px;
  color: rgba(0,0,0,0.72);
}}

.h-card {{
  width: 100%;
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(0,0,0,0.10);
  box-shadow: 0 24px 60px rgba(0,0,0,0.10);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 18px;
  padding: 22px 22px 18px;
}}

.h-card h2 {{
  margin: 0;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.02em;
}}
.h-card .desc {{
  margin-top: 6px;
  font-size: 13px;
  color: rgba(0,0,0,0.60);
}}

.h-form-label {{
  margin-top: 14px;
  font-size: 12px;
  font-weight: 700;
  color: rgba(0,0,0,0.62);
}}

.h-help {{
  margin-top: 10px;
  font-size: 12px;
  color: rgba(0,0,0,0.55);
}}
/* Streamlit widget skin */
.h-card input {{
  border-radius: 12px !important;
}}
.h-card .stTextInput > div > div {{
  background: rgba(255,255,255,0.85) !important;
  border-radius: 12px !important;
}}
.h-card .stRadio > div {{
  background: rgba(255,255,255,0.0) !important;
}}
.h-card button {{
  border-radius: 12px !important;
  height: 46px !important;
  font-weight: 800 !important;
}}
</style>

<div class="h-landing-bg"></div>
<div class="h-landing-wrap">
  <div class="h-landing-grid">
    <div class="h-left">
      <h1>하테나쌤과 함께<br/>하루 5분, 회화 루틴</h1>
      <div class="sub">짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.</div>
"""
        ,
        unsafe_allow_html=True,
    )

    # sensei image (optional)
    if has_sensei:
        st.markdown(
            f"""<div class="h-sensei"><img src="data:image/png;base64,{_b64_image(sensei)}" alt="hotena sensei"/></div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""<div class="h-sensei"></div>""", unsafe_allow_html=True)

    st.markdown(
        """
      <div class="h-chiprow">
        <div class="h-chip">🎧 듣기</div>
        <div class="h-chip">🗣️ 말하기</div>
        <div class="h-chip">💡 스마트코치</div>
        <div class="h-chip">✅ 오늘의 루틴</div>
      </div>
    </div>
    <div class="h-right">
      <div class="h-card">
        <h2>시작하기</h2>
        <div class="desc">로그인 후 바로 홈 허브로 이동합니다.</div>
""",
        unsafe_allow_html=True,
    )

    with st.form("hotena_landing_form", clear_on_submit=False):
        st.markdown('<div class="h-form-label">이메일</div>', unsafe_allow_html=True)
        email = st.text_input("", key="landing_email", label_visibility="collapsed")
        st.markdown('<div class="h-form-label">비밀번호</div>', unsafe_allow_html=True)
        pw = st.text_input("", type="password", key="landing_pw", label_visibility="collapsed")

        st.markdown('<div class="h-form-label">모드</div>', unsafe_allow_html=True)
        mode = st.radio("", ["로그인", "회원가입"], horizontal=True, key="landing_mode", label_visibility="collapsed")

        submitted = st.form_submit_button("확인", use_container_width=True)

    st.markdown(
        """
        <div class="h-help">• 회원가입 후 이메일 인증이 필요할 수 있어요.</div>
        <div class="h-help">• 비밀번호는 6자 이상을 권장합니다.</div>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    return email, pw, mode, submitted
