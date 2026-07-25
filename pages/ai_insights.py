import streamlit as st
from components.sidebar import render_sidebar
from firebase.firebase_service import get_dashboard_data
from src.data import get_all_dummy_data
from src.ui import apply_theme_styles


def _calculate_ai_insights(metrics, medicines):
    hr = metrics.get("heart_rate")
    try:
        hr = float(hr)
    except (TypeError, ValueError):
        hr = 76.0

    spo2 = metrics.get("spo2")
    try:
        spo2 = float(spo2)
    except (TypeError, ValueError):
        spo2 = 97.0

    temp = metrics.get("temperature")
    try:
        temp = float(temp)
    except (TypeError, ValueError):
        temp = 36.7

    taken_count = 0
    missed_count = 0
    if hasattr(medicines, "iterrows"):
        for _, row in medicines.iterrows():
            status = str(row.get("Status", "")).lower()
            if "taken" in status:
                taken_count += 1
            elif "missed" in status:
                missed_count += 1
    elif isinstance(medicines, (list, tuple)):
        for item in medicines:
            if isinstance(item, dict):
                status = str(item.get("Status") or item.get("status") or "").lower()
                if "taken" in status:
                    taken_count += 1
                elif "missed" in status:
                    missed_count += 1

    total_past = taken_count + missed_count
    adherence_pct = int(round((taken_count / total_past) * 100)) if total_past > 0 else 90

    base_score = 100
    if hr < 60 or hr > 100:
        base_score -= 15
    if spo2 < 95:
        base_score -= (95 - int(spo2)) * 5
    if temp < 36.0 or temp > 37.5:
        base_score -= 10
    if missed_count > 0:
        base_score -= min(20, missed_count * 8)

    health_score = max(0, min(100, int(base_score)))
    if metrics.get("health_score") is not None:
        try:
            health_score = int(metrics.get("health_score"))
        except (TypeError, ValueError):
            pass

    if health_score >= 80:
        overall_risk = "Low"
        risk_label = "Stable"
        summary_text = f"Your recent health pattern appears stable with good medication adherence and no immediate concern (Health Score: {health_score}/100). The system suggests continued monitoring and routine follow-up."
    elif health_score >= 60:
        overall_risk = "Medium"
        risk_label = "Monitor"
        summary_text = f"Your recent health pattern shows moderate activity (Health Score: {health_score}/100). Some vitals or medication reminders require closer monitoring."
    else:
        overall_risk = "High"
        risk_label = "Attention Needed"
        summary_text = f"Your recent health indicators require attention (Health Score: {health_score}/100). Caregiver review and vital checkups are advised."

    if 60 <= hr <= 100:
        heart_risk = "Low Risk"
    elif 50 <= hr < 60 or 100 < hr <= 110:
        heart_risk = "Medium Risk"
    else:
        heart_risk = "High Risk"

    if spo2 >= 95:
        oxygen_status = "Normal"
    elif spo2 >= 90:
        oxygen_status = "Warning"
    else:
        oxygen_status = "Critical"

    if 36.1 <= temp <= 37.5:
        temp_status = "Normal"
    elif temp > 37.5:
        temp_status = "Fever"
    else:
        temp_status = "Low"

    recs = []
    if missed_count > 0:
        recs.append(f"• Review missed medication doses ({missed_count}) with your caregiver.")
    else:
        recs.append("• Continue taking prescribed medicines on time.")

    if spo2 < 95:
        recs.append(f"• Monitor oxygen levels closely (current: {spo2}%). Rest in a well-ventilated area.")
    else:
        recs.append("• Keep a light walking routine daily.")

    if hr > 100:
        recs.append(f"• Heart rate is elevated ({int(hr)} bpm). Avoid strenuous exercise and stay hydrated.")
    elif hr < 60:
        recs.append(f"• Heart rate is lower than average ({int(hr)} bpm). Rest comfortably and track symptoms.")
    else:
        recs.append("• Stay hydrated and maintain regular sleep.")

    recs.append("• Review medications with your caregiver weekly.")
    recs.append("• Seek medical advice if symptoms worsen.")

    return {
        "score": health_score,
        "adherence": adherence_pct,
        "overall_risk": overall_risk,
        "risk_label": risk_label,
        "summary": summary_text,
        "taken": taken_count,
        "missed": missed_count,
        "heart_risk": heart_risk,
        "oxygen_status": oxygen_status,
        "temp_status": temp_status,
        "recommendations": recs,
    }


def render_ai():
    apply_theme_styles() 
    render_sidebar()

    st.markdown("# AI Insights")
    st.caption("A concise summary of health status and personalized recommendations.")
    st.divider()

    selected_patient_id = st.session_state.get("selected_patient_id")
    data = get_dashboard_data(selected_patient_id) if selected_patient_id else get_all_dummy_data()

    metrics = data.get("metrics", {})
    medicines = data.get("medicines")

    insights = _calculate_ai_insights(metrics, medicines)

    with st.container(border=True):
        st.subheader("AI Health Summary")
        st.write(insights["summary"])
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI Health Score", f"{insights['score']} / 100", "Good" if insights['score'] >= 80 else ("Moderate" if insights['score'] >= 60 else "Attention"))
        with c2:
            st.metric("Adherence", f"{insights['adherence']}%")
        with c3:
            st.metric("Overall Risk", insights['overall_risk'], insights['risk_label'])

    st.divider()
    with st.container(border=True):
        st.subheader("Medication Adherence")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Medicines Taken", str(insights['taken']))
        with c2:
            st.metric("Missed Doses", str(insights['missed']))
        with c3:
            st.metric("Adherence %", f"{insights['adherence']}%")

    st.divider()
    with st.container(border=True):
        st.subheader("Health Risk Analysis")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Heart Health", insights['heart_risk'])
        with c2:
            st.metric("Oxygen Level", insights['oxygen_status'])
        with c3:
            st.metric("Temperature", insights['temp_status'])
        with c4:
            st.metric("Overall Risk", insights['overall_risk'])

    st.divider()
    with st.container(border=True):
        st.subheader("Personalized Recommendations")
        for rec in insights["recommendations"]:
            st.write(rec)

    st.divider()
    with st.container(border=True):
        st.subheader("Emergency Alerts")
        if insights['overall_risk'] == "High" or insights['oxygen_status'] == "Critical":
            st.error(f"Attention Needed: Patient vitals indicate {insights['overall_risk']} Risk.")
        else:
            st.info("No Emergency Detected")

    st.divider()
    with st.container(border=True):
        st.subheader("Weekly AI Summary")
        st.write(f"• Health Score: {insights['score']}/100 ({insights['overall_risk']} Risk).")
        st.write(f"• Medication adherence rate: {insights['adherence']}%.")
        st.write(f"• Heart Health Status: {insights['heart_risk']}.")
        st.write(f"• Oxygen Saturation Status: {insights['oxygen_status']}.")
        st.write("• Continue routine monitoring and follow-up care.")


render_ai()
