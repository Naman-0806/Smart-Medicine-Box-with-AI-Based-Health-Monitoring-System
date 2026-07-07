import streamlit as st

PAGES = [
    "Dashboard",
    "Patient",
    "Medicines",
    "Health Monitoring",
    "AI Insights",
    "Reports",
    "Settings",
]


def render_sidebar():
    st.sidebar.title("Navigation")
    st.sidebar.markdown("\n".join([f"- {p}" for p in PAGES]))
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box")
