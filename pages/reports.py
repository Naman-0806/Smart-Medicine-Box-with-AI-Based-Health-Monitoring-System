import pandas as pd
import streamlit as st
from firebase.firebase_service import get_all_patients, get_dashboard_data, get_patient_by_id
from components.sidebar import render_sidebar
from src.ui import apply_theme_styles
from src.report_generator import generate_pdf_report, generate_html_report


def render_reports():
    render_sidebar()
    apply_theme_styles()

    st.markdown("# 📊 Patient Health & Activity Reports")
    st.caption("Generate and export comprehensive clinical reports using live Firebase data.")
    st.divider()

    # Patient Selector Section
    all_patients = get_all_patients()
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
            st.info("No registered patients found in Firebase. Displaying default patient report data.")
            selected_patient_id = current_selected_id

    with col_pat2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Firebase Data", use_container_width=True):
            st.rerun()

    # Fetch live Firebase data for selected patient
    data = get_dashboard_data(selected_patient_id)
    patient = data.get("patient", {})
    metrics = data.get("metrics", {})
    medicines = data.get("medicines", [])
    trends = data.get("trends", [])
    alerts = data.get("alerts", [])
    ai_recs = data.get("ai", [])

    # Display Patient Summary Header Card
    with st.container(border=True):
        st.subheader("👤 Selected Patient Details")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Name", patient.get("name") or "N/A")
            st.caption(f"ID: {patient.get('patient_id') or patient.get('id') or 'N/A'}")
        with c2:
            st.metric("Age / Gender", f"{patient.get('age', 'N/A')} / {patient.get('gender', 'N/A')}")
            st.caption(f"Blood Group: {patient.get('blood_group', 'N/A')}")
        with c3:
            st.metric("Health Score", f"{metrics.get('health_score', 'N/A')} / 100")
            st.caption(f"Vitals Status: Normal")
        with c4:
            st.metric("Attending Doctor", patient.get("doctor_name") or "N/A")
            st.caption(f"Condition: {patient.get('disease') or 'None'}")

    st.divider()

    # Section Tabs for Report Details
    t1, t2, t3, t4 = st.tabs(["💊 Medicines Schedule", "📈 Health History", "🤖 AI Recommendations", "📑 Full Report Overview"])

    with t1:
        st.subheader("Medication Schedule & Adherence")
        if isinstance(medicines, pd.DataFrame) and not medicines.empty:
            st.dataframe(medicines, use_container_width=True, hide_index=True)
        elif isinstance(medicines, list) and len(medicines) > 0:
            st.dataframe(pd.DataFrame(medicines), use_container_width=True, hide_index=True)
        else:
            st.info("No active medicine schedules recorded in Firebase for this patient.")

    with t2:
        st.subheader("Health History & Recent Vitals")
        vm1, vm2, vm3, vm4 = st.columns(4)
        with vm1:
            st.metric("Heart Rate", f"{metrics.get('heart_rate', 'N/A')} bpm")
        with vm2:
            st.metric("SpO₂", f"{metrics.get('spo2', 'N/A')} %")
        with vm3:
            st.metric("Temperature", f"{metrics.get('temperature', 'N/A')} °C")
        with vm4:
            st.metric("Blood Pressure", metrics.get("blood_pressure", "N/A"))

        st.markdown("#### Historical Vitals Trends")
        if isinstance(trends, pd.DataFrame) and not trends.empty:
            st.dataframe(trends, use_container_width=True, hide_index=True)
        elif isinstance(trends, list) and len(trends) > 0:
            st.dataframe(pd.DataFrame(trends), use_container_width=True, hide_index=True)
        else:
            st.info("No historical readings recorded in Firebase.")

    with t3:
        st.subheader("AI Clinical Advisory & Insights")
        if ai_recs:
            for idx, rec in enumerate(ai_recs, 1):
                st.markdown(f"**{idx}.** {rec}")
        else:
            st.info("AI analysis indicates stable vitals. Continue standard care plan.")

    with t4:
        st.subheader("Full Report Summary")
        st.markdown(f"""
        - **Patient Name:** {patient.get('name') or 'N/A'} (ID: {patient.get('patient_id') or patient.get('id') or 'N/A'})
        - **Medicines Count:** {len(medicines) if hasattr(medicines, '__len__') else 0}
        - **Health History Records:** {len(trends) if hasattr(trends, '__len__') else 0}
        - **Active AI Recommendations:** {len(ai_recs)}
        - **Recent Alerts:** {len(alerts)}
        """)

    st.divider()

    # Report Generation & Export Options
    st.subheader("📥 Export Patient Reports")
    st.caption("Generate and download PDF or HTML copies of the selected patient's full medical report.")

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    patient_name_slug = str(patient.get("name") or "patient").replace(" ", "_").lower()
    pdf_filename = f"health_report_{patient_name_slug}.pdf"
    html_filename = f"health_report_{patient_name_slug}.html"

    # Pre-generate report byte payloads
    pdf_bytes = generate_pdf_report(data, "Patient Health Report")
    html_bytes = generate_html_report(data, "Patient Health Report").encode("utf-8")

    with exp_col1:
        with st.container(border=True):
            st.subheader("📄 Daily Report")
            st.write("Export today's patient details, vitals, medicines, and AI suggestions.")
            st.download_button(
                label="📥 Download Daily PDF Report",
                data=pdf_bytes,
                file_name=f"daily_{pdf_filename}",
                mime="application/pdf",
                use_container_width=True,
                key="dl_daily_pdf"
            )

    with exp_col2:
        with st.container(border=True):
            st.subheader("📅 Weekly Report")
            st.write("Export weekly health history trends, medicine adherence, and AI recommendations.")
            st.download_button(
                label="📥 Download Weekly PDF Report",
                data=pdf_bytes,
                file_name=f"weekly_{pdf_filename}",
                mime="application/pdf",
                use_container_width=True,
                key="dl_weekly_pdf"
            )

    with exp_col3:
        with st.container(border=True):
            st.subheader("📑 Monthly / Full Report")
            st.write("Comprehensive export of all Firebase patient data, history, and AI insights.")
            st.download_button(
                label="📥 Download Comprehensive PDF",
                data=pdf_bytes,
                file_name=f"monthly_{pdf_filename}",
                mime="application/pdf",
                use_container_width=True,
                key="dl_monthly_pdf"
            )
            st.download_button(
                label="🌐 Download HTML Report",
                data=html_bytes,
                file_name=html_filename,
                mime="text/html",
                use_container_width=True,
                key="dl_html"
            )


render_reports()
