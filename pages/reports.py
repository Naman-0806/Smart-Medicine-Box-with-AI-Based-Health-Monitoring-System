import pandas as pd
import streamlit as st
from components.sidebar import render_sidebar
from firebase.auth_service import require_auth
from firebase.firebase_service import (
    get_all_patients,
    get_dashboard_data,
    get_patient_by_id,
    get_patient_reports,
    save_patient_report,
)
from src.report_generator import generate_html_report, generate_pdf_report
from src.ui import apply_theme_styles


def render_reports():
    render_sidebar()
    require_auth()
    apply_theme_styles()

    st.markdown("# 📊 Patient Health & Activity Reports")
    st.caption("Generate, save, and export comprehensive clinical reports for your selected patient.")
    st.divider()

    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")

    # Patient Selector Section scoped to owner_uid
    all_patients = get_all_patients(owner_uid=owner_uid)
    patient_options = {}

    if all_patients:
        for p in all_patients:
            p_id = p.get("patient_id") or p.get("id") or ""
            p_name = p.get("name") or p.get("full_name") or "Unnamed Patient"
            label = f"{p_name} ({p_id})"
            patient_options[label] = p_id

    current_selected_id = st.session_state.get("selected_patient_id")

    col_pat1, col_pat2 = st.columns([2, 1])
    with col_pat1:
        if patient_options:
            default_index = 0
            option_list = list(patient_options.keys())
            if current_selected_id:
                for idx, lbl in enumerate(option_list):
                    if patient_options[lbl] == current_selected_id:
                        default_index = idx
                        break

            selected_label = st.selectbox("Select Patient for Report Generation:", option_list, index=default_index)
            selected_patient_id = patient_options[selected_label]
            st.session_state["selected_patient_id"] = selected_patient_id
        else:
            st.warning("No registered patients found under your account. Please register a patient first.")
            return

    with col_pat2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # Fetch live Firebase data strictly for selected patient
    data = get_dashboard_data(selected_patient_id, owner_uid=owner_uid)
    patient = data.get("patient", {})
    metrics = data.get("metrics", {})
    medicines = data.get("medicines", [])
    trends = data.get("trends", [])
    alerts = data.get("alerts", [])
    ai_recs = data.get("ai", [])

    st.markdown("### 👤 Selected Patient Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Patient Name", patient.get("name") or patient.get("full_name") or "N/A")
    with col2:
        st.metric("Patient ID", patient.get("patient_id") or selected_patient_id or "N/A")
    with col3:
        st.metric("Age / Gender", f"{patient.get('age', 'N/A')} / {patient.get('gender', 'N/A')}")
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
        if isinstance(medicines, pd.DataFrame):
            st.dataframe(medicines, use_container_width=True, hide_index=True)
        elif isinstance(medicines, list) and medicines:
            st.dataframe(pd.DataFrame(medicines), use_container_width=True, hide_index=True)
        else:
            st.info("No medicine schedule records available.")

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
            st.info("No historical health trends available.")

    with tab5:
        st.subheader("📜 Saved Reports for this Patient")
        saved_reports = get_patient_reports(selected_patient_id)
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
            st.info("No saved reports found under subcollection `patients/{patientId}/reports` for this patient.")

    st.divider()
    st.markdown("### 📥 Download & Save Patient Report")

    p_id_str = patient.get("patient_id") or selected_patient_id or "patient"
    pdf_bytes = generate_pdf_report(patient, metrics, medicines, alerts, ai_recs, trends)
    html_str = generate_html_report(patient, metrics, medicines, alerts, ai_recs, trends)

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
            save_patient_report(selected_patient_id, {
                "report_type": "PDF",
                "file_name": f"patient_report_{p_id_str}.pdf",
                "health_score": metrics.get("health_score"),
                "generated_by": owner_uid,
            })

    with exp_col2:
        if st.download_button(
            label="🌐 Download HTML Report",
            data=html_str,
            file_name=f"patient_report_{p_id_str}.html",
            mime="text/html",
            use_container_width=True,
            key="dl_html_btn",
        ):
            save_patient_report(selected_patient_id, {
                "report_type": "HTML",
                "file_name": f"patient_report_{p_id_str}.html",
                "health_score": metrics.get("health_score"),
                "generated_by": owner_uid,
            })


render_reports()
