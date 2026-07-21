import streamlit as st
from components.sidebar import render_sidebar


def render_ai():
    render_sidebar()

    st.markdown("# AI Insights")
    st.caption("A concise summary of health status and personalized recommendations.")
    st.divider()

    with st.container(border=True):
        st.subheader("AI Health Summary")
        st.write("Your recent health pattern appears stable with good medication adherence and no immediate concern. The system suggests continued monitoring and routine follow-up.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI Health Score", "88 / 100", "Good")
        with c2:
            st.metric("Adherence", "91%", "+4%")
        with c3:
            st.metric("Overall Risk", "Low", "Stable")

    st.divider()
    with st.container(border=True):
        st.subheader("Medication Adherence")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Medicines Taken", "21")
        with c2:
            st.metric("Missed Doses", "2")
        with c3:
            st.metric("Adherence %", "91%")

    st.divider()
    with st.container(border=True):
        st.subheader("Health Risk Analysis")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Heart Health", "Low Risk")
        with c2:
            st.metric("Oxygen Level", "Normal")
        with c3:
            st.metric("Temperature", "Normal")
        with c4:
            st.metric("Overall Risk", "Low")

    st.divider()
    with st.container(border=True):
        st.subheader("Personalized Recommendations")
        st.write("• Continue taking prescribed medicines on time.")
        st.write("• Keep a light walking routine daily.")
        st.write("• Stay hydrated and maintain regular sleep.")
        st.write("• Review medications with your caregiver weekly.")
        st.write("• Seek medical advice if symptoms worsen.")

    st.divider()
    with st.container(border=True):
        st.subheader("Emergency Alerts")
        st.info("No Emergency Detected")

    st.divider()
    with st.container(border=True):
        st.subheader("Weekly AI Summary")
        st.write("• Medication adherence remained strong this week.")
        st.write("• Health patterns suggest stable daily activity.")
        st.write("• No urgent alerts were triggered.")
        st.write("• Reminder compliance improved compared to last week.")
        st.write("• Continue routine monitoring and follow-up care.")


render_ai()
