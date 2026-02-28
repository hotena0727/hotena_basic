# landing.py
# Landing-style login UI for Hotena (full-screen hero)
from __future__ import annotations

from pathlib import Path
import base64
import streamlit as st


def _img_to_data_uri(p: Path) -> str:
    b = p.read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode("utf-8")


def landing_ui(assets_dir: str = "assets"):
    """
    Render full-screen landing page and return (email, pw, mode, submitted).

    Assets (optional):
      - assets/landing_bg.png      : background-only image (no card/character)
      - assets/hotena_sensei.png   : character png (ideally transparent)
    """
    assets = Path(assets_dir)
    bg_path = assets / "landing_bg.png"
    char_path = assets / "hotena_sensei.png"

    if bg_path.exists():
        bg = f"background-image:url('{_img_to_data_uri(bg_path)}');"
    else:
        bg = "background: linear-gradient(180deg,#FAF8F4 0%, #F2EEE7 100%);"

    st.markdown(
        f"""
<style>
header, footer {{ visibility: hidden; height: 0; }}
.stApp {{
  {bg}
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}}
.block-container {{
  padding-top: 0rem !important;
  padding-bottom: 0rem !important;
  padding-left: 0rem !important;
  padding-right: 0rem !important;
  max-width: none !important;
}}
.hotena-hero {{
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}}
.hotena-inner {{
  width: min(1200px, 92vw);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 56px;
}}
.hotena-copy h1 {{
  margin: 0;
  font-size: 2.1rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}}
.hotena-copy .sub {{
  margin-top: .25rem;
  font-size: 1.1rem;
  opacity: .88;
  font-weight: 700;
}}
.hotena-copy .desc {{
  margin-top: .7rem;
  font-size: 1.0rem;
  opacity: .85;
}}
.hotena-chips {{
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
  border: 1px solid rgba(0,0,0,0.10);
  background: rgba(255,255,255,0.50);
  font-size: .93rem;
}}
.hotena-card {{
  width: min(520px, 92vw);
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 22px;
  box-shadow: 0 18px 50px rgba(0,0,0,0.10);
  padding: 22px 22px 14px;
}}
div[data-testid="stTextInput"] label {{ font-size: .92rem; opacity:.85; }}
div[data-testid="stTextInput"] input {{ border-radius: 14px; }}
div[data-testid="stFormSubmitButton"] button {{
  border-radius: 14px;
  height: 44px;
  font-weight: 800;
}}
@media (max-width: 900px) {{
  .hotena-inner {{
    flex-direction: column;
    gap: 22px;
    padding: 28px 0 34px;
  }}
  .hotena-copy h1 {{ font-size: 1.75rem; }}
}}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="hotena-hero"><div class="hotena-inner">', unsafe_allow_html=True)

    with st.container():
        left, right = st.columns([1.05, 0.95], vertical_alignment="center")

        with left:
            st.markdown(
                """
<div class="hotena-copy">
  <h1>하테나쌤과 함께</h1>
  <div class="sub">하루 5분, 회화 루틴</div>
  <div class="desc">짧게, 자주, 확실하게. 오늘도 한 세트만 시작해요.</div>
</div>
                """,
                unsafe_allow_html=True,
            )

            if char_path.exists():
                st.image(str(char_path), use_container_width=True)
            else:
                st.info("assets/hotena_sensei.png 를 넣으면 캐릭터가 표시됩니다.")

            st.markdown(
                """
<div class="hotena-chips">
  <span class="hotena-chip">🎧 듣기</span>
  <span class="hotena-chip">🗣️ 말하기</span>
  <span class="hotena-chip">🧠 스마트코치</span>
  <span class="hotena-chip">✅ 오늘의 루틴</span>
</div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.markdown('<div class="hotena-card">', unsafe_allow_html=True)
            st.markdown("### 시작하기")
            st.caption("로그인 후 바로 홈 허브로 이동합니다.")

            with st.form("landing_login", clear_on_submit=False):
                email = st.text_input("이메일", key="landing_email")
                pw = st.text_input("비밀번호", type="password", key="landing_pw")
                mode = st.radio("모드", ["로그인", "회원가입"], horizontal=True, key="landing_mode")
                submitted = st.form_submit_button("확인", use_container_width=True)

            st.caption("* 회원가입 후 이메일 인증이 필요할 수 있어요.")
            st.caption("* 비밀번호는 6자 이상을 권장합니다.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)
    return email, pw, mode, submitted
