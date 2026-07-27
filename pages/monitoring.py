import time
import streamlit as st
from components.charts import heart_rate_chart, spo2_chart, temperature_chart
from components.sidebar import render_sidebar
from firebase.firebase_service import get_dashboard_data
from src.ui import apply_theme_styles


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
            st.metric("Device Status", patient.get('device_status', 'Connected'))
        with c8:
            st.metric("Last Sync Time", patient.get('last_sync', 'N/A'))


def _render_status_section(alerts=None):
    st.subheader("Health Status")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Normal", "Stable")
        with c2:
            st.metric("Warning", "Monitor closely")
        with c3:
            st.metric("Critical", "Immediate attention")

        if alerts:
            st.divider()
            st.markdown("**Active Alerts:**")
            for alert in alerts:
                if isinstance(alert, dict):
                    txt = alert.get("text", "")
                    if alert.get("type") == "emergency" or "EMERGENCY" in str(txt):
                        st.error(f"🚨 {txt}")
                    else:
                        st.write(f"• {txt}")
                else:
                    st.write(f"• {alert}")


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
                st.markdown("No medicine schedule data available.")
                return
        elif not medicines:
            st.markdown("No medicine schedule data available.")
            return

        next_medicine = medicines.iloc[0] if hasattr(medicines, 'iloc') else medicines[0]
        last_dose = medicines.iloc[-1] if hasattr(medicines, 'iloc') else medicines[-1]

        st.write(f"**Next Medicine:** {next_medicine.get('Medicine', next_medicine.get('medicine_name', 'N/A'))}")
        st.write(f"**Next Dose Time:** {next_medicine.get('Time', next_medicine.get('time', 'N/A'))}")
        st.write(f"**Last Dose Taken:** {last_dose.get('Medicine', last_dose.get('medicine_name', 'N/A'))} at {last_dose.get('Time', last_dose.get('time', 'N/A'))}")


def render_monitoring():
    render_sidebar()
    apply_theme_styles()

    st.markdown("# 🩺 Health Monitoring")
    st.caption("Real-time vitals and telemetry tracking for your selected patient.")
    st.divider()

    is_logged_in = st.session_state.get("is_logged_in", False)
    owner_uid = st.session_state.get("owner_uid")

    if not is_logged_in or not owner_uid:
        st.warning("⚠️ Please log in or sign up in the sidebar to view health monitoring telemetry.")
        return

    selected_patient_id = st.session_state.get("selected_patient_id")
    refresh_interval = 5

    if "monitoring_last_refresh" not in st.session_state:
        st.session_state["monitoring_last_refresh"] = time.time()

    now = time.time()
    if "monitoring_data" not in st.session_state or (now - st.session_state["monitoring_last_refresh"] >= refresh_interval):
        st.session_state["monitoring_data"] = get_dashboard_data(selected_patient_id, owner_uid=owner_uid)
        st.session_state["monitoring_last_refresh"] = now

    data = st.session_state.get("monitoring_data", {})
    if data.get("no_patients") or not data.get("patient"):
        st.info("⚠️ No registered patients found. Please register a patient first.")
        return

    patient = data.get('patient', {})
    metrics = data.get('metrics', {})
    trends = data.get('trends')
    medicines = data.get('medicines')
    alerts = data.get('alerts', [])

    _render_overview(metrics, patient)
    st.divider()
    _render_status_section(alerts)
    st.divider()
    _render_trends(trends)
    st.divider()
    _render_medicine_reminder(medicines)


render_monitoring()
