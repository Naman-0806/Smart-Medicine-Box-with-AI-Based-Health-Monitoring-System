import streamlit as st
from components.sidebar import render_sidebar
from firebase.auth_service import render_login_page, logout_user

st.set_page_config(page_title="Login - Smart Medicine Box", layout="wide")

render_sidebar()

if st.session_state.get("is_logged_in") and st.session_state.get("user_uid"):
    user_name = st.session_state.get("auth_user", {}).get("full_name") or "User"
    st.markdown(f"# 🟢 Logged in as {user_name}")
    st.info(f"User UID: `{st.session_state.get('user_uid')}`")
    if st.button("🚪 Logout", key="login_page_logout"):
        logout_user()
        st.rerun()
else:
    render_login_page()
