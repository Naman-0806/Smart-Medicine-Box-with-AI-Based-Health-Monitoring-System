import streamlit as st
from components.sidebar import render_sidebar
from src.ui import _apply_styles


def render_ai():
    render_sidebar()
    _apply_styles()

    st.markdown("# AI Insights")
    st.markdown("AI Health Summary")
    st.markdown("Your recent health pattern appears stable with good medication adherence and no immediate concern. The system suggests continued monitoring and routine follow-up.")

    st.markdown("---")
    st.subheader("AI Health Score")
    st.markdown("**88 / 100**")
    st.markdown("**Status:** Good")

    st.markdown("---")
    st.subheader("Medication Adherence")
    st.markdown("- Medicines Taken: 21")
    st.markdown("- Missed Doses: 2")
    st.markdown("- Adherence Percentage: 91%")

    st.markdown("---")
    st.subheader("Health Risk Analysis")
    st.markdown("- Heart Health: Low Risk")
    st.markdown("- Oxygen Level: Normal")
    st.markdown("- Temperature: Normal")
    st.markdown("- Overall Risk: Low")

    st.markdown("---")
    st.subheader("Personalized Recommendations")
    st.markdown("- Continue taking prescribed medicines on time.")
    st.markdown("- Keep a light walking routine daily.")
    st.markdown("- Stay hydrated and maintain regular sleep.")
    st.markdown("- Review medications with your caregiver weekly.")
    st.markdown("- Seek medical advice if symptoms worsen.")

    st.markdown("---")
    st.subheader("Emergency Alerts")
    st.info("No Emergency Detected")

    st.markdown("---")
    st.subheader("Weekly AI Summary")
    st.markdown("- Medication adherence remained strong this week.")
    st.markdown("- Health patterns suggest stable daily activity.")
    st.markdown("- No urgent alerts were triggered.")
    st.markdown("- Reminder compliance improved compared to last week.")
    st.markdown("- Continue routine monitoring and follow-up care.")


render_ai()
