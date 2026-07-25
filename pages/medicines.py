import pandas as pd
import streamlit as st
from firebase.firebase_service import delete_patient_medicine, get_medicine_schedule, save_patient_medicine
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.tables import medicine_table
from src.ui import apply_theme_styles


def _get_medicine_frame(patient_id=None):
    df = get_medicine_schedule(patient_id)
    if not isinstance(df, pd.DataFrame):
        base_data = get_all_dummy_data()
        df = base_data["medicines"].copy()
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
    render_sidebar()

    st.markdown("# Medicines")
    st.caption("Manage the patient's medication schedule.")
    st.divider()

    selected_patient_id = st.session_state.get("selected_patient_id")
    if selected_patient_id:
        st.caption(f"Connected to patient: **{selected_patient_id}**")
    else:
        st.info("No patient selected. Changes will apply locally until a patient is selected.")

    if (
        "medicine_df" not in st.session_state
        or st.session_state.get("medicine_patient_id") != selected_patient_id
    ):
        st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
        st.session_state["medicine_patient_id"] = selected_patient_id

    if "medicine_edit_index" not in st.session_state:
        st.session_state["medicine_edit_index"] = None

    medicine_df = st.session_state["medicine_df"].copy()

    with st.container(border=True):
        st.subheader("Medicine Schedule")
        with st.form("add_medicine_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                medicine_name = st.text_input("Medicine Name")
            with c2:
                dosage = st.text_input("Dosage")
            with c3:
                time_value = st.text_input("Time")
            with c4:
                status_value = st.selectbox("Status", ["Taken", "Missed", "Upcoming"], index=2)
            submitted = st.form_submit_button("Add Medicine")
            if submitted and medicine_name.strip():
                med_payload = {
                    "Medicine": medicine_name.strip(),
                    "Dosage": dosage.strip(),
                    "Time": time_value.strip(),
                    "Status": status_value,
                }
                if selected_patient_id:
                    save_patient_medicine(selected_patient_id, med_payload)
                    st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                else:
                    medicine_df.loc[len(medicine_df)] = med_payload
                    st.session_state["medicine_df"] = medicine_df.reset_index(drop=True)
                st.success("Medicine added.")
                st.rerun()

    edit_index = st.session_state.get("medicine_edit_index")
    if edit_index is not None and edit_index < len(medicine_df):
        row = medicine_df.loc[edit_index]
        with st.container(border=True):
            st.subheader("Edit Medication")
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
                save_clicked = st.form_submit_button("Save Changes")
                cancel_clicked = st.form_submit_button("Cancel")
                if save_clicked and edited_name.strip():
                    med_payload = {
                        "Medicine": edited_name.strip(),
                        "Dosage": edited_dosage.strip(),
                        "Time": edited_time.strip(),
                        "Status": edited_status,
                    }
                    med_id = str(row.get("id")) if row.get("id") else None
                    if selected_patient_id and med_id:
                        save_patient_medicine(selected_patient_id, med_payload, medicine_id=med_id)
                        st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                    else:
                        medicine_df.loc[edit_index] = {
                            "id": med_id or "",
                            **med_payload,
                        }
                        st.session_state["medicine_df"] = medicine_df.reset_index(drop=True)
                    st.session_state["medicine_edit_index"] = None
                    st.success("Medicine updated.")
                    st.rerun()
                elif cancel_clicked:
                    st.session_state["medicine_edit_index"] = None
                    st.rerun()

    st.divider()
    with st.container(border=True):
        st.subheader("Search and Filter")
        c1, c2 = st.columns(2)
        with c1:
            search_query = st.text_input("Search medicines", placeholder="Search by medicine name")
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
        st.subheader("Quick Actions")
        if view_df.empty:
            st.info("No medicines match the current filters.")
        else:
            for index, row in view_df.iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                with c1:
                    st.write(f"{row['Medicine']} — {row['Dosage']}")
                with c2:
                    st.write(f"{row['Time']} • {row['Status']}")
                with c3:
                    if st.button("Edit", key=f"edit_row_{index}"):
                        st.session_state["medicine_edit_index"] = int(index)
                        st.rerun()
                with c4:
                    if st.button("Delete", key=f"delete_row_{index}"):
                        med_id = str(row.get("id")) if row.get("id") else None
                        if selected_patient_id and med_id:
                            delete_patient_medicine(selected_patient_id, med_id)
                            st.session_state["medicine_df"] = _get_medicine_frame(selected_patient_id)
                        else:
                            medicine_df = medicine_df.drop(index=int(index)).reset_index(drop=True)
                            st.session_state["medicine_df"] = medicine_df
                        st.session_state["medicine_edit_index"] = None
                        st.success("Medicine removed.")
                        st.rerun()

    st.divider()
    st.subheader("Today's Medicines")
    st.write("The medicine list above now supports add, edit, delete, search, and filter actions.")


render_medicines()
