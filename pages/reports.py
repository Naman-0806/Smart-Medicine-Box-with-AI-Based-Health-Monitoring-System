import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar


def render_reports():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Reports")
    metrics = data["metrics"]

    st.subheader("Daily Report Preview")
    st.markdown(f"- Patient: {data['patient']['name']}")
    st.markdown(f"- Heart Rate: {metrics['heart_rate']} bpm")
    st.markdown(f"- SpO₂: {metrics['spo2']} %")
    st.markdown(f"- Temperature: {metrics['temperature']} °C")
    st.button("Export Daily Report")

    st.markdown("---")
    st.subheader("Weekly Report Preview")
    st.markdown(f"- Recent alerts: {len(data.get('alerts', []))}")
    st.button("Export Weekly Report")

    st.markdown("---")
    st.subheader("Monthly Report Preview")
    st.markdown(f"- Medicines tracked: {len(data.get('medicines', []))}")
    st.button("Export Monthly Report")


render_reports()
