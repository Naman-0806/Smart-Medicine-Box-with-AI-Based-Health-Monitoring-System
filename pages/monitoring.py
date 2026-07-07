import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.cards import small_card
from components.charts import heart_rate_chart, spo2_chart, temperature_chart


def render_monitoring():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Health Monitoring")
    metrics = data['metrics']
    c1, c2, c3 = st.columns(3)
    with c1:
        small_card("Heart Rate", f"{metrics['heart_rate']} bpm")
    with c2:
        small_card("SpO₂", f"{metrics['spo2']} %")
    with c3:
        small_card("Temperature", f"{metrics['temperature']} °C")

    st.markdown("---")
    st.subheader("Trends")
    col_a, col_b, col_c = st.columns(3)
    trends = data['trends']
    with col_a:
        st.markdown("**Heart Rate Trend**")
        st.altair_chart(heart_rate_chart(trends), use_container_width=True)
    with col_b:
        st.markdown("**SpO₂ Trend**")
        st.altair_chart(spo2_chart(trends), use_container_width=True)
    with col_c:
        st.markdown("**Temperature Trend**")
        st.altair_chart(temperature_chart(trends), use_container_width=True)


render_monitoring()
