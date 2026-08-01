import streamlit as st
from firebase.auth_service import require_auth
from firebase.firebase_service import get_dashboard_data, save_ai_recommendation
from src.ui import apply_theme_styles


def _calculate_ai_insights(metrics, medicines, patient):
    p_name = (patient or {}).get("name") or (patient or {}).get("full_name") or "Patient"
    p_doctor = (patient or {}).get("doctor_name") or "Assigned Doctor"
    p_disease = (patient or {}).get("disease") or (patient or {}).get("existing_diseases") or ""

    hr = metrics.get("heart_rate")
    try:
        hr_val = float(hr) if hr is not None else None
    except (TypeError, ValueError):
        hr_val = None

    spo2 = metrics.get("spo2")
    try:
        spo2_val = float(spo2) if spo2 is not None else None
    except (TypeError, ValueError):
        spo2_val = None

    temp = metrics.get("temperature")
    try:
        temp_val = float(temp) if temp is not None else None
    except (TypeError, ValueError):
        temp_val = None

    taken_count = 0
    missed_count = 0
    total_meds = 0

    if hasattr(medicines, "iterrows"):
        total_meds = len(medicines)
        for _, row in medicines.iterrows():
            status = str(row.get("Status", "")).lower()
            if "taken" in status:
                taken_count += 1
            elif "missed" in status:
                missed_count += 1
    elif isinstance(medicines, (list, tuple)):
        total_meds = len(medicines)
        for item in medicines:
            if isinstance(item, dict):
                status = str(item.get("Status") or item.get("status") or "").lower()
                if "taken" in status:
                    taken_count += 1
                elif "missed" in status:
                    missed_count += 1

    total_past = taken_count + missed_count
    adherence_pct = int(round((taken_count / total_past) * 100)) if total_past > 0 else 100

    base_score = 100
    if hr_val is not None and (hr_val < 60 or hr_val > 100):
        base_score -= 15
    if spo2_val is not None and spo2_val < 95:
        base_score -= int((95 - spo2_val) * 5)
    if temp_val is not None and (temp_val < 36.0 or temp_val > 37.5):
        base_score -= 10
    if missed_count > 0:
        base_score -= min(20, missed_count * 8)

    health_score = max(0, min(100, int(base_score)))
    if metrics.get("health_score") is not None:
        try:
            health_score = int(float(metrics.get("health_score")))
        except (TypeError, ValueError):
            pass

    if health_score >= 80:
        overall_risk = "Low"
        risk_label = "Stable"
        summary_text = f"Health metrics for {p_name} indicate stable vital signs and high medication adherence."
    elif health_score >= 60:
        overall_risk = "Moderate"
        risk_label = "Monitor"
        summary_text = f"Health metrics for {p_name} show moderate vital fluctuations. Regular monitoring is recommended."
    else:
        overall_risk = "High"
        risk_label = "Critical"
        summary_text = f"Immediate attention required for {p_name}. Vital signs or medication adherence require urgent review."

    heart_risk = "Normal" if (hr_val and 60 <= hr_val <= 100) else ("High (Elevated)" if (hr_val and hr_val > 100) else ("Low (Bradycardia)" if hr_val else "Not Recorded"))
    oxygen_status = "Optimal" if (spo2_val and spo2_val >= 95) else ("Below Threshold (Low SpO2)" if spo2_val else "Not Recorded")
    temp_status = "Normal" if (temp_val and 36.0 <= temp_val <= 37.5) else ("Abnormal (Fever/Hypothermia)" if temp_val else "Not Recorded")

    recs = []
    if missed_count > 0:
        recs.append(f"• Review {missed_count} missed medication dose(s) for {p_name} with {p_doctor}.")
    else:
        recs.append(f"• Continue taking all {total_meds} prescribed medication(s) on schedule.")

    if spo2_val and spo2_val < 95:
        recs.append(f"• Oxygen saturation is {spo2_val}%. Ensure proper ventilation and consult {p_doctor} if dyspnea persists.")
    else:
        recs.append("• Maintain daily light activity and healthy hydration habits.")

    if hr_val and hr_val > 100:
        recs.append(f"• Heart rate is elevated ({int(hr_val)} bpm). Rest in a cool area and limit physical stress.")
    elif hr_val and hr_val < 60:
        recs.append(f"• Heart rate is low ({int(hr_val)} bpm). Rest comfortably and monitor for dizziness.")
    else:
        recs.append("• Maintain regular sleep schedule and stress management.")

    if p_disease:
        recs.append(f"• Follow specialized care guidelines for pre-existing condition: {p_disease}.")
    recs.append(f"• Routine follow-up scheduled with {p_doctor}.")

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
    require_auth()
    apply_theme_styles()

    st.markdown("# 🧠 AI Insights")
    st.caption("A concise summary of patient health status and AI-generated care recommendations.")
    st.divider()

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    data = get_dashboard_data(user_uid, owner_uid=user_uid)

    if data.get("no_patients") or not data.get("patient"):
        st.warning("📝 No patient profile registered yet. Please register your patient profile first.")
        if st.button("📝 Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
        return

    patient = data.get("patient", {})
    metrics = data.get("metrics", {})
    medicines = data.get("medicines")

    insights = _calculate_ai_insights(metrics, medicines, patient)

    # Persist generated recommendations to users/{user_uid}/ai_recommendations
    for rec in insights["recommendations"]:
        save_ai_recommendation(user_uid, rec)

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
