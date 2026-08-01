import pandas as pd
import streamlit as st
from firebase.auth_service import require_auth
from firebase.firebase_service import (
    check_duplicate_patient,
    delete_patient,
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


def _render_my_profile_view_and_update(patient_id, owner_uid):
    patient_data = get_patient_by_id(patient_id, owner_uid=owner_uid)
    if not patient_data:
        st.error("Patient profile details could not be retrieved from Cloud Firestore.")
        return

    # Render post-registration success banner if present
    if "reg_success_info" in st.session_state:
        info = st.session_state.pop("reg_success_info")
        st.success(
            f"{info.get('msg', '🎉 Registration Successful!')} | "
            f"**Patient ID:** `{info.get('patient_id')}` | "
            f"**Registration Date:** `{info.get('created_at')}`"
        )

    st.markdown("## 👤 My Profile")

    is_editing = st.session_state.get("editing_patient_profile", False)

    if not is_editing:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personal & Health Details</div>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        created_date = str(patient_data.get('created_at', '')).split("T")[0] or "-"
        with col_a:
            st.markdown(f"**Patient ID:** `{patient_data.get('patient_id', patient_id)}`")
            st.markdown(f"**Registration Date:** `{created_date}`")
            st.markdown(f"**Full Name:** {patient_data.get('name') or patient_data.get('full_name') or '-'}")
            st.markdown(f"**Age:** {patient_data.get('age', '-')}")
            st.markdown(f"**Gender:** {patient_data.get('gender', '-')}")
            st.markdown(f"**Height:** {patient_data.get('height', '-')} cm")
            st.markdown(f"**Weight:** {patient_data.get('weight', '-')} kg")
        with col_b:
            st.markdown(f"**Blood Group:** {patient_data.get('blood_group', '-')}")
            st.markdown(f"**Phone:** {patient_data.get('phone_number', '-')}")
            st.markdown(f"**Email:** {patient_data.get('email', '-')}")
            st.markdown(f"**Emergency Contact:** {patient_data.get('emergency_name', '-')} ({patient_data.get('emergency_phone', '-')})")
            st.markdown(f"**Doctor:** {patient_data.get('doctor_name', '-')}")
            st.markdown(f"**Hospital:** {patient_data.get('hospital_name', '-')}")
        with col_c:
            st.markdown(f"**Disease/Condition:** {patient_data.get('disease') or patient_data.get('existing_diseases') or '-'}")
            st.markdown(f"**Allergies:** {patient_data.get('allergies', '-')}")
            st.markdown(f"**Current Medications:** {patient_data.get('current_medications', '-')}")
            st.markdown(f"**Medicine Box ID:** {patient_data.get('medicine_box_id', '-')}")
            st.markdown(f"**Device Serial:** {patient_data.get('device_serial_number', '-')}")
            st.markdown(f"**Device Status:** {patient_data.get('device_status', 'Connected')}")
        st.markdown("</div>", unsafe_allow_html=True)

        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if st.button("✏️ Edit Profile", use_container_width=True, type="primary"):
                st.session_state["editing_patient_profile"] = True
                st.rerun()
        with col_act2:
            if st.button("🗑️ Reset Record", use_container_width=True):
                st.session_state["confirm_delete_patient"] = True

        if st.session_state.get("confirm_delete_patient"):
            p_name = patient_data.get('name') or patient_data.get('full_name') or 'Profile'
            st.warning(f"⚠️ Are you sure you want to delete profile for **{p_name}** (`{patient_id}`)?")
            c_del1, c_del2 = st.columns(2)
            with c_del1:
                if st.button("Confirm Delete Profile", key="btn_confirm_del", type="primary"):
                    success, res_msg = delete_patient(patient_id, owner_uid=owner_uid)
                    if success:
                        st.success(res_msg)
                        st.session_state.pop("selected_patient_id", None)
                        st.session_state.pop("confirm_delete_patient", None)
                        st.rerun()
                    else:
                        st.error(res_msg)
            with c_del2:
                if st.button("Cancel", key="btn_cancel_del"):
                    st.session_state.pop("confirm_delete_patient", None)
                    st.rerun()

    else:
        # Edit Form with pre-filled fields
        st.subheader("✏️ Edit Patient Profile")
        with st.form("edit_patient_profile_form"):
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Personal Information</div>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                e_name = st.text_input("Full Name *", value=patient_data.get("name") or patient_data.get("full_name") or "")
                e_age = st.number_input("Age", min_value=0, max_value=120, value=int(patient_data.get("age") or 0))
                gender_opts = ["Male", "Female", "Other"]
                curr_gender = patient_data.get("gender") if patient_data.get("gender") in gender_opts else "Other"
                e_gender = st.selectbox("Gender", gender_opts, index=gender_opts.index(curr_gender))
            with col2:
                e_blood = st.text_input("Blood Group", value=patient_data.get("blood_group") or "A+")
                e_height = st.number_input("Height (cm)", min_value=0, max_value=250, value=int(patient_data.get("height") or 170))
                e_weight = st.number_input("Weight (kg)", min_value=0, max_value=300, value=int(patient_data.get("weight") or 70))
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Contact Information</div>", unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                e_phone = st.text_input("Phone Number", value=patient_data.get("phone_number") or "")
                e_email = st.text_input("Email Address", value=patient_data.get("email") or "")
            with col4:
                e_em_name = st.text_input("Emergency Contact Name", value=patient_data.get("emergency_name") or "")
                e_em_phone = st.text_input("Emergency Contact Phone", value=patient_data.get("emergency_phone") or "")
            e_address = st.text_area("Address", value=patient_data.get("address") or "", height=80)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Medical & Device Information</div>", unsafe_allow_html=True)
            col5, col6 = st.columns(2)
            with col5:
                e_disease = st.text_area("Existing Diseases / Conditions", value=patient_data.get("disease") or patient_data.get("existing_diseases") or "", height=80)
                e_allergies = st.text_area("Allergies", value=patient_data.get("allergies") or "", height=80)
                e_meds = st.text_area("Current Medications", value=patient_data.get("current_medications") or "", height=80)
            with col6:
                e_doctor = st.text_input("Doctor Name", value=patient_data.get("doctor_name") or "")
                e_hospital = st.text_input("Hospital Name", value=patient_data.get("hospital_name") or "")
                e_box_id = st.text_input("Medicine Box ID", value=patient_data.get("medicine_box_id") or "")
                e_dev_serial = st.text_input("Device Serial Number", value=patient_data.get("device_serial_number") or "")
            st.markdown("</div>", unsafe_allow_html=True)

            btn_save = st.form_submit_button("Save Changes to Firebase", type="primary")
            btn_cancel = st.form_submit_button("Cancel Editing")

            if btn_save:
                upd_payload = {
                    "name": e_name.strip(),
                    "full_name": e_name.strip(),
                    "age": e_age,
                    "gender": e_gender,
                    "blood_group": e_blood.strip(),
                    "height": e_height,
                    "weight": e_weight,
                    "phone_number": e_phone.strip(),
                    "email": e_email.strip(),
                    "address": e_address.strip(),
                    "emergency_name": e_em_name.strip(),
                    "emergency_phone": e_em_phone.strip(),
                    "existing_diseases": e_disease.strip(),
                    "allergies": e_allergies.strip(),
                    "current_medications": e_meds.strip(),
                    "doctor_name": e_doctor.strip(),
                    "hospital_name": e_hospital.strip(),
                    "medicine_box_id": e_box_id.strip(),
                    "device_serial_number": e_dev_serial.strip(),
                }
                valid, msg = validate_patient_input(upd_payload)
                if not valid:
                    st.error(msg)
                else:
                    is_dup, dup_msg = check_duplicate_patient(owner_uid, e_phone.strip(), e_email.strip(), e_name.strip(), exclude_patient_id=patient_id)
                    if is_dup:
                        st.error(dup_msg)
                    else:
                        success, res_msg = update_patient_registration(patient_id, upd_payload, owner_uid=owner_uid)
                        if success:
                            st.success(res_msg)
                            st.session_state["editing_patient_profile"] = False
                            st.rerun()
                        else:
                            st.error(res_msg)

            if btn_cancel:
                st.session_state["editing_patient_profile"] = False
                st.rerun()


def _render_registration_form(owner_uid):
    st.markdown("## ➕ Register Patient Profile")
    st.caption("Fill out patient information to save your profile in Firebase.")

    existing_profile = get_patient_by_id(owner_uid) or {}
    auth_user = st.session_state.get("auth_user") or {}

    def_name = existing_profile.get("name") or existing_profile.get("full_name") or auth_user.get("full_name") or ""
    def_email = existing_profile.get("email") or auth_user.get("email") or ""
    def_phone = existing_profile.get("phone_number") or auth_user.get("phone_number") or ""

    with st.form("new_patient_registration_form"):
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personal Information</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            r_name = st.text_input("Full Name *", key="reg_full_name", value=def_name)
            r_age = st.number_input("Age", min_value=0, max_value=120, value=int(existing_profile.get("age") or 30), step=1, key="reg_age")
            gender_opts = ["Male", "Female", "Other"]
            curr_g = existing_profile.get("gender") if existing_profile.get("gender") in gender_opts else "Male"
            r_gender = st.selectbox("Gender", gender_opts, index=gender_opts.index(curr_g), key="reg_gender")
            r_dob = st.date_input("Date of Birth", key="reg_dob")
        with col2:
            blood_opts = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            curr_b = existing_profile.get("blood_group") if existing_profile.get("blood_group") in blood_opts else "A+"
            r_blood = st.selectbox("Blood Group", blood_opts, index=blood_opts.index(curr_b), key="reg_blood_group")
            r_height = st.number_input("Height (cm)", min_value=0, max_value=250, value=int(existing_profile.get("height") or 170), step=1, key="reg_height")
            r_weight = st.number_input("Weight (kg)", min_value=0, max_value=300, value=int(existing_profile.get("weight") or 70), step=1, key="reg_weight")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Contact Information</div>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            r_phone = st.text_input("Phone Number", key="reg_phone_number", value=def_phone, placeholder="+1234567890")
            r_email = st.text_input("Email Address", key="reg_email", value=def_email, placeholder="patient@example.com")
        with col4:
            r_em_name = st.text_input("Emergency Contact Name", key="reg_emergency_name", value=existing_profile.get("emergency_name") or "")
            r_em_phone = st.text_input("Emergency Contact Number", key="reg_emergency_phone", value=existing_profile.get("emergency_phone") or "")
        r_address = st.text_area("Address", key="reg_address", value=existing_profile.get("address") or "", height=80)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Medical Information</div>", unsafe_allow_html=True)
        col5, col6 = st.columns(2)
        with col5:
            r_disease = st.text_area("Existing Diseases / Conditions", key="reg_existing_diseases", value=existing_profile.get("disease") or existing_profile.get("existing_diseases") or "", height=80)
            r_allergies = st.text_area("Allergies", key="reg_allergies", value=existing_profile.get("allergies") or "", height=80)
        with col6:
            r_meds = st.text_area("Current Medications", key="reg_current_medications", value=existing_profile.get("current_medications") or "", height=80)
            r_doctor = st.text_input("Doctor Name", key="reg_doctor_name", value=existing_profile.get("doctor_name") or "Dr. Smith")
            r_hospital = st.text_input("Hospital Name", key="reg_hospital_name", value=existing_profile.get("hospital_name") or "")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Device Information</div>", unsafe_allow_html=True)
        col7, col8 = st.columns(2)
        with col7:
            r_box_id = st.text_input("Medicine Box ID", key="reg_medicine_box_id", value=existing_profile.get("medicine_box_id") or "")
        with col8:
            r_dev_serial = st.text_input("Device Serial Number", key="reg_device_serial_number", value=existing_profile.get("device_serial_number") or "")
        st.markdown("</div>", unsafe_allow_html=True)

        c_sub, c_clr = st.columns([1, 1])
        with c_sub:
            submitted = st.form_submit_button("Save Profile", type="primary")
        with c_clr:
            cleared = st.form_submit_button("Clear Form")

        if submitted:
            payload = {
                "name": r_name.strip(),
                "full_name": r_name.strip(),
                "age": r_age,
                "gender": r_gender,
                "dob": str(r_dob) if r_dob else "",
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
                "ownerUid": owner_uid,
            }

            valid, err_msg = validate_patient_input(payload)
            if not valid:
                st.error(err_msg)
            else:
                is_dup, dup_msg = check_duplicate_patient(owner_uid, r_phone, r_email, r_name, exclude_patient_id=owner_uid)
                if is_dup:
                    st.error(dup_msg)
                else:
                    success, res_msg = save_patient_registration(payload, owner_uid=owner_uid)
                    if success:
                        st.session_state["selected_patient_id"] = owner_uid
                        st.session_state["owner_uid"] = owner_uid
                        st.session_state["user_uid"] = owner_uid
                        _clear_form()
                        st.success(res_msg)
                        st.switch_page("pages/dashboard.py")
                    else:
                        st.error(res_msg)

        if cleared:
            _clear_form()
            st.rerun()


def render_patient():
    require_auth()
    _apply_styles()

    st.markdown("# 🩺 Patient Management")

    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    if not owner_uid:
        st.error("Authentication required. Please log in.")
        return

    # Check if users/{current_uid}/patient/profile exists in Firestore automatically on page open
    user_profile = get_patient_by_id(owner_uid, owner_uid=owner_uid, force_refresh=True)

    if user_profile:
        st.session_state["selected_patient_id"] = owner_uid
        _render_my_profile_view_and_update(owner_uid, owner_uid=owner_uid)
    else:
        _render_registration_form(owner_uid=owner_uid)


render_patient()
