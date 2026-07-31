import time
import streamlit as st
from components.charts import heart_rate_chart, spo2_chart, temperature_chart
from firebase.auth_service import require_auth
from firebase.firebase_service import get_dashboard_data
from src.ui import apply_theme_styles


def _render_overview(metrics, patient):
    st.subheader("Live Health Overview")
    with st.container(border=True):
        hr_val = f"{metrics.get('heart_rate')} bpm" if metrics.get('heart_rate') is not None else "N/A"
        spo2_val = f"{metrics.get('spo2')} %" if metrics.get('spo2') is not None else "N/A"
        temp_val = f"{metrics.get('temperature')} °C" if metrics.get('temperature') is not None else "N/A"
        bp_val = metrics.get('blood_pressure') or "N/A"
        resp_val = metrics.get('respiratory_rate') or "N/A"
        score_val = metrics.get('health_score') if metrics.get('health_score') is not None else "N/A"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Heart Rate", hr_val)
        with c2:
            st.metric("SpO₂", spo2_val)
        with c3:
            st.metric("Body Temperature", temp_val)

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Blood Pressure", bp_val)
        with c5:
            st.metric("Respiratory Rate", resp_val)
        with c6:
            st.metric("Health Score", score_val)

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
        if trends is None or (hasattr(trends, 'empty') and trends.empty):
            st.info("No health readings recorded yet for this patient.")
            return

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
    require_auth()
    apply_theme_styles()

    st.markdown("# 🩺 Health Monitoring")
    st.caption("Real-time vitals and telemetry tracking for your selected patient.")
    st.divider()

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    refresh_interval = 5

    if "monitoring_last_refresh" not in st.session_state:
        st.session_state["monitoring_last_refresh"] = time.time()

    now = time.time()
    if "monitoring_data" not in st.session_state or (now - st.session_state["monitoring_last_refresh"] >= refresh_interval):
        st.session_state["monitoring_data"] = get_dashboard_data(user_uid, owner_uid=user_uid)
        st.session_state["monitoring_last_refresh"] = now

    data = st.session_state.get("monitoring_data", {})
    if data.get("no_patients") or not data.get("patient"):
        st.warning("📝 No patient profile registered yet. Please register your patient profile first.")
        if st.button("📝 Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
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
