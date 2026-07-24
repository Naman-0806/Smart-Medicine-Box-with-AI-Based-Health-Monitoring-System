import streamlit as st
from src.ui import apply_theme_styles


def small_card(title: str, content: str):
    apply_theme_styles()
    with st.container(border=True):
        st.markdown(f"<div class='title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='value'>{content}</div>", unsafe_allow_html=True)


def patient_card(patient: dict):
    apply_theme_styles()
    with st.container(border=True):
        st.markdown("<div class='section-title'>Patient Snapshot</div>", unsafe_allow_html=True)
        st.write(f"**Name:** {patient.get('name', '—')}")
        st.write(f"**Age:** {patient.get('age', '—')}")
        st.write(f"**Patient ID:** {patient.get('patient_id', '—')}")
        st.write(f"**Blood Group:** {patient.get('blood_group', '—')}")
        st.write(f"**Device Status:** {patient.get('device_status', '—')}")
        st.write(f"**Battery:** {patient.get('battery_level', '—')}%")
        st.write(f"**Last Sync:** {patient.get('last_sync', '—')}")
