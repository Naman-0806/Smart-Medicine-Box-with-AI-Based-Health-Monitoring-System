import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar


def render_reports():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Reports")
    st.subheader("Daily Report Preview")
    st.markdown("(Dummy preview of daily report)")
    st.button("Export Daily Report")

    st.markdown("---")
    st.subheader("Weekly Report Preview")
    st.markdown("(Dummy preview of weekly report)")
    st.button("Export Weekly Report")

    st.markdown("---")
    st.subheader("Monthly Report Preview")
    st.markdown("(Dummy preview of monthly report)")
    st.button("Export Monthly Report")


render_reports()
