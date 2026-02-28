# landing.py
# Landing-style login UI for Hotena
from __future__ import annotations

from pathlib import Path
import base64
import streamlit as st


def _img_to_data_uri(p: Path) -> str:
    b = p.read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")


def landing_ui(assets_dir: str = "assets"):
    """Render landing page and return (email, pw, mode, submitted).

    - PC: left (brand/character) + right (login card)
    - Mobile: stacked
    """
    assets = Path(assets_dir)
    bg_path = assets / "landing_bg.png"           # optional
    char_path = assets / "hotena_sensei.png"      # optional

    bg_css = ""
    if bg_path.exists():
        bg_css = f"background-image:url('{_img_to_data_uri(bg_path)}'); background-size:cover; background-position:center;"
    else:
        # graceful fallback
        bg_css = "background: linear-gradient(180deg,#FAF8F4 0%, #F2EEE7 100%);"

    # --- Global landing styles ---
    st.markdown(
        f"""
<style>
/* Hide Streamlit default top padding a bit */
.block-container {{ padding-top: 1.0rem; padding-bottom: 2rem; max-width: 1200px; }}

/* Full-page landing backdrop */
.hotena-landing-backdrop {{
  min-height: calc(100vh - 2rem);
  border-radius: 28px;
  {bg_css}
  display:flex;
  align-items:center;
  justify-content:center;
  padding: 38px 26px;
}}

/* Inner layout */
.hotena-landing-inner {{
  width: 100%;
  max-width: 1100px;
  display:flex;
  gap: 56px;
  align-items:center;
  justify-content:space-between;
}}

/* Responsive */
@media (max-width: 900px) {{
  .hotena-landing-inner {{ flex-direction: column; gap: 22px; }}
}}

/* Right card */
.hotena-card {{
  width: 100%;
  max-width: 520px;
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: 22px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.10);
  padding: 22px 22px 14px;
}}

.hotena-brand-title {{
  font-size: 2.0rem;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0;
}}
.hotena-brand-sub {{
  font-size: 1.05rem;
  opacity: .85;
  margin-top: .35rem;
  margin-bottom: 1.05rem;
}}
.hotena-bullets {{
  display:flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}}
.hotena-chip {{
  display:inline-flex;
  align-items:center;
  gap: 6px;
  padding: 8px 11px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,0.08);
  background: rgba(255,255,255,0.55);
  font-size: .92rem;
}}

/* Make Streamlit inputs look cleaner */
div[data-testid="stTextInput"] label {{ font-size: .92rem; opacity:.85; }}
div[data-testid="stTextInput"] input {{ border-radius: 14px; }}

/* Button */
div[data-testid="stFormSubmitButton"] button {{
  border-radius: 14px;
  height: 44px;
  font-weight: 800;
}}
</style>
""",
        unsafe_allow_html=True,
    )

    # --- Layout container ---
    st.markdown('<div class="hotena-landing-backdrop"><div class="hotena-landing-inner">', unsafe_allow_html=True)

    # Left: character + copy
    left, right = st.columns([1.05, 0.95], vertical_alignment="center")

    with left:
        st.markdown("<p class='hotena-brand-title'>하테나쌤과 함께</p>", unsafe_allow_html=True)
        st.markdown("<div class='hotena-brand-sub'>하루 5분, 회화 루틴</div>", unsafe_allow_html=True)
        st.markdown("짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.")

        if char_path.exists():
            st.image(str(char_path), use_container_width=True)
        else:
            st.info("assets/hotena_sensei.png 를 넣으면 캐릭터가 표시됩니다.")

        st.markdown(
            """
<div class="hotena-bullets">
  <span class="hotena-chip">🎧 듣기</span>
  <span class="hotena-chip">🗣️ 말하기</span>
  <span class="hotena-chip">🧠 스마트코치</span>
  <span class="hotena-chip">✅ 오늘의 루틴</span>
</div>
""",
            unsafe_allow_html=True,
        )

    # Right: login card
    with right:
        st.markdown('<div class="hotena-card">', unsafe_allow_html=True)
        st.markdown("### 시작하기")
        st.caption("로그인 후 바로 홈 허브로 이동합니다.")

        # Use form to reduce rerun flicker
        with st.form("landing_login", clear_on_submit=False):
            email = st.text_input("이메일", key="landing_email")
            pw = st.text_input("비밀번호", type="password", key="landing_pw")
            mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True, key="landing_mode")
            submitted = st.form_submit_button("확인", use_container_width=True)

        st.caption("* 회원가입 후 이메일 인증이 필요할 수 있어요.")
        st.caption("* 비밀번호는 6자 이상을 권장합니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    return email, pw, mode, submitted
