import streamlit as st
from components.sidebar import render_sidebar
from firebase.firebase_service import get_patient_by_id, get_patient_data
from src.ui import set_theme, apply_theme_styles


from firebase.auth_service import require_auth


def render_settings():
    render_sidebar()
    require_auth()
    apply_theme_styles()

    selected_patient_id = st.session_state.get("selected_patient_id")
    patient = get_patient_by_id(selected_patient_id) or get_patient_data()

    st.markdown("# Settings")
    st.subheader("Theme")
    current_theme = st.session_state.get("theme", "Dark")
    selected_theme = st.selectbox(
        "Select Theme",
        ["Dark", "Light"],
        index=0 if current_theme == "Dark" else 1,
        key="app_theme",
    )
    set_theme(selected_theme)
    st.session_state["theme"] = selected_theme

    st.markdown("---")
    st.subheader("Notifications")
    st.checkbox("Enable notifications", value=True)
    st.checkbox("Email alerts", value=False)

    st.markdown("---")
    st.subheader("Device Settings")
    st.markdown(f"- Connected Patient: **{patient.get('name', 'N/A')}**")
    st.markdown(f"- Patient / Box ID: `{patient.get('patient_id') or patient.get('id') or 'N/A'}`")
    st.button("Reconnect Device")


render_settings()

