# talk.py
import streamlit as st
import ai_tutor

GENERAL_KEYWORDS = [
    "패키지", "요금", "가격", "수업", "강의",
    "환불", "결제", "프로", "무료", "기능"
]

st.title("💬 회화 훈련")

user_q = st.text_input("질문하세요")
ask = st.button("스마트코치에게 묻기")

USER_PLAN = st.session_state.get("plan", "free")
is_admin = bool(st.session_state.get("is_admin", False))

if ask and user_q.strip():

    if not is_admin and any(k in user_q for k in GENERAL_KEYWORDS):

        st.info("📩 이 질문은 상담이 필요한 내용이에요. 하테나쌤에게 직접 문의해 주세요 🙂")
        st.markdown(
            '<a href="https://talk.naver.com/YOUR_LINK_HERE" target="_blank" '
            'style="display:inline-block;margin-top:10px;padding:10px 18px;'
            'background:#03C75A;color:white;border-radius:8px;'
            'text-decoration:none;font-weight:600;">'
            '네이버 톡으로 문의하기</a>',
            unsafe_allow_html=True
        )

    else:

        context = {
            "situation": "복도에서 인사",
            "correct": "こんにちは",
            "user_answer": user_q
        }

        ans = ai_tutor.ask_hatena(
            mode="talk",
            user_input=user_q,
            context=context,
            meta={
                "is_admin": is_admin,
                "plan": USER_PLAN,
            },
        )

        st.success(ans)
