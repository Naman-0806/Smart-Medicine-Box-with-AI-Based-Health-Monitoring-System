import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.tables import medicine_table


def _get_medicine_frame():
    base_data = get_all_dummy_data()
    medicine_df = base_data["medicines"].copy()
    for column in ["Medicine", "Dosage", "Time", "Status"]:
        if column not in medicine_df.columns:
            medicine_df[column] = ""
    medicine_df = medicine_df[["Medicine", "Dosage", "Time", "Status"]].copy()
    medicine_df = medicine_df.fillna("")
    return medicine_df.reset_index(drop=True)


def _get_status_options(medicine_df):
    statuses = sorted({str(value).strip() for value in medicine_df["Status"].dropna() if str(value).strip()})
    return ["All"] + statuses


def render_medicines():
    render_sidebar()

    st.markdown("# Medicines")
    st.subheader("Medicine Schedule")

    if "medicine_df" not in st.session_state:
        st.session_state["medicine_df"] = _get_medicine_frame()
    if "medicine_edit_index" not in st.session_state:
        st.session_state["medicine_edit_index"] = None

    medicine_df = st.session_state["medicine_df"].copy()

    with st.form("add_medicine_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            medicine_name = st.text_input("Medicine Name")
        with col2:
            dosage = st.text_input("Dosage")
        with col3:
            time_value = st.text_input("Time")
        with col4:
            status_value = st.selectbox("Status", ["Taken", "Missed", "Upcoming"], index=2)
        submitted = st.form_submit_button("Add Medicine")
        if submitted and medicine_name.strip():
            medicine_df.loc[len(medicine_df)] = {
                "Medicine": medicine_name.strip(),
                "Dosage": dosage.strip(),
                "Time": time_value.strip(),
                "Status": status_value,
            }
            st.session_state["medicine_df"] = medicine_df.reset_index(drop=True)
            st.success("Medicine added.")

    edit_index = st.session_state.get("medicine_edit_index")
    if edit_index is not None and edit_index < len(medicine_df):
        row = medicine_df.loc[edit_index]
        with st.form("edit_medicine_form", clear_on_submit=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                edited_name = st.text_input("Edit Medicine Name", value=row["Medicine"])
            with col2:
                edited_dosage = st.text_input("Edit Dosage", value=row["Dosage"])
            with col3:
                edited_time = st.text_input("Edit Time", value=row["Time"])
            with col4:
                status_options = ["Taken", "Missed", "Upcoming"]
                status_index = status_options.index(row["Status"]) if row["Status"] in status_options else 2
                edited_status = st.selectbox("Edit Status", status_options, index=status_index)
            save_clicked = st.form_submit_button("Save Changes")
            cancel_clicked = st.form_submit_button("Cancel")
            if save_clicked and edited_name.strip():
                medicine_df.loc[edit_index] = {
                    "Medicine": edited_name.strip(),
                    "Dosage": edited_dosage.strip(),
                    "Time": edited_time.strip(),
                    "Status": edited_status,
                }
                st.session_state["medicine_df"] = medicine_df.reset_index(drop=True)
                st.session_state["medicine_edit_index"] = None
                st.success("Medicine updated.")
            elif cancel_clicked:
                st.session_state["medicine_edit_index"] = None

    st.markdown("---")
    st.subheader("Search and Filter")
    search_query = st.text_input("Search medicines", placeholder="Search by medicine name")
    status_filter = st.selectbox("Filter by status", _get_status_options(medicine_df), index=0)

    view_df = medicine_df.copy()
    if search_query:
        view_df = view_df[view_df["Medicine"].str.lower().str.contains(search_query.lower(), na=False)]
    if status_filter != "All":
        view_df = view_df[view_df["Status"] == status_filter]

    medicine_table(view_df.reset_index(drop=True))

    st.markdown("---")
    st.subheader("Quick Actions")
    if view_df.empty:
        st.info("No medicines match the current filters.")
    else:
        for index, row in view_df.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.write(f"{row['Medicine']} — {row['Dosage']}")
            with col2:
                st.write(f"{row['Time']} • {row['Status']}")
            with col3:
                if st.button("Edit", key=f"edit_row_{index}"):
                    st.session_state["medicine_edit_index"] = int(index)
            with col4:
                if st.button("Delete", key=f"delete_row_{index}"):
                    medicine_df = medicine_df.drop(index=int(index)).reset_index(drop=True)
                    st.session_state["medicine_df"] = medicine_df
                    st.session_state["medicine_edit_index"] = None
                    st.success("Medicine removed.")
                    st.rerun()

    st.markdown("---")
    st.subheader("Today's Medicines")
    st.write("The medicine list above now supports add, edit, delete, search, and filter actions.")


render_medicines()
