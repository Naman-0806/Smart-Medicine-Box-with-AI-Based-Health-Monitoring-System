import streamlit as st
from src.ui import apply_theme_styles

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
    apply_theme_styles()
    st.sidebar.title("Navigation")
    st.sidebar.markdown("\n".join([f"- {p}" for p in PAGES]))
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box")
