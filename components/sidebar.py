import streamlit as st
from firebase.auth_service import login_user, logout_user
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

    # Firebase Authentication & Patient Access Control
    st.sidebar.markdown("### 🔐 Patient Login")

    is_logged_in = st.session_state.get("is_logged_in", False)
    auth_user = st.session_state.get("auth_user")

    if is_logged_in and auth_user:
        patient_info = auth_user.get("patient", {})
        patient_name = patient_info.get("name") or auth_user.get("identifier")
        patient_id = auth_user.get("patient_id")

        # Lock active patient ID to logged-in patient only
        st.session_state["selected_patient_id"] = patient_id

        st.sidebar.success(f"🟢 Logged in as:\n**{patient_name}**")
        st.sidebar.caption(f"Patient ID: `{patient_id}`")

        if st.sidebar.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
            logout_user()
            st.rerun()

    else:
        with st.sidebar.expander("🔑 Login with Firebase", expanded=True):
            login_id = st.text_input("Phone or Email", placeholder="e.g. +1234567890 or patient@email.com", key="login_id_input")
            if st.button("Sign In / Register", key="login_submit_btn", use_container_width=True):
                if login_id.strip():
                    if login_user(login_id):
                        st.sidebar.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.sidebar.error("Authentication failed.")
                else:
                    st.sidebar.warning("Please enter your email or phone number.")

        st.sidebar.markdown("---")

        # Fallback patient selection for non-logged in state
        st.sidebar.markdown("#### Patient Selector (Demo)")
        all_patients = get_all_patients()
        patient_options = {}
        if all_patients:
            for p in all_patients:
                p_id = p.get("patient_id") or p.get("id") or ""
                p_name = p.get("name") or p.get("full_name") or "Unnamed Patient"
                label = f"{p_name} ({p_id})" if p_id else p_name
                patient_options[label] = p_id

        if patient_options:
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
                "Select Active Patient",
                option_labels,
                index=default_index,
                key="sidebar_patient_selector"
            )
            new_selected_id = patient_options[selected_label]
            if st.session_state.get("selected_patient_id") != new_selected_id:
                st.session_state["selected_patient_id"] = new_selected_id
                st.rerun()
        else:
            st.sidebar.caption("No registered patients in Firebase")

    st.sidebar.markdown("---")
    st.sidebar.markdown("\n".join([f"- {p}" for p in PAGES]))
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box with Firebase Auth")
