
# ============================================================
# talk.py (FINAL STABLE VERSION)
# - Smart Coach split logic
# - General questions redirect to Naver Talk
# ============================================================

import streamlit as st
import ai_tutor

GENERAL_KEYWORDS = [
    "패키지", "요금", "가격", "수업", "강의",
    "환불", "결제", "프로", "무료", "기능"
]

def render():
    st.title("💬 회화 훈련")

    ctx = {
        "situation": "복도에서 마주쳤다",
        "partner": "こんにちは。"
    }

    qid = "demo"
    tag = "daily"
    ok = True

    with st.expander("🤖 하테나쌤 스마트 코치", expanded=False):

        user_q = st.text_input("질문을 입력하세요")

        ask = st.button("AI 코칭 받기")

        coach_slot = st.empty()

        if ask and user_q.strip():

            user_text = user_q.strip()

            # ✅ 일반 질문 → 네이버 톡 안내
            if any(k in user_text for k in GENERAL_KEYWORDS):

                coach_slot.info(
                    "📩 상담이 필요한 질문입니다.\n"
                    "하테나쌤에게 직접 문의해 주세요 🙂"
                )

                st.markdown("""
                <a href="https://talk.naver.com/YOUR_LINK_HERE"
                   target="_blank"
                   style="
                       display:inline-block;
                       margin-top:10px;
                       padding:10px 18px;
                       background:#03C75A;
                       color:white;
                       border-radius:8px;
                       text-decoration:none;
                       font-weight:600;
                   ">
                   네이버 톡으로 문의하기
                </a>
                """, unsafe_allow_html=True)

            else:

                ans = ai_tutor.ask_hatena(
                    mode="talk",
                    user_input=user_text,
                    context=ctx,
                    meta={
                        "page": "talk",
                        "qid": str(qid),
                        "tag": str(tag),
                        "ok": bool(ok),
                        "is_admin": bool(st.session_state.get("is_admin", False)),
                        "plan": st.session_state.get("plan", "free"),
                    },
                )

                coach_slot.info(ans)
