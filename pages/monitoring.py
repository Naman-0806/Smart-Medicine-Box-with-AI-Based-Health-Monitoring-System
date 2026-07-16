import time
import streamlit as st
from firebase.firebase_service import get_dashboard_data
from components.sidebar import render_sidebar
from components.cards import small_card
from components.charts import heart_rate_chart, spo2_chart, temperature_chart
from src.ui import _apply_styles


def _render_overview(metrics, patient):
    st.subheader("Live Health Overview")
    c1, c2, c3 = st.columns(3)
    with c1:
        small_card("Heart Rate", f"{metrics.get('heart_rate', 'N/A')} bpm")
    with c2:
        small_card("SpO₂", f"{metrics.get('spo2', 'N/A')} %")
    with c3:
        small_card("Body Temperature", f"{metrics.get('temperature', 'N/A')} °C")

    c4, c5, c6 = st.columns(3)
    with c4:
        small_card("Blood Pressure", metrics.get("blood_pressure", "N/A"))
    with c5:
        small_card("Respiratory Rate", metrics.get("respiratory_rate", "N/A"))
    with c6:
        small_card("Health Score", metrics.get("health_score", "N/A"))

    st.markdown("---")
    c7, c8 = st.columns(2)
    with c7:
        small_card("Device Status", patient.get('device_status', 'N/A'))
    with c8:
        small_card("Last Sync Time", patient.get('last_sync', 'N/A'))


def _render_status_section():
    st.subheader("Health Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='card'><div class='title'>Normal</div><div class='value'>Stable</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='card'><div class='title'>Warning</div><div class='value'>Monitor closely</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='card'><div class='title'>Critical</div><div class='value'>Immediate attention</div></div>", unsafe_allow_html=True)


def _render_trends(trends):
    st.subheader("Health Trend")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Heart Rate**")
        st.altair_chart(heart_rate_chart(trends), use_container_width=True)
    with col_b:
        st.markdown("**SpO₂**")
        st.altair_chart(spo2_chart(trends), use_container_width=True)
    with col_c:
        st.markdown("**Temperature**")
        st.altair_chart(temperature_chart(trends), use_container_width=True)


def _render_medicine_reminder(medicines):
    st.subheader("Medicine Reminder Status")
    if hasattr(medicines, 'empty'):
        if medicines.empty:
            st.markdown("No medicine data available.")
            return
    elif not medicines:
        st.markdown("No medicine data available.")
        return

    next_medicine = medicines.iloc[0] if hasattr(medicines, 'iloc') else medicines[0]
    last_dose = medicines.iloc[-1] if hasattr(medicines, 'iloc') else medicines[-1]

    st.markdown(f"**Next Medicine:** {next_medicine.get('Medicine', next_medicine.get('medicine_name', 'N/A'))}")
    st.markdown(f"**Next Dose Time:** {next_medicine.get('Time', next_medicine.get('time', 'N/A'))}")
    st.markdown(f"**Last Dose Taken:** {last_dose.get('Medicine', last_dose.get('medicine_name', 'N/A'))} at {last_dose.get('Time', last_dose.get('time', 'N/A'))}")


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
    _apply_styles()

    st.markdown("# Health Monitoring")
    data = st.session_state["monitoring_data"]
    patient = data.get('patient', {})
    metrics = data.get('metrics', {})
    trends = data.get('trends')
    medicines = data.get('medicines')

    _render_overview(metrics, patient)
    st.markdown("---")
    _render_status_section()
    st.markdown("---")
    _render_trends(trends)
    st.markdown("---")
    _render_medicine_reminder(medicines)


render_monitoring()
