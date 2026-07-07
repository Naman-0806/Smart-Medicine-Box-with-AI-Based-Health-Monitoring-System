import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.cards import patient_card, small_card
from components.tables import medicine_table, medicine_summary


def render_dashboard():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Smart Medicine Box Dashboard")

    patient = data['patient']
    metrics = data['metrics']

    col1, col2 = st.columns([2,5])
    with col1:
        patient_card(patient)
    with col2:
        c1, c2, c3, c4 = st.columns(4)
        small_card("Heart Rate", f"{metrics['heart_rate']} bpm")
        small_card("SpO₂", f"{metrics['spo2']} %")
        small_card("Temperature", f"{metrics['temperature']} °C")
        small_card("Health Score", f"{metrics['health_score']}")

    st.markdown("---")
    st.subheader("Recent Alerts")
    for a in data['alerts']:
        st.markdown(f"- {a['text']}")

    st.markdown("---")
    st.subheader("Medicine Summary")
    medicine_table(data['medicines'])


render_dashboard()
