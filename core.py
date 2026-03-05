
import streamlit as st

def apply_global_ui_css():
    st.markdown(
        '''
<style>

/* remove streamlit header */
header {visibility:hidden;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

/* remove top space */
.block-container{
    padding-top:0 !important;
    margin-top:0 !important;
}

[data-testid="block-container"]{
    padding-top:0 !important;
    margin-top:0 !important;
}

div[data-testid="stVerticalBlock"]{
    margin-top:0 !important;
    padding-top:0 !important;
}

[data-testid="stAppViewContainer"] > .main > div{
    padding-top:0 !important;
    margin-top:0 !important;
}

</style>
''',
        unsafe_allow_html=True
    )
