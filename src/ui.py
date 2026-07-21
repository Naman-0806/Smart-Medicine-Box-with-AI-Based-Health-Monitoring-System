import streamlit as st
import pandas as pd
import altair as alt
from streamlit.components.v1 import html


THEME_STORAGE_KEY = "smart_medicine_box_theme"


def get_theme():
    theme = st.session_state.get("theme", "Dark")
    return "Dark" if str(theme).strip().lower() == "dark" else "Light"


def set_theme(theme):
    normalized = "Dark" if str(theme).strip().lower() == "dark" else "Light"
    st.session_state["theme"] = normalized
    return normalized


def _inject_theme_script():
    current_theme = get_theme().lower()
    script = f"""
    <script>
      const storageKey = "{THEME_STORAGE_KEY}";
      const savedTheme = window.parent.localStorage.getItem(storageKey);
      const theme = (savedTheme || "{get_theme()}").toLowerCase();
      const normalizedTheme = theme === "dark" ? "dark" : "light";
      const root = window.parent.document.documentElement;
      const body = window.parent.document.body;
      root.setAttribute("data-theme", normalizedTheme);
      body.setAttribute("data-theme", normalizedTheme);
      root.style.colorScheme = normalizedTheme;
      window.parent.localStorage.setItem(storageKey, normalizedTheme === "dark" ? "Dark" : "Light");
    </script>
    """
    html(script, height=0)


_THEME_STYLE = """
<style>
:root {
    color-scheme: light;
    --bg: #f5f7fb;
    --surface: #ffffff;
    --surface-2: #f8fbff;
    --text: #0f172a;
    --muted: #64748b;
    --accent: #2563eb;
    --accent-2: #60a5fa;
    --border: rgba(15, 23, 42, 0.12);
    --shadow: rgba(15, 23, 42, 0.08);
}
:root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #020617;
    --surface: #0f172a;
    --surface-2: #111c34;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #60a5fa;
    --accent-2: #38bdf8;
    --border: rgba(148, 163, 184, 0.24);
    --shadow: rgba(2, 6, 23, 0.45);
}
html, body, .stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
}
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--surface) 0%, var(--surface-2) 100%) !important;
    border-right: 1px solid var(--border);
    color: var(--text) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text) !important;
}
[data-testid="stToolbar"] {
    background: var(--surface) !important;
    color: var(--text) !important;
}
.card, .section-card {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 8px 24px var(--shadow);
    margin-bottom: 16px;
    opacity: 0;
    animation: fadeInUp 0.45s ease forwards;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:hover, .section-card:hover {
    transform: translateY(-2px) scale(1.01);
    box-shadow: 0 12px 28px var(--shadow);
}
.card .title {
    font-size: 0.84rem;
    color: var(--accent);
    font-weight: 700;
    margin-bottom: 6px;
    letter-spacing: 0.01em;
}
.card .value {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
}
.section-title {
    font-size: 1.02rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 8px;
}
.helper-text {
    color: var(--muted);
    font-size: 0.9rem;
}
.stButton > button, .stDownloadButton > button {
    border-radius: 999px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: white;
    border: 1px solid transparent;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.16);
}
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div,
.stDateInput input,
.stCheckbox > label,
.stRadio > label {
    background: var(--surface) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
.stMetric, [data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px;
    color: var(--text) !important;
}
div[data-testid="stDataFrame"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px;
}
[data-testid="stDataFrame"] * {
    color: var(--text) !important;
}
.stAlert, .stWarning, .stInfo, .stSuccess {
    border-radius: 12px;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""


def apply_theme_styles():
    _inject_theme_script()
    st.markdown(_THEME_STYLE, unsafe_allow_html=True)


def render_sidebar():
    st.sidebar.title("Navigation")
    menu = st.sidebar.radio("", ["Dashboard", "Patient", "Medicines", "Health Monitoring", "AI Insights", "Reports", "Settings"])
    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box")


def _card(title, content):
    st.markdown(f"<div class='card'><div class='title'>{title}</div><div class='value'>{content}</div></div>", unsafe_allow_html=True)


def render_main(data: dict):
    apply_theme_styles()
    st.markdown("# Smart Medicine Box Dashboard")

    patient = data["patient"]
    metrics = data["metrics"]

    # Patient info
    with st.container():
        col1, col2 = st.columns([2, 5])
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"**Name:** {patient['name']}  \\n+**Age:** {patient['age']}  \\n+**Patient ID:** {patient['patient_id']}  \\n+**Device Status:** {patient['device_status']}  \\n+**Last Sync:** {patient['last_sync']}", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                _card("Heart Rate", f"{metrics['heart_rate']} bpm")
            with c2:
                _card("SpO₂", f"{metrics['spo2']} %")
            with c3:
                _card("Temperature", f"{metrics['temperature']} °C")
            with c4:
                _card("Health Score", f"{metrics['health_score']}")

    st.markdown("---")

    # Medicine table and alerts
    with st.container():
        left, right = st.columns([3, 1])
        with left:
            st.subheader("Medicine Status")
            df = data["medicines"]
            st.dataframe(df, use_container_width=True)
        with right:
            st.subheader("Alerts")
            for a in data["alerts"]:
                st.markdown(f"- {a['text']}")

    st.markdown("---")

    # AI Recommendation
    st.subheader("AI Recommendations")
    ai = data.get("ai", [])
    if isinstance(ai, list):
        for rec in ai:
            st.markdown(f"<div class='card small'>{rec}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='card small'>{ai}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    st.subheader("Trends")
    trends = data["trends"]
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Heart Rate Trend**")
        chart = alt.Chart(trends).mark_line().encode(x='time:T', y='heart_rate:Q')
        st.altair_chart(chart, use_container_width=True)

    with col_b:
        st.markdown("**SpO₂ Trend**")
        chart2 = alt.Chart(trends).mark_line(color='#4caf50').encode(x='time:T', y='spo2:Q')
        st.altair_chart(chart2, use_container_width=True)

    with col_c:
        st.markdown("**Temperature Trend**")
        chart3 = alt.Chart(trends).mark_line(color='#ff9800').encode(x='time:T', y='temperature:Q')
        st.altair_chart(chart3, use_container_width=True)
