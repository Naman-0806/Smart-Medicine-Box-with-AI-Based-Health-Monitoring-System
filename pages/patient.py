import pandas as pd
import streamlit as st
from components.sidebar import render_sidebar
from firebase.firebase_service import (
    check_duplicate_patient,
    delete_patient,
    get_all_patients,
    get_patient_by_id,
    save_patient_registration,
    update_patient_registration,
    validate_patient_input,
)
from src.ui import apply_theme_styles


def _apply_styles():
    apply_theme_styles()


def _clear_form():
    for key in [
        "reg_full_name",
        "reg_age",
        "reg_gender",
        "reg_dob",
        "reg_blood_group",
        "reg_height",
        "reg_weight",
        "reg_phone_number",
        "reg_email",
        "reg_address",
        "reg_emergency_name",
        "reg_emergency_phone",
        "reg_existing_diseases",
        "reg_allergies",
        "reg_current_medications",
        "reg_doctor_name",
        "reg_hospital_name",
        "reg_medicine_box_id",
        "reg_device_serial_number",
    ]:
        st.session_state.pop(key, None)


def _render_patient_list(owner_uid):
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>📋 Your Registered Patients</div>", unsafe_allow_html=True)

    patients = get_all_patients(owner_uid=owner_uid) or []
    search_query = st.text_input("🔍 Search your patients", key="patient_search_query")

    filtered_patients = []
    if search_query:
        query = search_query.strip().lower()
        for patient in patients:
            searchable_text = " ".join(
                str(patient.get(key) or "") for key in ["patient_id", "name", "full_name", "age", "gender", "blood_group", "phone_number", "doctor_name"]
            ).lower()
            if query in searchable_text:
                filtered_patients.append(patient)
    else:
        filtered_patients = patients

    if filtered_patients:
        display_rows = []
        for p in filtered_patients:
            display_rows.append({
                "Patient ID": p.get("patient_id") or p.get("id") or "",
                "Name": p.get("name") or p.get("full_name") or "",
                "Age": p.get("age") or "",
                "Gender": p.get("gender") or "",
                "Blood Group": p.get("blood_group") or "",
                "Phone Number": p.get("phone_number") or "",
                "Doctor Name": p.get("doctor_name") or "",
            })

        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

        patient_ids = [p.get("patient_id") or p.get("id") or "" for p in filtered_patients]
        patient_labels = [
            f"{p.get('name') or p.get('full_name') or 'Unnamed'} ({p.get('patient_id') or p.get('id') or '-'})"
            for p in filtered_patients
        ]

        current_selected = st.session_state.get("selected_patient_id")
        def_idx = 0
        if current_selected in patient_ids:
            def_idx = patient_ids.index(current_selected)

        selected_id = st.selectbox(
            "Select Active Patient",
            options=patient_ids,
            index=def_idx,
            format_func=lambda pid: next((label for current_id, label in zip(patient_ids, patient_labels) if current_id == pid), pid),
            key="page_patient_selector_dropdown",
        )

        if st.session_state.get("selected_patient_id") != selected_id:
            st.session_state["selected_patient_id"] = selected_id
            st.rerun()

        st.caption(f"Active Patient ID: `{selected_id}`")
    else:
        st.info("No registered patients found for your account. Please register a patient below.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_profile_view_and_update(selected_patient_id, owner_uid):
    patient_data = get_patient_by_id(selected_patient_id, owner_uid=owner_uid)
    if not patient_data:
        st.error("Patient details could not be retrieved from Firebase.")
        return

    st.markdown("## 👤 Patient Profile Details & Management")

    is_editing = st.session_state.get("editing_patient_profile", False)

    if not is_editing:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Patient Overview</div>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Patient ID:** `{patient_data.get('patient_id', '-')}`")
            st.markdown(f"**Name:** {patient_data.get('name') or patient_data.get('full_name') or '-'}")
            st.markdown(f"**Age:** {patient_data.get('age', '-')}")
            st.markdown(f"**Gender:** {patient_data.get('gender', '-')}")
        with col_b:
            st.markdown(f"**Blood Group:** {patient_data.get('blood_group', '-')}")
            st.markdown(f"**Phone:** {patient_data.get('phone_number', '-')}")
            st.markdown(f"**Email:** {patient_data.get('email', '-')}")
            st.markdown(f"**Doctor:** {patient_data.get('doctor_name', '-')}")
        with col_c:
            st.markdown(f"**Disease/Condition:** {patient_data.get('disease') or patient_data.get('existing_diseases') or '-'}")
            st.markdown(f"**Device ID:** {patient_data.get('medicine_box_id', '-')}")
            st.markdown(f"**Device Serial:** {patient_data.get('device_serial_number', '-')}")
            st.markdown(f"**Status:** {patient_data.get('device_status', 'Connected')}")
        st.markdown("</div>", unsafe_allow_html=True)

        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("✏️ Edit Patient Profile", use_container_width=True):
                st.session_state["editing_patient_profile"] = True
                st.rerun()
        with col_act2:
            if st.button("🗑️ Delete Patient Record", type="primary", use_container_width=True):
                st.session_state["confirm_delete_patient"] = True

        if st.session_state.get("confirm_delete_patient"):
            st.warning(f"⚠️ Are you sure you want to permanently delete patient **{patient_data.get('name')}** (`{selected_patient_id}`)? This action immediately removes all medicine and health records from Firebase.")
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                if st.button("YES, Delete Patient", key="btn_confirm_del"):
                    if delete_patient(selected_patient_id, owner_uid=owner_uid):
                        st.success("Patient record deleted successfully from Firebase.")
                        st.session_state.pop("selected_patient_id", None)
                        st.session_state.pop("confirm_delete_patient", None)
                        st.rerun()
                    else:
                        st.error("Failed to delete patient from Firebase.")
            with c_del2:
                if st.button("Cancel", key="btn_cancel_del"):
                    st.session_state.pop("confirm_delete_patient", None)
                    st.rerun()

    else:
        # Edit Form
        st.subheader("✏️ Update Patient Profile")
        with st.form("edit_patient_profile_form"):
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                e_name = st.text_input("Name *", value=patient_data.get("name") or patient_data.get("full_name") or "")
                e_age = st.number_input("Age", min_value=0, max_value=120, value=int(patient_data.get("age") or 0))
                e_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(patient_data.get("gender")) if patient_data.get("gender") in ["Male", "Female", "Other"] else 2)
            with col2:
                e_blood = st.text_input("Blood Group", value=patient_data.get("blood_group") or "A+")
                e_phone = st.text_input("Phone Number", value=patient_data.get("phone_number") or "")
                e_email = st.text_input("Email Address", value=patient_data.get("email") or "")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                e_disease = st.text_area("Disease / Conditions", value=patient_data.get("disease") or patient_data.get("existing_diseases") or "", height=80)
                e_allergies = st.text_area("Allergies", value=patient_data.get("allergies") or "", height=80)
            with col4:
                e_meds = st.text_area("Current Medications", value=patient_data.get("current_medications") or "", height=80)
                e_doctor = st.text_input("Doctor Name", value=patient_data.get("doctor_name") or "")
            st.markdown("</div>", unsafe_allow_html=True)

            btn_save = st.form_submit_button("Save Changes to Firebase")
            btn_cancel = st.form_submit_button("Cancel Editing")

            if btn_save:
                upd_payload = {
                    "name": e_name.strip(),
                    "full_name": e_name.strip(),
                    "age": e_age,
                    "gender": e_gender,
                    "blood_group": e_blood.strip(),
                    "phone_number": e_phone.strip(),
                    "email": e_email.strip(),
                    "existing_diseases": e_disease.strip(),
                    "allergies": e_allergies.strip(),
                    "current_medications": e_meds.strip(),
                    "doctor_name": e_doctor.strip(),
                }
                valid, msg = validate_patient_input(upd_payload)
                if not valid:
                    st.error(msg)
                else:
                    if update_patient_registration(selected_patient_id, upd_payload, owner_uid=owner_uid):
                        st.success("Patient profile updated successfully in Firebase!")
                        st.session_state["editing_patient_profile"] = False
                        st.rerun()
                    else:
                        st.error("Failed to update patient profile in Firebase.")

            if btn_cancel:
                st.session_state["editing_patient_profile"] = False
                st.rerun()


def _render_registration_form(owner_uid):
    st.markdown("## ➕ Register New Patient")
    st.caption("Fill out patient information to save a new record under your Firebase account.")

    with st.form("new_patient_registration_form"):
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personal Information</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            r_name = st.text_input("Full Name *", key="reg_full_name")
            r_age = st.number_input("Age", min_value=0, max_value=120, value=30, step=1, key="reg_age")
            r_gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=0, key="reg_gender")
            r_dob = st.date_input("Date of Birth", key="reg_dob")
        with col2:
            r_blood = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], index=0, key="reg_blood_group")
            r_height = st.number_input("Height (cm)", min_value=0, max_value=250, value=170, step=1, key="reg_height")
            r_weight = st.number_input("Weight (kg)", min_value=0, max_value=300, value=70, step=1, key="reg_weight")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Contact Information</div>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            r_phone = st.text_input("Phone Number", key="reg_phone_number", placeholder="+1234567890")
            r_email = st.text_input("Email Address", key="reg_email", placeholder="patient@example.com")
        with col4:
            r_em_name = st.text_input("Emergency Contact Name", key="reg_emergency_name")
            r_em_phone = st.text_input("Emergency Contact Number", key="reg_emergency_phone")
        r_address = st.text_area("Address", key="reg_address", height=80)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Medical Information</div>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            r_disease = st.text_area("Existing Diseases / Conditions", key="reg_existing_diseases", height=80)
            r_allergies = st.text_area("Allergies", key="reg_allergies", height=80)
        with col6:
            r_meds = st.text_area("Current Medications", key="reg_current_medications", height=80)
            r_doctor = st.text_input("Doctor Name", key="reg_doctor_name", value="Dr. Smith")
            r_hospital = st.text_input("Hospital Name", key="reg_hospital_name")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Device Information</div>", unsafe_allow_html=True)
        col7, col8 = st.columns(2)
        with col7:
            r_box_id = st.text_input("Medicine Box ID", key="reg_medicine_box_id")
        with col8:
            r_dev_serial = st.text_input("Device Serial Number", key="reg_device_serial_number")
        st.markdown("</div>", unsafe_allow_html=True)

        c_sub, c_clr = st.columns([1, 1])
        with c_sub:
            submitted = st.form_submit_button("Register Patient", type="primary")
        with c_clr:
            cleared = st.form_submit_button("Clear Form")

        if submitted:
            payload = {
                "name": r_name.strip(),
                "full_name": r_name.strip(),
                "age": r_age,
                "gender": r_gender,
                "dob": r_dob,
                "blood_group": r_blood,
                "height": r_height,
                "weight": r_weight,
                "phone_number": r_phone.strip(),
                "email": r_email.strip(),
                "address": r_address.strip(),
                "emergency_name": r_em_name.strip(),
                "emergency_phone": r_em_phone.strip(),
                "existing_diseases": r_disease.strip(),
                "allergies": r_allergies.strip(),
                "current_medications": r_meds.strip(),
                "doctor_name": r_doctor.strip(),
                "hospital_name": r_hospital.strip(),
                "medicine_box_id": r_box_id.strip(),
                "device_serial_number": r_dev_serial.strip(),
                "owner_uid": owner_uid,
            }

            # 1. Validation
            valid, err_msg = validate_patient_input(payload)
            if not valid:
                st.error(err_msg)
            else:
                # 2. Check for Duplicate Patients
                is_dup, dup_msg = check_duplicate_patient(owner_uid, r_phone, r_email, r_name)
                if is_dup:
                    st.error(dup_msg)
                else:
                    new_pid = save_patient_registration(payload, owner_uid=owner_uid)
                    if new_pid:
                        st.success(f"Patient successfully registered in Firebase! (ID: {new_pid})")
                        st.session_state["selected_patient_id"] = new_pid
                        _clear_form()
                        st.rerun()
                    else:
                        st.error("Failed to save patient to Firebase. Please try again.")

        if cleared:
            _clear_form()
            st.rerun()


def render_patient():
    render_sidebar()
    _apply_styles()

    st.markdown("# 🩺 Patient Management")

    is_logged_in = st.session_state.get("is_logged_in", False)
    owner_uid = st.session_state.get("owner_uid")

    if not is_logged_in or not owner_uid:
        st.warning("⚠️ Please log in or sign up in the sidebar to view, register, or manage your patient records.")
        return

    _render_patient_list(owner_uid=owner_uid)

    selected_patient_id = st.session_state.get("selected_patient_id")
    if selected_patient_id:
        _render_profile_view_and_update(selected_patient_id, owner_uid=owner_uid)

    st.markdown("---")
    _render_registration_form(owner_uid=owner_uid)


render_patient()
