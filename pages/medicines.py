import pandas as pd
import streamlit as st
from components.tables import medicine_table
from firebase.auth_service import require_auth
from firebase.firebase_service import delete_patient_medicine, get_medicine_schedule, get_patient_by_id, save_patient_medicine
from src.ui import apply_theme_styles


def _get_medicine_frame(patient_id=None):
    df = get_medicine_schedule(patient_id)
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=["id", "Medicine", "Dosage", "Time", "Status"])
    for column in ["id", "Medicine", "Dosage", "Time", "Status"]:
        if column not in df.columns:
            df[column] = ""
    df = df[["id", "Medicine", "Dosage", "Time", "Status"]].copy()
    df = df.fillna("")
    return df.reset_index(drop=True)


def _get_status_options(medicine_df):
    statuses = sorted({str(value).strip() for value in medicine_df["Status"].dropna() if str(value).strip()})
    return ["All"] + statuses


def render_medicines():
    require_auth()
    apply_theme_styles()

    st.markdown("# 💊 Medicine Management")
    st.caption("Manage medication schedules stored in Firebase under `users/{userId}/medicines`.")
    st.divider()

    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    selected_patient_id = user_uid
    st.session_state["selected_patient_id"] = user_uid
    st.session_state["owner_uid"] = user_uid
    st.session_state["user_uid"] = user_uid

    patient = get_patient_by_id(user_uid)
    if not patient:
        st.warning("📝 No patient profile registered yet. Please register your patient profile first.")
        if st.button("📝 Register Patient Profile", type="primary", use_container_width=True):
            st.switch_page("pages/patient.py")
        return

    st.caption(f"Patient Profile: **{patient.get('name') or patient.get('full_name')}** (ID: `{user_uid}`)")

    st.session_state["medicine_df"] = _get_medicine_frame(user_uid)
    st.session_state["medicine_patient_id"] = user_uid

    if "medicine_edit_index" not in st.session_state:
        st.session_state["medicine_edit_index"] = None

    medicine_df = st.session_state["medicine_df"].copy()

    with st.container(border=True):
        st.subheader("➕ Add New Medication")
        with st.form("add_medicine_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                medicine_name = st.text_input("Medicine Name *")
            with c2:
                dosage = st.text_input("Dosage", placeholder="e.g. 500mg")
            with c3:
                time_value = st.text_input("Time", placeholder="e.g. 08:00 AM")
            with c4:
                status_value = st.selectbox("Status", ["Taken", "Missed", "Upcoming"], index=2)
            submitted = st.form_submit_button("Add Medicine", type="primary")
            if submitted:
                if not medicine_name.strip():
                    st.error("Medicine Name cannot be empty.")
                else:
                    try:
                        med_payload = {
                            "Medicine": medicine_name.strip(),
                            "Dosage": dosage.strip(),
                            "Time": time_value.strip(),
                            "Status": status_value,
                        }
                        with st.spinner("Saving medication to Cloud Firestore..."):
                            save_patient_medicine(selected_patient_id, med_payload)
                            st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                        st.success(f"Medicine '{medicine_name}' saved directly to Firebase!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to save medicine: {str(ex)}")

    edit_index = st.session_state.get("medicine_edit_index")
    if edit_index is not None and edit_index < len(medicine_df):
        row = medicine_df.loc[edit_index]
        with st.container(border=True):
            st.subheader("✏️ Edit Medication")
            with st.form("edit_medicine_form", clear_on_submit=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    edited_name = st.text_input("Edit Medicine Name", value=row["Medicine"])
                with c2:
                    edited_dosage = st.text_input("Edit Dosage", value=row["Dosage"])
                with c3:
                    edited_time = st.text_input("Edit Time", value=row["Time"])
                with c4:
                    status_options = ["Taken", "Missed", "Upcoming"]
                    status_index = status_options.index(row["Status"]) if row["Status"] in status_options else 2
                    edited_status = st.selectbox("Edit Status", status_options, index=status_index)
                save_clicked = st.form_submit_button("Save Changes to Firebase")
                cancel_clicked = st.form_submit_button("Cancel")
                if save_clicked:
                    if not edited_name.strip():
                        st.error("Medicine Name cannot be empty.")
                    else:
                        try:
                            med_payload = {
                                "Medicine": edited_name.strip(),
                                "Dosage": edited_dosage.strip(),
                                "Time": edited_time.strip(),
                                "Status": edited_status,
                            }
                            med_id = str(row.get("id")) if row.get("id") else None
                            with st.spinner("Updating medication in Cloud Firestore..."):
                                save_patient_medicine(selected_patient_id, med_payload, medicine_id=med_id)
                                st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                                st.session_state["medicine_edit_index"] = None
                            st.success("Medication updated in Firebase.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Failed to update medicine: {str(ex)}")
                elif cancel_clicked:
                    st.session_state["medicine_edit_index"] = None
                    st.rerun()

    st.divider()
    with st.container(border=True):
        st.subheader("🔍 Medicine Schedule & Search")
        c1, c2 = st.columns(2)
        with c1:
            search_query = st.text_input("Search medicines", placeholder="Filter by medicine name")
        with c2:
            status_filter = st.selectbox("Filter by status", _get_status_options(medicine_df), index=0)

        view_df = medicine_df.copy()
        if search_query:
            view_df = view_df[view_df["Medicine"].str.lower().str.contains(search_query.lower(), na=False)]
        if status_filter != "All":
            view_df = view_df[view_df["Status"] == status_filter]

        medicine_table(view_df.reset_index(drop=True))

    st.divider()
    with st.container(border=True):
        st.subheader("⚙️ Quick Management")
        if view_df.empty:
            st.info("No medicines found for this patient.")
        else:
            for index, row in view_df.iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                with c1:
                    st.write(f"**{row['Medicine']}** — {row['Dosage']}")
                with c2:
                    st.write(f"🕒 {row['Time']} | Status: `{row['Status']}`")
                with c3:
                    if st.button("Edit", key=f"edit_med_{index}"):
                        st.session_state["medicine_edit_index"] = int(index)
                        st.rerun()
                with c4:
                    if st.button("Delete", key=f"del_med_{index}"):
                        try:
                            med_id = str(row.get("id")) if row.get("id") else None
                            if med_id:
                                with st.spinner("Deleting medication from Cloud Firestore..."):
                                    delete_patient_medicine(selected_patient_id, med_id)
                            st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                            st.session_state["medicine_edit_index"] = None
                            st.success("Medicine deleted from Firebase.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Failed to delete medicine: {str(ex)}")


render_medicines()
