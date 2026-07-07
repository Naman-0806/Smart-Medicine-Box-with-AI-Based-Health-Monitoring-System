import streamlit as st
from src.ui import render_main
from firebase.firebase_service import get_firebase_data


st.set_page_config(page_title="Smart Medicine Box Dashboard", layout="wide")


def main():
    data = get_firebase_data()
    render_main(data)


if __name__ == "__main__":
    main()
