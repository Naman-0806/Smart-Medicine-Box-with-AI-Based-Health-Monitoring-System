import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.cards import patient_card


def render_patient():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Patient Profile")
    patient = data['patient']
    patient_card(patient)

    st.markdown("---")
    st.subheader("Medical Information")
    st.markdown(f"- Blood Group: {patient.get('blood_group')}")

    st.markdown("---")
    st.subheader("Device Information")
    st.markdown(f"- Device Status: {patient.get('device_status')}")
    st.markdown(f"- Battery Level: {patient.get('battery_level')} %")


render_patient()
