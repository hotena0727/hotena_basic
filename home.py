
import streamlit as st

st.markdown("""
<style>
a { text-decoration: none !important; }
a:hover { text-decoration: none !important; }
</style>
""", unsafe_allow_html=True)

if "hub_page" not in st.session_state:
    st.session_state.hub_page = "home"

if "user_plan" not in st.session_state:
    st.session_state.user_plan = "free"

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

def render_plan_pill():
    plan_label = "PRO 이용중" if st.session_state.user_plan == "pro" else "FREE 이용중"

    gear_html = ""
    if st.session_state.is_admin:
        gear_html = """
        <a href='?p=admin'
           style='margin-left:8px;text-decoration:none !important;font-size:18px;'>
           ⚙️
        </a>
        """

    st.markdown(f"""
    <div style='display:flex;align-items:center;'>
        <div style='padding:6px 12px;border-radius:20px;background:#111;color:white;font-size:13px;'>
            {plan_label}
        </div>
        {gear_html}
    </div>
    """, unsafe_allow_html=True)

query_params = st.query_params
page = query_params.get("p", "home")

allowed_pages = ["home", "word", "kanji", "talk", "mypage"]
if st.session_state.is_admin:
    allowed_pages.append("admin")

if page not in allowed_pages:
    page = "home"

st.session_state.hub_page = page

render_plan_pill()
st.markdown("---")

if page == "home":
    st.title("홈 허브")
    st.markdown("[단어 훈련](?p=word)")
    st.markdown("[한자 훈련](?p=kanji)")
    st.markdown("[회화 훈련](?p=talk)")
    st.markdown("[마이페이지](?p=mypage)")

elif page == "admin" and st.session_state.is_admin:
    st.title("관리자 페이지")
    st.write("관리자 기능 영역")

elif page == "word":
    st.title("단어 훈련")

elif page == "kanji":
    st.title("한자 훈련")

elif page == "talk":
    st.title("회화 훈련")

elif page == "mypage":
    st.title("마이페이지")
