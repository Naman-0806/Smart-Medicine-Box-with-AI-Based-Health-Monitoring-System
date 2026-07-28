import time
import altair as alt
import pandas as pd
import streamlit as st
from components.cards import patient_card
from components.sidebar import render_sidebar
from components.tables import medicine_table
from firebase.auth_service import require_auth
from firebase.firebase_service import get_dashboard_data, process_esp32_data


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
    require_auth()
    render_sidebar()


    st.markdown("# Smart Medicine Box Dashboard", unsafe_allow_html=True)
    st.caption("Live overview of patient wellness, medication activity, and care alerts.")

    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")

    # Fetch dashboard data scoped to owner_uid
    selected_patient_id = st.session_state.get("selected_patient_id")
    data = get_dashboard_data(selected_patient_id, owner_uid=owner_uid) or {}

    if data.get("no_patients") or not data.get("patient"):
        st.info("⚠️ No patients found. Please register a patient.")
        st.markdown("""
        <div style='padding:20px; text-align:center;'>
            <p>You currently do not have any registered patients under your account.</p>
            <p>Go to the <b>Patient Management</b> tab in the sidebar to register a patient.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if data.get("offline"):
        st.warning("Running in Offline Mode")

    # ESP32 Live Telemetry Ingestion / Simulator Expander
    with st.expander("📡 ESP32 Device Ingestion & Testing", expanded=False):
        st.write("Simulate or transmit live ESP32 sensor values (`heart_rate`, `spo2`, `temperature`) directly into Firebase.")
        e_c1, e_c2, e_c3, e_c4 = st.columns(4)
        with e_c1:
            in_hr = st.number_input("Heart Rate (bpm)", min_value=30.0, max_value=220.0, value=75.0, step=1.0)
        with e_c2:
            in_spo2 = st.number_input("SpO₂ (%)", min_value=50.0, max_value=100.0, value=98.0, step=1.0)
        with e_c3:
            in_temp = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=36.8, step=0.1)
        with e_c4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📡 Send ESP32 Reading", use_container_width=True):
                res = process_esp32_data(in_hr, in_spo2, in_temp, patient_id=selected_patient_id)
                if res.get("success"):
                    st.success(f"ESP32 Vitals saved to Firebase! (Reading ID: {res.get('reading_id')})")
                    st.rerun()
                else:
                    st.error("Failed to transmit ESP32 reading.")

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}
    alerts = _normalize_collection(data.get("alerts", []), [])
    medicines = _normalize_collection(data.get("medicines", []), [])
    trends_df = data.get("trends")

    heart_rate = _safe_number(metrics.get("heart_rate"), 0)
    spo2 = _safe_number(metrics.get("spo2"), 0)
    temperature = _safe_number(metrics.get("temperature"), 0)
    health_score = _safe_number(metrics.get("health_score"), 0)

    left_col, right_col = st.columns([1.08, 1.92], gap="large")
    with left_col:
        patient_card(patient)
        st.write("")
        with st.container(border=True):
            st.markdown("<div class='section-title'>Recent Alerts</div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 0.45rem;'></div>", unsafe_allow_html=True)
            if alerts:
                for alert in alerts:
                    if isinstance(alert, dict):
                        st.write(f"• {alert.get('text', '')}")
                    else:
                        st.write(f"• {alert}")
            else:
                st.caption("No emergency alerts recorded.")

    with right_col:
        if isinstance(trends_df, pd.DataFrame) and not trends_df.empty:
            line_chart = (
                alt.Chart(trends_df)
                .mark_line(point=True, strokeWidth=3, color="#2563eb")
                .encode(
                    x=alt.X("time", title="Time"),
                    y=alt.Y("heart_rate", title="Heart Rate (BPM)"),
                    tooltip=["time", "heart_rate", "spo2", "temperature"],
                )
                .configure_view(fill='transparent')
                .properties(height=220)
            )
            _render_chart_card("Vital Trend", line_chart)
        else:
            with st.container(border=True):
                st.markdown("<div class='section-title'>Vital Trend</div>", unsafe_allow_html=True)
                st.caption("No vital telemetry readings recorded yet for this patient.")

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
                    "Category": ["Health Score", "Alerts", "Medicines"],
                    "Count": [int(health_score), len(alerts), len(medicines)],
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
        if isinstance(trends_df, pd.DataFrame) and not trends_df.empty:
            area_chart = (
                alt.Chart(trends_df)
                .mark_area(line=True, color="#93c5fd", opacity=0.45)
                .encode(
                    x=alt.X("time", title="Time"),
                    y=alt.Y("health_score", title="Score"),
                    tooltip=["time", "health_score"],
                )
                .configure_view(fill='transparent')
                .properties(height=220)
            )
            _render_chart_card("Wellness Area", area_chart)
        else:
            with st.container(border=True):
                st.markdown("<div class='section-title'>Wellness Area</div>", unsafe_allow_html=True)
                st.caption("No wellness history recorded yet for this patient.")

        st.write("")
        _render_progress_indicators(health_score, spo2, heart_rate)

        st.write("")
        with st.container(border=True):
            st.markdown("<div class='section-title'>Medicine Summary</div>", unsafe_allow_html=True)
            medicine_table(medicines)


render_dashboard()
