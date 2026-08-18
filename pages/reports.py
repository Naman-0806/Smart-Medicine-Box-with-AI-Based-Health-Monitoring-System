import pandas as pd
import streamlit as st
from firebase.auth_service import require_auth
from firebase.firebase_service import (
    get_dashboard_data,
    get_patient_by_id,
    get_patient_reports,
    save_patient_report,
)
from src.report_generator import generate_html_report, generate_pdf_report
from src.ui import apply_theme_styles


def render_reports():
    require_auth()
    apply_theme_styles()

    st.markdown("# 📊 Patient Health & Activity Reports")
    st.caption("Generate, save, and export comprehensive clinical reports from your Cloud Firestore health data.")
    st.divider()

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    selected_patient_id = user_uid
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    patient = get_patient_by_id(user_uid, force_refresh=True)
    if not patient:
        st.warning("📝 No patient profile registered yet. Please register your patient profile first.")
        if st.button("📝 Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
        return

    st.caption(f"Patient Profile: **{patient.get('name') or patient.get('full_name')}** (ID: `{user_uid}`)")

    if st.button("🔄 Refresh Data"):
        st.rerun()

    # Fetch live Cloud Firestore data strictly for authenticated logged-in user
    data = get_dashboard_data(user_uid, owner_uid=user_uid, force_refresh=True)
    patient = data.get("patient", {})
    metrics = data.get("metrics", {})
    medicines = data.get("medicines", [])
    trends = data.get("trends", [])
    alerts = data.get("alerts", [])
    ai_recs = data.get("ai", [])

    st.markdown("### 👤 Logged In Patient Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patient Name", patient.get("name") or patient.get("full_name") or "N/A")
    with col2:
        st.metric("Patient ID", patient.get("patient_id") or user_uid or "N/A")
    with col3:
        st.metric("Age / Gender", f"{patient.get('age', 'N/A')} yrs / {patient.get('gender', 'N/A')}")
    with col4:
        st.metric("Assigned Doctor", patient.get("doctor_name", "N/A"))

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "❤️ Vitals & Metrics",
        "💊 Medication Schedule",
        "🚨 Alerts & AI Recommendations",
        "📈 Health Trends",
        "📜 Saved Reports History"
    ])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Heart Rate", f"{metrics.get('heart_rate', 'N/A')} bpm" if metrics.get('heart_rate') is not None else "N/A")
        c2.metric("SpO₂ Level", f"{metrics.get('spo2', 'N/A')} %" if metrics.get('spo2') is not None else "N/A")
        c3.metric("Body Temperature", f"{metrics.get('temperature', 'N/A')} °C" if metrics.get('temperature') is not None else "N/A")
        c4.metric("Blood Pressure", f"{metrics.get('blood_pressure', 'N/A')}")

    with tab2:
        if isinstance(medicines, pd.DataFrame) and not medicines.empty:
            st.dataframe(medicines, use_container_width=True, hide_index=True)
        elif isinstance(medicines, list) and medicines:
            st.dataframe(pd.DataFrame(medicines), use_container_width=True, hide_index=True)
        else:
            st.info("No medication records found in Firestore for your account.")

    with tab3:
        st.subheader("Recent Alerts")
        if alerts:
            for alert in alerts:
                if isinstance(alert, dict):
                    st.write(f"• **[{alert.get('type', 'info').upper()}]** {alert.get('text', '')}")
                else:
                    st.write(f"• {alert}")
        else:
            st.caption("No alerts recorded.")

        st.subheader("AI Recommendations")
        if ai_recs:
            for rec in ai_recs:
                st.write(f"💡 {rec}")
        else:
            st.caption("No AI recommendations available.")

    with tab4:
        if isinstance(trends, pd.DataFrame) and not trends.empty:
            st.dataframe(trends, use_container_width=True, hide_index=True)
        else:
            st.info("No historical health trends recorded in Firestore.")

    with tab5:
        st.subheader("📜 Saved Reports for Your Account")
        saved_reports = get_patient_reports(user_uid)
        if saved_reports:
            rpt_rows = []
            for r in saved_reports:
                rpt_rows.append({
                    "Report ID": r.get("id") or r.get("report_id"),
                    "Type": r.get("report_type", "PDF"),
                    "File Name": r.get("file_name", ""),
                    "Health Score": r.get("health_score", "N/A"),
                    "Generated At": r.get("created_at", ""),
                })
            st.dataframe(pd.DataFrame(rpt_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No saved reports found under `patients/{patientId}/reports` for your account.")

    st.divider()
    st.markdown("### 📥 Download & Save Clinical Report")

    p_id_str = patient.get("patient_id") or user_uid or "patient"
    try:
        pdf_bytes = generate_pdf_report(data)
        html_str = generate_html_report(data)
    except Exception as ex:
        st.error(f"Error generating clinical report: {str(ex)}")
        pdf_bytes = b""
        html_str = ""

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        if st.download_button(
            label="📄 Download PDF Clinical Report",
            data=pdf_bytes,
            file_name=f"patient_report_{p_id_str}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="dl_pdf_btn",
        ):
            try:
                with st.spinner("Saving PDF report metadata to Cloud Firestore..."):
                    save_patient_report(user_uid, {
                        "report_type": "PDF",
                        "file_name": f"patient_report_{p_id_str}.pdf",
                        "health_score": metrics.get("health_score"),
                        "generated_by": user_uid,
                    })
                st.success("PDF Report record saved to Cloud Firestore.")
            except Exception as ex:
                st.error(f"Failed to save report record: {str(ex)}")

    with exp_col2:
        if st.download_button(
            label="🌐 Download HTML Report",
            data=html_str,
            file_name=f"patient_report_{p_id_str}.html",
            mime="text/html",
            use_container_width=True,
            key="dl_html_btn",
        ):
            try:
                with st.spinner("Saving HTML report metadata to Cloud Firestore..."):
                    save_patient_report(user_uid, {
                        "report_type": "HTML",
                        "file_name": f"patient_report_{p_id_str}.html",
                        "health_score": metrics.get("health_score"),
                        "generated_by": user_uid,
                    })
                st.success("HTML Report record saved to Cloud Firestore.")
            except Exception as ex:
                st.error(f"Failed to save report record: {str(ex)}")


render_reports()
