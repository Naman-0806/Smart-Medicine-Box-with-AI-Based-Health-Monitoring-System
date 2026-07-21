import pandas as pd
import altair as alt
import streamlit as st
from components.sidebar import render_sidebar
from components.cards import patient_card
from components.tables import medicine_table
from firebase.firebase_service import get_dashboard_data


def _safe_number(value, default=0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_collection(value, default=None):
    if value is None:
        return [] if default is None else default
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, dict):
        return [value]
    if hasattr(value, "tolist"):
        return value.tolist()
    return [value]


def _render_chart_card(title, chart):
    with st.container(border=True):
        st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.altair_chart(chart, use_container_width=True)


def _render_progress_indicators(health_score, spo2, heart_rate):
    with st.container(border=True):
        st.markdown("<div class='section-title'>Progress Overview</div>", unsafe_allow_html=True)
        progress_col_1, progress_col_2 = st.columns([1, 1], gap="small")
        with progress_col_1:
            st.markdown(
                f"""
                <div style="display:flex; flex-direction:column; align-items:center; padding:12px 8px; border-radius:18px; background:rgba(255,255,255,0.7);">
                    <div style="width:96px; height:96px; border-radius:50%; background:conic-gradient(#2563eb {int(health_score)}%, #e2e8f0 0); display:flex; align-items:center; justify-content:center; box-shadow: inset 0 0 0 10px rgba(255,255,255,0.8);">
                        <div style="width:62px; height:62px; border-radius:50%; background:white; display:flex; align-items:center; justify-content:center; font-weight:700; color:#0f172a;">{int(health_score)}%</div>
                    </div>
                    <div style="margin-top:10px; font-size:0.9rem; color:#475569;">Overall Wellness</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with progress_col_2:
            st.markdown(
                f"""
                <div style="padding:12px 10px; border-radius:18px; background:rgba(255,255,255,0.7);">
                    <div style="font-size:0.85rem; color:#64748b; margin-bottom:6px;">Oxygen Saturation</div>
                    <div style="height:8px; border-radius:999px; background:#e2e8f0; overflow:hidden; margin-bottom:8px;">
                        <div style="width:{min(100, max(0, int(spo2)))}%; height:100%; border-radius:999px; background:linear-gradient(90deg, #34d399, #10b981);"></div>
                    </div>
                    <div style="font-size:0.88rem; font-weight:700; color:#0f172a;">{int(spo2)}%</div>
                    <div style="font-size:0.85rem; color:#64748b; margin-top:10px;">Heart Rate</div>
                    <div style="height:8px; border-radius:999px; background:#e2e8f0; overflow:hidden; margin-bottom:8px;">
                        <div style="width:{min(100, max(0, int((heart_rate / 120) * 100)))}%; height:100%; border-radius:999px; background:linear-gradient(90deg, #60a5fa, #2563eb);"></div>
                    </div>
                    <div style="font-size:0.88rem; font-weight:700; color:#0f172a;">{int(heart_rate)} bpm</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_dashboard():
    data = get_dashboard_data() or {}
    render_sidebar()

    if data.get("offline"):
        st.warning("Running in Offline Mode")

    st.markdown("# Smart Medicine Box Dashboard", unsafe_allow_html=True)
    st.caption("Live overview of patient wellness, medication activity, and care alerts.")
    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}
    alerts = _normalize_collection(data.get("alerts", []), [])
    medicines = _normalize_collection(data.get("medicines", []), [])

    heart_rate = _safe_number(metrics.get("heart_rate", 72), 72)
    spo2 = _safe_number(metrics.get("spo2", 97), 97)
    temperature = _safe_number(metrics.get("temperature", 36.8), 36.8)
    health_score = _safe_number(metrics.get("health_score", 82), 82)

    left_col, right_col = st.columns([1.08, 1.92], gap="large")
    with left_col:
        patient_card(patient)
        st.write("")
        with st.container(border=True):
            st.markdown("<div class='section-title'>Recent Alerts</div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 0.45rem;'></div>", unsafe_allow_html=True)
            for alert in alerts:
                if isinstance(alert, dict):
                    st.write(f"• {alert.get('text', '')}")
                else:
                    st.write(f"• {alert}")

    with right_col:
        trend_df = pd.DataFrame(
            {
                "Period": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "Heart Rate": [heart_rate - 2, heart_rate - 1, heart_rate, heart_rate + 1, heart_rate + 2],
                "Health Score": [health_score - 3, health_score - 1, health_score, health_score + 1, health_score + 2],
            }
        )

        line_chart = (
            alt.Chart(trend_df)
            .mark_line(point=True, strokeWidth=3, color="#2563eb")
            .encode(
                x=alt.X("Period", title=""),
                y=alt.Y("Heart Rate", title="BPM"),
                tooltip=["Period", "Heart Rate"],
            )
            .configure_view(fill='transparent')
            .properties(height=220)
        )
        _render_chart_card("Vital Trend", line_chart)

        st.write("")
        col_a, col_b = st.columns([1, 1], gap="small")
        with col_a:
            bar_df = pd.DataFrame(
                {
                    "Metric": ["Heart Rate", "SpO₂", "Temperature", "Health Score"],
                    "Value": [heart_rate, spo2, temperature, health_score],
                }
            )
            bar_chart = (
                alt.Chart(bar_df)
                .mark_bar(color="#60a5fa", cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("Metric", sort=None, title=""),
                    y=alt.Y("Value", title=""),
                    tooltip=["Metric", "Value"],
                )
                .configure_view(fill='transparent')
                .properties(height=220)
            )
            _render_chart_card("Vitals Overview", bar_chart)

        with col_b:
            pie_df = pd.DataFrame(
                {
                    "Category": ["Adherence", "Alerts", "Medicines"],
                    "Count": [max(1, int(health_score)), max(1, len(alerts)), max(1, len(medicines))],
                }
            )
            pie_chart = (
                alt.Chart(pie_df)
                .mark_arc(innerRadius=70, stroke="#ffffff", strokeWidth=1)
                .encode(
                    theta=alt.Theta(field="Count", type="quantitative"),
                    color=alt.Color(field="Category", type="nominal", legend=alt.Legend(title="")),
                    tooltip=["Category", "Count"],
                )
                .configure_view(fill='transparent')
                .properties(height=220)
            )
            _render_chart_card("Care Distribution", pie_chart)

        st.write("")
        area_df = pd.DataFrame(
            {
                "Day": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "Score": [health_score - 4, health_score - 2, health_score, health_score + 1, health_score + 2],
            }
        )
        area_chart = (
            alt.Chart(area_df)
            .mark_area(line=True, color="#93c5fd", opacity=0.45)
            .encode(
                x=alt.X("Day", title=""),
                y=alt.Y("Score", title="Score"),
                tooltip=["Day", "Score"],
            )
            .configure_view(fill='transparent')
            .properties(height=220)
        )
        _render_chart_card("Wellness Area", area_chart)

        st.write("")
        _render_progress_indicators(health_score, spo2, heart_rate)

        st.write("")
        with st.container(border=True):
            st.markdown("<div class='section-title'>Medicine Summary</div>", unsafe_allow_html=True)
            medicine_table(medicines)


render_dashboard()
