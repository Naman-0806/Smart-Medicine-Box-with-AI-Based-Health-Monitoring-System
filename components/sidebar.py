import streamlit as st
from firebase.auth_service import login_user, logout_user, signup_user
from firebase.firebase_service import get_patient_by_id
from src.ui import apply_theme_styles

PAGES = [
    "Dashboard",
    "Patient",
    "Medicines",
    "Health Monitoring",
    "AI Insights",
    "Reports",
    "Settings",
]


def render_sidebar():
    apply_theme_styles()
    st.sidebar.title("Navigation")

    is_logged_in = st.session_state.get("is_logged_in", False)
    auth_user = st.session_state.get("auth_user") or {}
    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")

    if is_logged_in and auth_user and owner_uid:
        user_name = auth_user.get("full_name") or auth_user.get("email", "").split("@")[0] or "User"
        user_email = auth_user.get("email") or ""

        # Enforce user-specific patient ID session mapping
        st.session_state["selected_patient_id"] = owner_uid
        st.session_state["owner_uid"] = owner_uid

        st.sidebar.success(f"🟢 Logged in as:\n**{user_name}**")
        if user_email:
            st.sidebar.caption(f"📧 {user_email}")

        patient = get_patient_by_id(owner_uid, owner_uid=owner_uid)
        if patient:
            st.sidebar.markdown(f"👤 Profile: **{patient.get('name') or patient.get('full_name')}**")
            st.sidebar.caption(f"ID: `{owner_uid}`")
        else:
            st.sidebar.info("📝 No patient profile registered yet.")

        if st.sidebar.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
            logout_user()
            st.rerun()

    else:
        st.sidebar.markdown("### 🔐 Firebase Authentication")
        tab_login, tab_signup = st.sidebar.tabs(["🔑 Login", "📝 Sign Up"])

        with tab_login:
            login_id = st.text_input("Email or Phone", placeholder="user@example.com", key="sidebar_login_id")
            login_pwd = st.text_input("Password", type="password", placeholder="••••••••", key="sidebar_login_pwd")

            if st.button("Log In", key="sidebar_login_btn", use_container_width=True):
                if login_id and login_pwd:
                    success, msg = login_user(login_id, login_pwd)
                    if success:
                        st.sidebar.success(msg)
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
                else:
                    st.sidebar.warning("Please enter both email/phone and password.")

        with tab_signup:
            su_name = st.text_input("Full Name", placeholder="John Doe", key="sidebar_su_name")
            su_email = st.text_input("Email Address", placeholder="user@example.com", key="sidebar_su_email")
            su_phone = st.text_input("Phone (Optional)", placeholder="+1234567890", key="sidebar_su_phone")
            su_pwd = st.text_input("Password", type="password", placeholder="Min 6 chars", key="sidebar_su_pwd")
            su_pwd2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="sidebar_su_pwd2")

            if st.button("Create Account", key="sidebar_signup_btn", use_container_width=True):
                success, msg = signup_user(
                    email=su_email,
                    password=su_pwd,
                    confirm_password=su_pwd2,
                    full_name=su_name,
                    phone_number=su_phone
                )
                if success:
                    st.sidebar.success(msg)
                    st.rerun()
                else:
                    st.sidebar.error(msg)

        st.sidebar.markdown("---")
        st.sidebar.info("🔒 Please log in or sign up to manage your patient records securely.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("\n".join([f"- {p}" for p in PAGES]))
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box Healthcare Platform")
