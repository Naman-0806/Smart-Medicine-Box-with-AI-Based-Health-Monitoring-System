import streamlit as st


def medicine_table(df):
    st.dataframe(df, use_container_width=True)


def medicine_summary(df):
    counts = df['Status'].value_counts().to_dict()
    return counts
