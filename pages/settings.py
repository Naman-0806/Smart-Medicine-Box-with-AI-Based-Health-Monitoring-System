import streamlit as st
from components.sidebar import render_sidebar
from src.data import get_all_dummy_data
from src.ui import set_theme


def render_settings():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Settings")
    st.subheader("Theme")
    current_theme = st.session_state.get("theme", "Dark")
    selected_theme = st.selectbox(
        "Select Theme",
        ["Dark", "Light"],
        index=0 if current_theme == "Dark" else 1,
        key="theme",
    )
    set_theme(selected_theme)

    st.markdown("---")
    st.subheader("Notifications")
    st.checkbox("Enable notifications", value=True)
    st.checkbox("Email alerts", value=False)

    st.markdown("---")
    st.subheader("Device Settings")
    st.markdown(f"- Device ID: {data['patient'].get('patient_id')}")
    st.button("Reconnect Device")


render_settings()
