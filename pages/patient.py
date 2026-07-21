import streamlit as st
from components.sidebar import render_sidebar
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
    st.session_state["patient_registration_data"] = {
        key: st.session_state.get(key) for key in field_keys
    }
    st.session_state["registration_complete"] = True
    st.session_state["edit_profile"] = False


def _render_profile_view():
    patient_data = st.session_state.get("patient_registration_data", {})

    st.markdown("# Patient Profile")
    st.caption("Your profile is already stored in session state.")

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Profile Summary</div>", unsafe_allow_html=True)
    st.markdown(f"**Full Name:** {patient_data.get('full_name', '-')}" )
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
    st.caption("First-time patient onboarding form. No data is saved or connected to Firebase.")

    with st.form("patient_registration_form"):
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Personal Information</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name", key="full_name")
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
            st.text_area("Existing Diseases", key="existing_diseases", height=100)
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
            _store_registration_data()
            st.success("Registration completed successfully. Your information is stored in session state.")
        if cleared:
            _clear_form()
            st.rerun()


def render_patient():
    render_sidebar()
    _apply_styles()

    if st.session_state.get("patient_registration_data") and not st.session_state.get("edit_profile"):
        _render_profile_view()
    else:
        _render_registration_form()


render_patient()
