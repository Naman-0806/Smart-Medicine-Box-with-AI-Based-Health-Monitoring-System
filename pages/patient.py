import pandas as pd
import streamlit as st
from components.sidebar import render_sidebar
from firebase.firebase_service import get_all_patients, save_patient_registration
from src.ui import apply_theme_styles


def _apply_styles():
    apply_theme_styles()


def _clear_form():
    for key in [
        "full_name",
        "age",
        "gender",
        "dob",
        "blood_group",
        "height",
        "weight",
        "phone_number",
        "email",
        "address",
        "emergency_name",
        "emergency_phone",
        "existing_diseases",
        "allergies",
        "current_medications",
        "doctor_name",
        "hospital_name",
        "medicine_box_id",
        "device_serial_number",
    ]:
        st.session_state.pop(key, None)
    st.session_state.pop("patient_registration_data", None)
    st.session_state.pop("registration_complete", None)
    st.session_state.pop("edit_profile", None)


def _store_registration_data():
    field_keys = [
        "full_name",
        "age",
        "gender",
        "dob",
        "blood_group",
        "height",
        "weight",
        "phone_number",
        "email",
        "address",
        "emergency_name",
        "emergency_phone",
        "existing_diseases",
        "allergies",
        "current_medications",
        "doctor_name",
        "hospital_name",
        "medicine_box_id",
        "device_serial_number",
    ]
    patient_data = {key: st.session_state.get(key) for key in field_keys}
    payload = {
        "name": patient_data.get("full_name") or "",
        "age": patient_data.get("age"),
        "gender": patient_data.get("gender"),
        "blood_group": patient_data.get("blood_group"),
        "height": patient_data.get("height"),
        "weight": patient_data.get("weight"),
        "disease": patient_data.get("existing_diseases") or "",
        "doctor_name": patient_data.get("doctor_name"),
        "phone_number": patient_data.get("phone_number"),
    }

    patient_id = save_patient_registration(payload)
    if patient_id:
        patient_data["patient_id"] = patient_id
        st.session_state["patient_registration_data"] = patient_data
        st.session_state["registration_complete"] = True
        st.session_state["edit_profile"] = False
        return True

    st.session_state["patient_registration_data"] = patient_data
    st.session_state["registration_complete"] = True
    st.session_state["edit_profile"] = False
    return False


def _render_patient_list():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Patient List</div>", unsafe_allow_html=True)

    patients = get_all_patients() or []
    search_query = st.text_input("Search patients", key="patient_search_query")

    filtered_patients = []
    if search_query:
        query = search_query.strip().lower()
        for patient in patients:
            searchable_text = " ".join(
                str(patient.get(key) or "") for key in ["patient_id", "name", "age", "gender", "blood_group", "phone_number", "doctor_name"]
            ).lower()
            if query in searchable_text:
                filtered_patients.append(patient)
    else:
        filtered_patients = patients

    if filtered_patients:
        display_rows = []
        for patient in filtered_patients:
            display_rows.append({
                "Patient ID": patient.get("patient_id") or patient.get("id") or "",
                "Name": patient.get("name") or "",
                "Age": patient.get("age") or "",
                "Gender": patient.get("gender") or "",
                "Blood Group": patient.get("blood_group") or "",
                "Phone Number": patient.get("phone_number") or "",
                "Doctor Name": patient.get("doctor_name") or "",
            })

        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

        patient_ids = [patient.get("patient_id") or patient.get("id") or "" for patient in filtered_patients]
        patient_labels = [
            f"{patient.get('name') or '-'} ({patient.get('patient_id') or patient.get('id') or '-'})"
            for patient in filtered_patients
        ]

        selected_patient_id = st.selectbox(
            "Select a patient",
            options=patient_ids,
            format_func=lambda patient_id: next(
                label for current_id, label in zip(patient_ids, patient_labels) if current_id == patient_id
            ),
            key="selected_patient_id",
        )
        st.session_state["selected_patient_id"] = selected_patient_id
        st.caption(f"Selected patient ID: {selected_patient_id}")
    else:
        st.info("No patients found in Firebase.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_profile_view():
    patient_data = st.session_state.get("patient_registration_data", {})

    st.markdown("# Patient Profile")
    st.caption("Your profile is already stored in session state.")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Profile Summary</div>", unsafe_allow_html=True)
    st.markdown(f"**Patient ID:** {patient_data.get('patient_id', '-')}" )
    st.markdown(f"**Name:** {patient_data.get('full_name', '-')}" )
    st.markdown(f"**Age:** {patient_data.get('age', '-')}" )
    st.markdown(f"**Gender:** {patient_data.get('gender', '-')}" )
    st.markdown(f"**Phone Number:** {patient_data.get('phone_number', '-')}" )
    st.markdown(f"**Email:** {patient_data.get('email', '-')}" )
    st.markdown(f"**Blood Group:** {patient_data.get('blood_group', '-')}" )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Edit Profile"):
        st.session_state["edit_profile"] = True
        st.rerun()


def _render_registration_form():
    st.markdown("# Patient Registration")
    st.caption("Register a patient and save the profile to Firebase.")

    with st.form("patient_registration_form"):
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personal Information</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Name", key="full_name")
            st.number_input("Age", min_value=0, step=1, key="age")
            st.text_input("Gender", key="gender")
            st.date_input("Date of Birth", key="dob")
        with col2:
            st.text_input("Blood Group", key="blood_group")
            st.number_input("Height (cm)", min_value=0, step=1, key="height")
            st.number_input("Weight (kg)", min_value=0, step=1, key="weight")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Contact Information</div>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            st.text_input("Phone Number", key="phone_number")
            st.text_input("Email", key="email")
        with col4:
            st.text_input("Emergency Contact Name", key="emergency_name")
            st.text_input("Emergency Contact Number", key="emergency_phone")
        st.text_area("Address", key="address", height=120)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Medical Information</div>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            st.text_area("Disease", key="existing_diseases", height=100)
            st.text_area("Allergies", key="allergies", height=100)
        with col6:
            st.text_area("Current Medications", key="current_medications", height=100)
            st.text_input("Doctor Name", key="doctor_name")
            st.text_input("Hospital Name", key="hospital_name")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Device Information</div>", unsafe_allow_html=True)
        col7, col8 = st.columns(2)
        with col7:
            st.text_input("Medicine Box ID", key="medicine_box_id")
        with col8:
            st.text_input("Device Serial Number", key="device_serial_number")
        st.markdown("</div>", unsafe_allow_html=True)

        col_submit, col_clear = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("Register")
        with col_clear:
            cleared = st.form_submit_button("Clear")

        if submitted:
            saved = _store_registration_data()
            if saved:
                st.success("Registration completed successfully and saved to Firebase.")
            else:
                st.error("Registration could not be saved to Firebase. Your information is still available in session state.")
        if cleared:
            _clear_form()
            st.rerun()


def render_patient():
    render_sidebar()
    _apply_styles()

    st.session_state.setdefault("selected_patient_id", None)
    _render_patient_list()

    if st.session_state.get("patient_registration_data") and not st.session_state.get("edit_profile"):
        _render_profile_view()
    else:
        _render_registration_form()


render_patient()
