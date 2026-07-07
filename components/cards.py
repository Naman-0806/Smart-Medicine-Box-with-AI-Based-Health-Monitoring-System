import streamlit as st
from src.ui import _apply_styles


def small_card(title: str, content: str):
    _apply_styles()
    st.markdown(f"<div class='card'><div class='title'>{title}</div><div class='value'>{content}</div></div>", unsafe_allow_html=True)


def patient_card(patient: dict):
    _apply_styles()
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        f"**Name:** {patient.get('name')}  \\  \n**Age:** {patient.get('age')}  \\  \n**Patient ID:** {patient.get('patient_id')}  \\  \n**Blood Group:** {patient.get('blood_group')}  \\  \n**Device Status:** {patient.get('device_status')}  \\  \n**Battery:** {patient.get('battery_level')}%  \\  \n**Last Sync:** {patient.get('last_sync')}",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
