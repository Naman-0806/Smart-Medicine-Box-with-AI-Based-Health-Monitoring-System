import time
import altair as alt
import pandas as pd
import streamlit as st
from components.cards import patient_card
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

    st.markdown("# 🩺 Smart Medicine Box Dashboard", unsafe_allow_html=True)
    st.caption("Live overview of patient wellness, medication activity, and care alerts.")

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    # Fetch dashboard data scoped strictly to authenticated user_uid
    data = get_dashboard_data(user_uid, owner_uid=user_uid, force_refresh=True) or {}

    if data.get("no_patients") or not data.get("patient"):
        st.warning("📝 No patient profile found for your account. Please register your patient profile first.")
        if st.button("📝 Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
        return

    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}
    alerts = _normalize_collection(data.get("alerts", []), [])
    medicines = data.get("medicines")
    trends_df = data.get("trends")

    # Extract dynamic logged in user metrics
    patient_name = patient.get("name") or patient.get("full_name") or "N/A"

    # Calculate medicine count and upcoming medicines
    total_meds_count = 0
    upcoming_meds_df = pd.DataFrame(columns=["Medicine", "Dosage", "Time", "Status"])

    if isinstance(medicines, pd.DataFrame):
        total_meds_count = len(medicines)
        if not medicines.empty and "Status" in medicines.columns:
            upcoming_meds_df = medicines[medicines["Status"].astype(str).str.lower() == "upcoming"]
    elif isinstance(medicines, list):
        total_meds_count = len(medicines)
        upcoming_items = [m for m in medicines if isinstance(m, dict) and str(m.get("Status") or m.get("status")).lower() == "upcoming"]
        if upcoming_items:
            upcoming_meds_df = pd.DataFrame(upcoming_items)

    # Health status calculation
    score = _safe_number(metrics.get("health_score"), 100)
    if score >= 80:
        health_status = "Stable (Good)"
    elif score >= 60:
        health_status = "Monitor (Moderate)"
    else:
        health_status = "Attention Needed"

    raw_sync = patient.get("last_sync") or metrics.get("updated_at") or "Just Now"
    last_sync = str(raw_sync).split("T")[0] if "T" in str(raw_sync) else str(raw_sync)
    battery_level = patient.get("battery_level") if patient.get("battery_level") is not None else metrics.get("battery_level", 90)
    device_status = patient.get("device_status") or metrics.get("device_status") or "Connected"

    # Display Top Metrics Row (Patient Name, Medicine Count, Health Status, Last Sync, Battery Level)
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Patient Name", patient_name)
    with m2:
        st.metric("Total Medicines", str(total_meds_count))
    with m3:
        st.metric("Health Status", health_status, f"{int(score)} / 100")
    with m4:
        st.metric("Last Sync", last_sync)
    with m5:
        st.metric("Battery Level", f"{battery_level}%", device_status)

    st.divider()

    # ESP32 Device Testing Expander
    with st.expander("📡 ESP32 Live Device Telemetry", expanded=False):
        st.write("Transmit live ESP32 vitals directly to Cloud Firestore under `patients/{uid}/health/latest`.")
        e_c1, e_c2, e_c3, e_c4 = st.columns(4)
        with e_c1:
            in_hr = st.number_input("Heart Rate (bpm)", min_value=30.0, max_value=220.0, value=75.0, step=1.0)
        with e_c2:
            in_spo2 = st.number_input("SpO₂ (%)", min_value=50.0, max_value=100.0, value=98.0, step=1.0)
        with e_c3:
            in_temp = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=36.8, step=0.1)
        with e_c4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📡 Transmit Telemetry", use_container_width=True):
                try:
                    with st.spinner("Transmitting telemetry to Cloud Firestore..."):
                        res = process_esp32_data(in_hr, in_spo2, in_temp, patient_id=user_uid)
                    if res.get("success"):
                        st.success(f"Vitals saved to Firestore! (Reading ID: {res.get('reading_id')})")
                        st.rerun()
                    else:
                        st.error("Failed to transmit reading to Cloud Firestore.")
                except Exception as ex:
                    st.error(f"Telemetry transmission failed: {str(ex)}")

    st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

    heart_rate = _safe_number(metrics.get("heart_rate"), 0)
    spo2 = _safe_number(metrics.get("spo2"), 0)
    temperature = _safe_number(metrics.get("temperature"), 0)

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
                st.caption("No vital telemetry readings recorded yet in Firestore.")

        st.write("")
        col_a, col_b = st.columns([1, 1], gap="small")
        with col_a:
            bar_df = pd.DataFrame(
                {
                    "Metric": ["Heart Rate", "SpO₂", "Temperature", "Health Score"],
                    "Value": [heart_rate, spo2, temperature, score],
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
                    "Count": [int(score), len(alerts), total_meds_count],
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
        _render_progress_indicators(score, spo2, heart_rate)

        st.write("")
        with st.container(border=True):
            st.markdown("<div class='section-title'>💊 Upcoming Medicines</div>", unsafe_allow_html=True)
            if not upcoming_meds_df.empty:
                medicine_table(upcoming_meds_df)
            elif isinstance(medicines, pd.DataFrame) and not medicines.empty:
                st.caption("No medicines with 'Upcoming' status. Displaying all scheduled medications:")
                medicine_table(medicines)
            else:
                st.info("No medicine schedule recorded in Firestore.")


render_dashboard()
