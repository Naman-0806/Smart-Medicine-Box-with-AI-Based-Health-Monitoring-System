import streamlit as st
from src.ui import render_sidebar, render_main
from src.data import get_all_dummy_data


st.set_page_config(page_title="Smart Medicine Box Dashboard", layout="wide")


def main():
	data = get_all_dummy_data()
	render_sidebar()
	render_main(data)


if __name__ == "__main__":
	main()

