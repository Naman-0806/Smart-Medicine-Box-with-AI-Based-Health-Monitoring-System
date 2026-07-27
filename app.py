import streamlit as st
from components.sidebar import render_sidebar
from firebase.auth_service import require_auth

st.set_page_config(page_title="Smart Medicine Box Dashboard", layout="wide")


def main():
    render_sidebar()
    require_auth()

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
    st.markdown("- Firebase Auth & Firestore")
    st.markdown("- ESP32 IoT Sensors")
    st.markdown("- AI/ML Analytics")

    st.markdown("---")
    st.caption("Select a module from the sidebar navigation to begin.")


if __name__ == "__main__":
    main()
