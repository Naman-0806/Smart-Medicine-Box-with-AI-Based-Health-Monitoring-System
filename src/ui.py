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
        surface_hover = "#334155"
        text = "#FFFFFF"
        text_muted = "#94A3B8"
        border = "#334155"
        input_bg = "#1E293B"
        popover_bg = "#1E293B"
    else:
        bg = "#e6ffee"
        surface = "#ffc2b3"
        surface_hover = "#ffab99"
        text = "#1E293B"
        text_muted = "#64748B"
        border = "#D1D5DB"
        input_bg = "#FFFFFF"
        popover_bg = "#FFFFFF"

    st.markdown(
        f"""
<style>

/* App Background & Base Text */
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
    border-right: 1px solid {border};
}}

[data-testid="stSidebar"] * {{
    color: {text} !important;
}}

/* Headings & General Text */
h1, h2, h3, h4, h5, h6 {{
    color: {text} !important;
}}

p, label, span {{
    color: {text};
}}

/* Form Inputs (Text, Number, Area, Date, Time) */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] > textarea,
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input,
.stTimeInput input {{
    background-color: {input_bg} !important;
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
    border-color: {border} !important;
    border-radius: 8px;
}}

/* Input Placeholders */
input::placeholder,
textarea::placeholder,
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {{
    color: {text_muted} !important;
    -webkit-text-fill-color: {text_muted} !important;
    opacity: 1 !important;
}}

/* Number Input Controls */
div[data-testid="stNumberInput"] button {{
    background-color: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
}}

div[data-testid="stNumberInput"] button:hover {{
    background-color: {surface_hover} !important;
}}

div[data-testid="stNumberInput"] button * {{
    color: {text} !important;
}}

/* Selectbox & Multiselect */
div[data-baseweb="select"],
div[data-baseweb="select"] > div {{
    background-color: {input_bg} !important;
    color: {text} !important;
    border-color: {border} !important;
    border-radius: 8px;
}}

div[data-baseweb="select"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

div[data-baseweb="select"] svg {{
    fill: {text} !important;
}}

/* Dropdown Menu / Popovers */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-baseweb="menu"],
ul[role="listbox"] {{
    background-color: {popover_bg} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 8px;
}}

li[data-baseweb="menu-item"],
li[role="option"] {{
    background-color: {popover_bg} !important;
    color: {text} !important;
}}

li[data-baseweb="menu-item"] *,
li[role="option"] * {{
    color: {text} !important;
    -webkit-text-fill-color: {text} !important;
}}

li[data-baseweb="menu-item"]:hover,
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {{
    background-color: {surface_hover} !important;
    color: {text} !important;
}}

/* Secondary Buttons */
button[kind="secondary"],
button[data-testid="baseButton-secondary"],
.stButton > button {{
    background-color: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 8px;
}}

button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
.stButton > button:hover {{
    background-color: {surface_hover} !important;
    border-color: {border} !important;
    color: {text} !important;
}}

button[kind="secondary"] *,
button[data-testid="baseButton-secondary"] *,
.stButton > button * {{
    color: {text} !important;
}}

/* Primary Buttons */
button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: 1px solid #2563EB !important;
    border-radius: 8px;
}}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    background-color: #1D4ED8 !important;
    border-color: #1D4ED8 !important;
    color: #FFFFFF !important;
}}

button[kind="primary"] *,
button[data-testid="baseButton-primary"] * {{
    color: #FFFFFF !important;
}}

/* Tabs */
div[data-testid="stTabs"] button[role="tab"],
div[data-testid="stTabs"] button[data-baseweb="tab"] {{
    background-color: transparent !important;
    color: {text_muted} !important;
}}

div[data-testid="stTabs"] button[role="tab"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"] * {{
    color: {text_muted} !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"]:hover,
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{
    color: {text} !important;
    border-bottom-color: #2563EB !important;
}}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * {{
    color: {text} !important;
}}

/* Radio & Checkboxes */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] span,
div[data-testid="stRadio"] p,
div[data-testid="stCheckbox"] label,
div[data-testid="stCheckbox"] span,
div[data-testid="stCheckbox"] p {{
    color: {text} !important;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    background-color: {surface} !important;
    border: 1px solid {border} !important;
    border-radius: 12px;
}}

div[data-testid="stExpander"] summary {{
    color: {text} !important;
}}

div[data-testid="stExpander"] summary * {{
    color: {text} !important;
}}

/* Metrics */
div[data-testid="stMetric"] {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 15px;
    padding: 15px;
}}

div[data-testid="stMetric"] * {{
    color: {text} !important;
}}

[data-testid="stMetricValue"] {{
    font-size: 2rem;
    font-weight: 700;
}}

[data-testid="stMetricLabel"] {{
    font-size: 0.95rem;
}}

[data-testid="stMetricDelta"] {{
    color: #22C55E !important;
}}

/* Containers */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 18px;
    padding: 10px;
}}

/* Tables */
[data-testid="stDataFrame"] {{
    border: 1px solid {border};
    border-radius: 8px;
}}

[data-testid="stDataFrame"] * {{
    color: {text} !important;
}}

</style>
""",
        unsafe_allow_html=True,
    )