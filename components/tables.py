import pandas as pd
import streamlit as st


def medicine_table(df):
    if df is None or (isinstance(df, pd.DataFrame) and df.empty) or (isinstance(df, (list, tuple)) and not df):
        st.info("No data available")
    else:
        st.dataframe(df, use_container_width=True)


def medicine_summary(df):
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return {}
    counts = df['Status'].value_counts().to_dict()
    return counts
