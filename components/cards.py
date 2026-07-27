import streamlit as st
from src.ui import apply_theme_styles


def small_card(title: str, content: str):
    apply_theme_styles()
    with st.container(border=True):
        st.markdown(f"<div class='title'>{title}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='value'>{content}</div>", unsafe_allow_html=True)


def patient_card(patient: dict):
    apply_theme_styles()
    p = patient or {}
    name = p.get('name') or p.get('full_name') or 'No data available'
    age = str(p.get('age')) if p.get('age') is not None else 'No data available'
    pid = p.get('patient_id') or p.get('id') or 'No data available'
    blood = p.get('blood_group') or 'No data available'
    status = p.get('device_status') or 'No data available'
    battery = f"{p.get('battery_level')}%" if p.get('battery_level') is not None else 'No data available'
    last_sync = p.get('last_sync') or 'No data available'

    with st.container(border=True):
        st.markdown("<div class='section-title'>Patient Snapshot</div>", unsafe_allow_html=True)
        st.write(f"**Name:** {name}")
        st.write(f"**Age:** {age}")
        st.write(f"**Patient ID:** `{pid}`")
        st.write(f"**Blood Group:** {blood}")
        st.write(f"**Device Status:** {status}")
        st.write(f"**Battery:** {battery}")
        st.write(f"**Last Sync:** {last_sync}")
