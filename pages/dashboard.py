import streamlit as st
from components.sidebar import render_sidebar
from components.cards import small_card
from components.tables import medicine_table
from firebase.firebase_service import get_dashboard_data


def render_dashboard():
    data = get_dashboard_data() or {}
    render_sidebar()

    if data.get("offline"):
        st.warning("Running in Offline Mode")

    st.markdown("# Smart Medicine Box Dashboard")

    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}

    col1, col2 = st.columns([2, 5])
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            f"**Name:** {patient.get('name', '—')}  \n**Age:** {patient.get('age', '—')}  \n**Patient ID:** {patient.get('patient_id', '—')}  \n**Blood Group:** {patient.get('blood_group', '—')}  \n**Device Status:** {patient.get('device_status', '—')}  \n**Battery:** {patient.get('battery_level', '—')}%  \n**Last Sync:** {patient.get('last_sync', '—')}",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        metric_cols = st.columns(4)
        with metric_cols[0]:
            small_card("Heart Rate", f"{metrics.get('heart_rate', '—')} bpm")
        with metric_cols[1]:
            small_card("SpO₂", f"{metrics.get('spo2', '—')} %")
        with metric_cols[2]:
            small_card("Temperature", f"{metrics.get('temperature', '—')} °C")
        with metric_cols[3]:
            small_card("Health Score", f"{metrics.get('health_score', '—')}")

    st.markdown("---")
    st.subheader("Recent Alerts")
    for alert in data.get("alerts", []) or []:
        st.markdown(f"- {alert.get('text', '')}")

    st.markdown("---")
    st.subheader("Medicine Summary")
    medicine_table(data.get("medicines", []))


render_dashboard()
