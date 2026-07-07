import streamlit as st
from src.data import get_all_dummy_data
from components.sidebar import render_sidebar


def render_ai():
    data = get_all_dummy_data()
    render_sidebar()

    st.markdown("# AI Insights")
    st.subheader("Health Score")
    st.markdown(f"**{data['metrics'].get('health_score')}**")

    st.markdown("---")
    st.subheader("Recommendations")
    for r in data.get('ai', []):
        st.markdown(f"- {r}")

    st.markdown("---")
    st.subheader("Risk Indicators")
    st.markdown("(Placeholder risk indicators — dummy data)")


render_ai()
