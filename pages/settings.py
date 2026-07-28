import streamlit as st
from components.sidebar import render_sidebar
from firebase.auth_service import require_auth
from firebase.firebase_service import get_patient_by_id
from src.ui import apply_theme_styles, set_theme


def render_settings():
    require_auth()
    render_sidebar()
    apply_theme_styles()


    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    patient = get_patient_by_id(owner_uid, owner_uid=owner_uid) or {}

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
    p_name = patient.get('name') or patient.get('full_name') or 'No data available'
    p_id = patient.get('patient_id') or patient.get('id') or 'No data available'
    st.markdown(f"- Connected Patient: **{p_name}**")
    st.markdown(f"- Patient / Box ID: `{p_id}`")
    st.button("Reconnect Device")


render_settings()
