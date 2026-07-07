import streamlit as st
from components.sidebar import render_sidebar
from src.data import get_all_dummy_data


def render_settings():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Settings")
    st.subheader("Theme")
    st.selectbox("Select Theme", ["Dark", "Light"], index=0)

    st.markdown("---")
    st.subheader("Notifications")
    st.checkbox("Enable notifications", value=True)
    st.checkbox("Email alerts", value=False)

    st.markdown("---")
    st.subheader("Device Settings")
    st.markdown(f"- Device ID: {data['patient'].get('patient_id')}")
    st.button("Reconnect Device")


render_settings()
