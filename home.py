import streamlit as st
import importlib
import core

# --------------------------------------------------
# Global UI
# --------------------------------------------------
core.apply_global_ui_css()

# --------------------------------------------------
# Query Param Reader (safe)
# --------------------------------------------------
def get_page():
    try:
        qp = dict(st.query_params)
    except Exception:
        qp = {}

    return qp.get("p", "home")


# --------------------------------------------------
# Cached module loader (reduces rerun reload time)
# --------------------------------------------------
@st.cache_resource
def load_module(name):
    return importlib.import_module(name)


def run_module(module_name):
    try:
        mod = load_module(module_name)

        if hasattr(mod, "main"):
            mod.main()

        elif hasattr(mod, "app"):
            mod.app()

        else:
            st.error(f"{module_name} 모듈에 main() 또는 app()이 없습니다.")

    except Exception as e:
        st.error(f"모듈 실행 오류: {e}")


# --------------------------------------------------
# Determine current page
# --------------------------------------------------
page = get_page()

# --------------------------------------------------
# Render navigation
# --------------------------------------------------
core.render_top_nav(page)


# --------------------------------------------------
# Page Router
# --------------------------------------------------
if page == "home":

    st.markdown(
        """
        ### HOTENA

        일본어 회화 훈련을 시작해보세요.
        """
    )

elif page == "talk":

    run_module("talk")

elif page == "basic":

    run_module("hotena_basic")

elif page == "kanji":

    run_module("kanji")

elif page == "mypage":

    run_module("mypage")

elif page == "admin":

    run_module("admin")

else:

    st.warning("페이지를 찾을 수 없습니다.")
