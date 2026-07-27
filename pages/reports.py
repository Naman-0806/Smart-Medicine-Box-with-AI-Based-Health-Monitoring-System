import pandas as pd
import streamlit as st
from components.sidebar import render_sidebar
from firebase.firebase_service import get_all_patients, get_dashboard_data, get_patient_by_id
from src.report_generator import generate_html_report, generate_pdf_report
from src.ui import apply_theme_styles


def render_reports():
    render_sidebar()
    apply_theme_styles()

    st.markdown("# 📊 Patient Health & Activity Reports")
    st.caption("Generate and export comprehensive clinical reports using live Firebase data.")
    st.divider()

    is_logged_in = st.session_state.get("is_logged_in", False)
    owner_uid = st.session_state.get("owner_uid")

    if not is_logged_in or not owner_uid:
        st.warning("⚠️ Please log in or sign up in the sidebar to generate reports for your patients.")
        return

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

    # Fetch live Firebase data for selected patient
    data = get_dashboard_data(selected_patient_id, owner_uid=owner_uid)
    patient = data.get("patient", {})
    metrics = data.get("metrics", {})
    medicines = data.get("medicines", [])
    trends = data.get("trends", [])
    alerts = data.get("alerts", [])
    ai_recs = data.get("ai", [])

    st.markdown("### 👤 Patient Overview")
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

    # Preview Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["❤️ Vitals & Metrics", "💊 Medication Schedule", "🚨 Alerts & AI Recommendations", "📈 Health Trends"])

    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Heart Rate", f"{metrics.get('heart_rate', 'N/A')} bpm")
        c2.metric("SpO₂ Level", f"{metrics.get('spo2', 'N/A')} %")
        c3.metric("Body Temperature", f"{metrics.get('temperature', 'N/A')} °C")
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

    st.divider()
    st.markdown("### 📥 Download & Export Report")

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        pdf_bytes = generate_pdf_report(patient, metrics, medicines, alerts, ai_recs, trends)
        p_id_str = patient.get("patient_id") or selected_patient_id or "patient"
        st.download_button(
            label="📄 Download PDF Clinical Report",
            data=pdf_bytes,
            file_name=f"patient_report_{p_id_str}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )

    with exp_col2:
        html_str = generate_html_report(patient, metrics, medicines, alerts, ai_recs, trends)
        st.download_button(
            label="🌐 Download HTML Report",
            data=html_str,
            file_name=f"patient_report_{p_id_str}.html",
            mime="text/html",
            use_container_width=True,
        )


render_reports()
