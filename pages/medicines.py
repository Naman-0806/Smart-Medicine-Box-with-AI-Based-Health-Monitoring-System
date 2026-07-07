import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar
from components.tables import medicine_table


def render_medicines():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# Medicines")
    st.subheader("Medicine Schedule")
    medicine_table(data['medicines'])

    st.markdown("---")
    st.subheader("Today's Medicines")
    st.markdown("(Placeholder for today's medicines — dummy data used)")

    st.markdown("---")
    st.subheader("Medicine History")
    st.markdown("(Placeholder for medicine history — dummy data)")


render_medicines()
