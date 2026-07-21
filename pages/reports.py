import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar


def render_reports():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Reports")
    st.caption("Review and export patient activity summaries.")
    st.divider()

    metrics = data["metrics"]

    with st.container(border=True):
        st.subheader("Daily Report Preview")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Patient", data['patient']['name'])
        with c2:
            st.metric("Heart Rate", f"{metrics['heart_rate']} bpm")
        with c3:
            st.metric("SpO₂", f"{metrics['spo2']} %")
        with c4:
            st.metric("Temperature", f"{metrics['temperature']} °C")
        st.button("Export Daily Report")

    st.divider()
    with st.container(border=True):
        st.subheader("Weekly Report Preview")
        st.metric("Recent Alerts", len(data.get('alerts', [])))
        st.button("Export Weekly Report")

    st.divider()
    with st.container(border=True):
        st.subheader("Monthly Report Preview")
        st.metric("Medicines Tracked", len(data.get('medicines', [])))
        st.button("Export Monthly Report")


render_reports()
