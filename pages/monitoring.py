import time
import streamlit as st
from firebase.firebase_service import get_dashboard_data
from components.sidebar import render_sidebar
from components.charts import heart_rate_chart, spo2_chart, temperature_chart


def _render_overview(metrics, patient):
    st.subheader("Live Health Overview")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Heart Rate", f"{metrics.get('heart_rate', 'N/A')} bpm")
        with c2:
            st.metric("SpO₂", f"{metrics.get('spo2', 'N/A')} %")
        with c3:
            st.metric("Body Temperature", f"{metrics.get('temperature', 'N/A')} °C")

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Blood Pressure", metrics.get("blood_pressure", "N/A"))
        with c5:
            st.metric("Respiratory Rate", metrics.get("respiratory_rate", "N/A"))
        with c6:
            st.metric("Health Score", metrics.get("health_score", "N/A"))

        st.divider()
        c7, c8 = st.columns(2)
        with c7:
            st.metric("Device Status", patient.get('device_status', 'N/A'))
        with c8:
            st.metric("Last Sync Time", patient.get('last_sync', 'N/A'))


def _render_status_section():
    st.subheader("Health Status")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Normal", "Stable")
        with c2:
            st.metric("Warning", "Monitor closely")
        with c3:
            st.metric("Critical", "Immediate attention")


def _render_trends(trends):
    st.subheader("Health Trend")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Heart Rate**")
            st.altair_chart(heart_rate_chart(trends), use_container_width=True)
        with c2:
            st.markdown("**SpO₂**")
            st.altair_chart(spo2_chart(trends), use_container_width=True)
        with c3:
            st.markdown("**Temperature**")
            st.altair_chart(temperature_chart(trends), use_container_width=True)


def _render_medicine_reminder(medicines):
    st.subheader("Medicine Reminder Status")
    with st.container(border=True):
        if hasattr(medicines, 'empty'):
            if medicines.empty:
                st.markdown("No medicine data available.")
                return
        elif not medicines:
            st.markdown("No medicine data available.")
            return

        next_medicine = medicines.iloc[0] if hasattr(medicines, 'iloc') else medicines[0]
        last_dose = medicines.iloc[-1] if hasattr(medicines, 'iloc') else medicines[-1]

        st.write(f"**Next Medicine:** {next_medicine.get('Medicine', next_medicine.get('medicine_name', 'N/A'))}")
        st.write(f"**Next Dose Time:** {next_medicine.get('Time', next_medicine.get('time', 'N/A'))}")
        st.write(f"**Last Dose Taken:** {last_dose.get('Medicine', last_dose.get('medicine_name', 'N/A'))} at {last_dose.get('Time', last_dose.get('time', 'N/A'))}")


def render_monitoring():
    refresh_interval = 5
    if "monitoring_data" not in st.session_state:
        st.session_state["monitoring_data"] = get_dashboard_data()

    if "monitoring_last_refresh" not in st.session_state:
        st.session_state["monitoring_last_refresh"] = time.time()

    now = time.time()
    if now - st.session_state["monitoring_last_refresh"] >= refresh_interval:
        st.session_state["monitoring_data"] = get_dashboard_data()
        st.session_state["monitoring_last_refresh"] = now

    render_sidebar()

    st.markdown("# Health Monitoring")
    st.caption("Real-time vitals and reminders in a cleaner, more scannable layout.")
    st.divider()
    data = st.session_state["monitoring_data"]
    patient = data.get('patient', {})
    metrics = data.get('metrics', {})
    trends = data.get('trends')
    medicines = data.get('medicines')

    _render_overview(metrics, patient)
    st.divider()
    _render_status_section()
    st.divider()
    _render_trends(trends)
    st.divider()
    _render_medicine_reminder(medicines)


render_monitoring()
