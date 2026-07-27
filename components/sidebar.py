import streamlit as st
from firebase.auth_service import login_user, logout_user, signup_user
from firebase.firebase_service import get_all_patients
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
    owner_uid = st.session_state.get("owner_uid")

    if is_logged_in and auth_user:
        user_name = auth_user.get("full_name") or auth_user.get("email", "").split("@")[0] or "User"
        user_email = auth_user.get("email") or ""

        st.sidebar.success(f"🟢 Logged in as:\n**{user_name}**")
        if user_email:
            st.sidebar.caption(f"📧 {user_email}")

        if st.sidebar.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
            logout_user()
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.markdown("#### Active Patient Selector")

        user_patients = get_all_patients(owner_uid=owner_uid)
        patient_options = {}

        if user_patients:
            for p in user_patients:
                p_id = p.get("patient_id") or p.get("id") or ""
                p_name = p.get("name") or p.get("full_name") or "Unnamed Patient"
                label = f"{p_name} ({p_id})" if p_id else p_name
                patient_options[label] = p_id

            option_labels = list(patient_options.keys())
            current_selected_id = st.session_state.get("selected_patient_id")

            default_index = 0
            if current_selected_id:
                for idx, label in enumerate(option_labels):
                    if patient_options[label] == current_selected_id:
                        default_index = idx
                        break
            else:
                st.session_state["selected_patient_id"] = patient_options[option_labels[0]]

            selected_label = st.sidebar.selectbox(
                "Select Patient",
                option_labels,
                index=default_index,
                key="sidebar_user_patient_selector"
            )
            new_selected_id = patient_options[selected_label]
            if st.session_state.get("selected_patient_id") != new_selected_id:
                st.session_state["selected_patient_id"] = new_selected_id
                st.rerun()
        else:
            st.session_state["selected_patient_id"] = None
            st.sidebar.warning("No patients registered yet.")

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
