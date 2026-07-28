import streamlit as st
from components.sidebar import render_sidebar
from firebase.auth_service import require_auth

st.set_page_config(page_title="Smart Medicine Box Dashboard", layout="wide")


def main():
    require_auth()
    render_sidebar()

    if st.session_state.get("is_logged_in"):
        st.switch_page("pages/dashboard.py")




if __name__ == "__main__":
    main()
