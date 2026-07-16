import streamlit as st
from components.sidebar import render_sidebar


st.set_page_config(page_title="Smart Medicine Box Dashboard", layout="wide")


def main():
    st.session_state.setdefault("current_page", "Home")
    render_sidebar()
    st.sidebar.radio("", ["Dashboard", "Patient", "Health Monitoring", "AI Insights", "Reports", "Settings"], key="current_page")

    st.markdown("# Smart Medicine Box with AI-Based Health Monitoring System")
    st.markdown("")
    st.markdown("This project combines smart medicine management with real-time health monitoring to support elderly patients and caregivers.")
    st.markdown("It provides automated reminders, device-based health tracking, and AI-powered insights for better care decisions.")
    st.markdown("The system helps improve medication adherence, monitor vital signs continuously, and generate useful reports.")
    st.markdown("It is designed to be simple, user-friendly, and practical for home healthcare environments.")

    st.markdown("## Objectives")
    st.markdown("- Smart medicine reminders")
    st.markdown("- Real-time health monitoring")
    st.markdown("- AI health insights")
    st.markdown("- Patient management")
    st.markdown("- Report generation")
    st.markdown("- Emergency alerts")

    st.markdown("## Key Features")
    st.markdown("- Dashboard")
    st.markdown("- Medicine Management")
    st.markdown("- Health Monitoring")
    st.markdown("- AI Insights")
    st.markdown("- Patient Profile")
    st.markdown("- Reports")
    st.markdown("- Settings")

    st.markdown("## Technology Stack")
    st.markdown("- Streamlit")
    st.markdown("- Python")
    st.markdown("- Firebase")
    st.markdown("- ESP32")
    st.markdown("- AI/ML")
    st.markdown("- IoT Sensors")

    st.markdown("---")
    st.caption("Select a module from the sidebar to begin.")


if __name__ == "__main__":
    main()
