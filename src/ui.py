import streamlit as st

# ------------------ Theme ------------------ #

def get_theme():
    return st.session_state.get("theme", "Dark")


def set_theme(theme):
    st.session_state["theme"] = theme


def apply_theme_styles():

    theme = get_theme()

    if theme == "Dark":
        bg = "#0F172A"
        surface = "#1E293B"
        text = "#FFFFFF"
        border = "#334155"
    else:
        bg = "#e6ffee"
        surface = "#ffc2b3"
        text = "#1E293B"
        border = "#D1D5DB"

    st.markdown(
        f"""
<style>

/* Background */

.stApp {{
    background-color: {bg};
    color: {text};
}}

.main .block-container {{
    color: {text};
}}

/* Sidebar */

[data-testid="stSidebar"] {{
    background-color: {surface};
    border-right:1px solid {border};
}}

[data-testid="stSidebar"] * {{
    color:{text} !important;
}}

/* Headings */

h1,h2,h3,h4,h5,h6 {{
    color:{text} !important;
}}

p,label,span {{
    color:{text} !important;
}}

/* Metrics */

div[data-testid="stMetric"] {{
    background:{surface};
    border:1px solid {border};
    border-radius:15px;
    padding:15px;
}}

div[data-testid="stMetric"] * {{
    color:{text} !important;
}}

[data-testid="stMetricValue"] {{
    font-size:2rem;
    font-weight:700;
}}

[data-testid="stMetricLabel"] {{
    font-size:0.95rem;
}}

[data-testid="stMetricDelta"] {{
    color:#22C55E !important;
}}

/* Containers */

div[data-testid="stVerticalBlockBorderWrapper"] {{
    background:{surface};
    border:1px solid {border};
    border-radius:18px;
    padding:10px;
}}

/* Tables */

[data-testid="stDataFrame"] * {{
    color:{text} !important;
}}

</style>
""",
        unsafe_allow_html=True,
    )