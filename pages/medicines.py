import streamlit as st
import pandas as pd
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.tables import medicine_table


def _get_medicine_rows() -> pd.DataFrame:
    data = get_all_dummy_data()
    return data["medicines"].copy()


def _render_summary_cards(df: pd.DataFrame) -> None:
    total = len(df)
    taken = int((df["Status"] == "Taken").sum())
    missed = int((df["Status"] == "Missed").sum())
    upcoming = int((df["Status"] == "Upcoming").sum())

    cols = st.columns(4)
    cols[0].metric("Total Medicines", total)
    cols[1].metric("Taken Today", taken)
    cols[2].metric("Missed Today", missed)
    cols[3].metric("Upcoming", upcoming)


def render_medicines() -> None:
    render_sidebar()
    st.markdown("# Medicines")
    st.markdown("### Medicine Management")

    df = _get_medicine_rows()
    if df.empty:
        st.info("No medicines available.")
        return

    _render_summary_cards(df)

    st.markdown("---")

    search_term = st.text_input("Search medicine", placeholder="Type medicine name")
    filter_choice = st.radio("Filter", ["All", "Taken", "Upcoming", "Missed"], horizontal=True)

    filtered_df = df.copy()
    if search_term:
        filtered_df = filtered_df[filtered_df["Medicine"].str.contains(search_term, case=False, na=False)]

    if filter_choice != "All":
        filtered_df = filtered_df[filtered_df["Status"] == filter_choice]

    action_col, _ = st.columns([1, 4])
    with action_col:
        st.button("Add Medicine")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("Edit")
    with col2:
        st.button("Delete")
    with col3:
        st.button("Refresh")

    st.markdown("---")
    st.subheader("Today's Medicines")
    medicine_table(filtered_df)


render_medicines()
