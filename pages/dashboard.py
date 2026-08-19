import altair as alt
import pandas as pd
import streamlit as st
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


def render_dashboard():
    require_auth()

    # 1. Title + one short description
    st.title("Smart Medicine Box Dashboard")
    st.caption("Live overview of patient wellness, medication activity, and system status.")

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    # Fetch dashboard data scoped strictly to authenticated user_uid
    data = get_dashboard_data(user_uid, owner_uid=user_uid, force_refresh=True) or {}

    if data.get("no_patients") or not data.get("patient"):
        st.warning("No patient profile found for your account. Please register your patient profile first.")
        if st.button("Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
        return

    patient = data.get("patient", {}) or {}
    metrics = data.get("metrics", {}) or {}
    alerts = _normalize_collection(data.get("alerts", []), [])
    medicines = data.get("medicines")
    trends_df = data.get("trends")

    heart_rate = _safe_number(metrics.get("heart_rate"), 0)
    spo2 = _safe_number(metrics.get("spo2"), 0)
    temperature = _safe_number(metrics.get("temperature"), 0)
    score = _safe_number(metrics.get("health_score"), 100)

    raw_sync = patient.get("last_sync") or metrics.get("updated_at") or "Just Now"
    last_sync = str(raw_sync).split("T")[0] if "T" in str(raw_sync) else str(raw_sync)
    battery_level = patient.get("battery_level") if patient.get("battery_level") is not None else metrics.get("battery_level", 90)
    device_status = patient.get("device_status") or metrics.get("device_status") or "Connected"

    # Calculate Medication Adherence
    taken_count = 0
    missed_count = 0
    total_meds_count = 0
    medicines_df = None

    if isinstance(medicines, pd.DataFrame):
        total_meds_count = len(medicines)
        medicines_df = medicines.copy()
        if not medicines.empty and "Status" in medicines.columns:
            for _, row in medicines.iterrows():
                status = str(row.get("Status", "")).lower()
                if "taken" in status:
                    taken_count += 1
                elif "missed" in status:
                    missed_count += 1
    elif isinstance(medicines, (list, tuple)):
        total_meds_count = len(medicines)
        if medicines:
            medicines_df = pd.DataFrame(medicines)
        for item in medicines:
            if isinstance(item, dict):
                status = str(item.get("Status") or item.get("status") or "").lower()
                if "taken" in status:
                    taken_count += 1
                elif "missed" in status:
                    missed_count += 1

    total_past = taken_count + missed_count
    adherence_pct = int(round((taken_count / total_past) * 100)) if total_past > 0 else 100

    # 2. Health Overview using 3-4 st.metric components
    st.subheader("Health Overview")
    ov1, ov2, ov3, ov4 = st.columns(4)
    with ov1:
        hr_display = f"{int(heart_rate)} bpm" if heart_rate > 0 else "N/A"
        st.metric("Heart Rate", hr_display)
    with ov2:
        spo2_display = f"{int(spo2)}%" if spo2 > 0 else "N/A"
        st.metric("SpO₂", spo2_display)
    with ov3:
        temp_display = f"{temperature:.1f} °C" if temperature > 0 else "N/A"
        st.metric("Temperature", temp_display)
    with ov4:
        st.metric("Medication Adherence", f"{adherence_pct}%")

    # 3. Today's Medicines using a simple table
    st.subheader("Today's Medicines")
    if medicines_df is not None and not medicines_df.empty:
        display_cols = [col for col in ["Medicine", "Dosage", "Time", "Status"] if col in medicines_df.columns]
        if not display_cols:
            display_cols = medicines_df.columns.tolist()
        st.dataframe(medicines_df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No medications scheduled for today.")

    # 4. Health Activity using existing native Streamlit charts
    st.subheader("Health Activity")
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
            .properties(height=240)
        )
        st.caption("Vital Trend")
        st.altair_chart(line_chart, use_container_width=True)
    else:
        st.info("No vital telemetry readings recorded yet.")

    ch_col1, ch_col2 = st.columns(2)
    with ch_col1:
        bar_df = pd.DataFrame(
            {
                "Metric": ["Heart Rate", "SpO₂", "Temperature", "Health Score"],
                "Value": [heart_rate, spo2, temperature, score],
            }
        )
        bar_chart = (
            alt.Chart(bar_df)
            .mark_bar(color="#60a5fa", cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("Metric", sort=None, title=""),
                y=alt.Y("Value", title=""),
                tooltip=["Metric", "Value"],
            )
            .configure_view(fill='transparent')
            .properties(height=200)
        )
        st.caption("Vitals Overview")
        st.altair_chart(bar_chart, use_container_width=True)

    with ch_col2:
        pie_df = pd.DataFrame(
            {
                "Category": ["Health Score", "Alerts", "Medicines"],
                "Count": [int(score), len(alerts), total_meds_count],
            }
        )
        pie_chart = (
            alt.Chart(pie_df)
            .mark_arc(innerRadius=55, stroke="#ffffff", strokeWidth=1)
            .encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Category", type="nominal", legend=alt.Legend(title="")),
                tooltip=["Category", "Count"],
            )
            .configure_view(fill='transparent')
            .properties(height=200)
        )
        st.caption("Care Distribution")
        st.altair_chart(pie_chart, use_container_width=True)

    # 5. System Status showing device status and last sync
    st.subheader("System Status")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Device Status", device_status)
    with sc2:
        st.metric("Last Sync", last_sync)
    with sc3:
        st.metric("Battery Level", f"{battery_level}%")

    # Alerts (Clean native expander if alerts exist)
    if alerts:
        with st.expander("Recent Alerts", expanded=False):
            for alert in alerts:
                if isinstance(alert, dict):
                    st.write(f"• {alert.get('text', '')}")
                else:
                    st.write(f"• {alert}")

    # ESP32 Device Testing Telemetry
    with st.expander("ESP32 Live Device Telemetry", expanded=False):
        st.caption("Transmit live ESP32 vitals directly to Cloud Firestore under patients/{uid}/health/latest.")
        e_c1, e_c2, e_c3, e_c4 = st.columns(4)
        with e_c1:
            in_hr = st.number_input("Heart Rate (bpm)", min_value=30.0, max_value=220.0, value=75.0, step=1.0)
        with e_c2:
            in_spo2 = st.number_input("SpO₂ (%)", min_value=50.0, max_value=100.0, value=98.0, step=1.0)
        with e_c3:
            in_temp = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=36.8, step=0.1)
        with e_c4:
            st.write("")
            transmit_btn = st.button("Transmit Telemetry", use_container_width=True)

        if transmit_btn:
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


render_dashboard()
