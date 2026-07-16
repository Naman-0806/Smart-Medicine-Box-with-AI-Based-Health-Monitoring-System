import streamlit as st
import pandas as pd
import altair as alt


_CARD_STYLE = """
<style>
.card { background-color: #000000; padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.5); color: #000000; }
.card .title { font-size:14px; color:#9fb3d6; }
.card .value { font-size:22px; font-weight:600; }
.rounded-table td, .rounded-table th { padding:8px; }
.small { font-size:12px; color:#9fb3d6 }
</style>
"""


def _apply_styles():
    st.markdown(_CARD_STYLE, unsafe_allow_html=True)


def render_sidebar():
    st.sidebar.title("Navigation")
    menu = st.sidebar.radio("", ["Dashboard", "Patient", "Medicines", "Health Monitoring", "AI Insights", "Reports", "Settings"])
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box")


def _card(title, content):
    st.markdown(f"<div class='card'><div class='title'>{title}</div><div class='value'>{content}</div></div>", unsafe_allow_html=True)


def render_main(data: dict):
    _apply_styles()
    st.markdown("# Smart Medicine Box Dashboard")

    patient = data["patient"]
    metrics = data["metrics"]

    # Patient info
    with st.container():
        col1, col2 = st.columns([2, 5])
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"**Name:** {patient['name']}  \\n+**Age:** {patient['age']}  \\n+**Patient ID:** {patient['patient_id']}  \\n+**Device Status:** {patient['device_status']}  \\n+**Last Sync:** {patient['last_sync']}", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                _card("Heart Rate", f"{metrics['heart_rate']} bpm")
            with c2:
                _card("SpO₂", f"{metrics['spo2']} %")
            with c3:
                _card("Temperature", f"{metrics['temperature']} °C")
            with c4:
                _card("Health Score", f"{metrics['health_score']}")

    st.markdown("---")

    # Medicine table and alerts
    with st.container():
        left, right = st.columns([3, 1])
        with left:
            st.subheader("Medicine Status")
            df = data["medicines"]
            st.dataframe(df, use_container_width=True)
        with right:
            st.subheader("Alerts")
            for a in data["alerts"]:
                st.markdown(f"- {a['text']}")

    st.markdown("---")

    # AI Recommendation
    st.subheader("AI Recommendations")
    ai = data.get("ai", [])
    if isinstance(ai, list):
        for rec in ai:
            st.markdown(f"<div class='card small'>{rec}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='card small'>{ai}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    st.subheader("Trends")
    trends = data["trends"]
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Heart Rate Trend**")
        chart = alt.Chart(trends).mark_line().encode(x='time:T', y='heart_rate:Q')
        st.altair_chart(chart, use_container_width=True)

    with col_b:
        st.markdown("**SpO₂ Trend**")
        chart2 = alt.Chart(trends).mark_line(color='#4caf50').encode(x='time:T', y='spo2:Q')
        st.altair_chart(chart2, use_container_width=True)

    with col_c:
        st.markdown("**Temperature Trend**")
        chart3 = alt.Chart(trends).mark_line(color='#ff9800').encode(x='time:T', y='temperature:Q')
        st.altair_chart(chart3, use_container_width=True)
