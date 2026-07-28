import streamlit as st
from firebase.auth_service import login_user, logout_user, signup_user
from firebase.firebase_service import get_patient_by_id
from src.ui import apply_theme_styles

PAGES = [
    "Dashboard",
    "Patient",
    "Medicines",
    "Health Monitoring",
    "AI Insights",
    "Reports",
    "Settings",
]


def render_sidebar():
    apply_theme_styles()

    is_logged_in = st.session_state.get("is_logged_in", False)
    auth_user = st.session_state.get("auth_user") or {}
    owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")

    if not is_logged_in or not owner_uid:
        # Hide sidebar completely before login
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

    # Hide default Streamlit sidebar page list for custom navigation
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navigation")

    user_name = auth_user.get("full_name") or auth_user.get("email", "").split("@")[0] or "User"
    user_email = auth_user.get("email") or ""

    # Enforce user-specific patient ID session mapping
    st.session_state["selected_patient_id"] = owner_uid
    st.session_state["owner_uid"] = owner_uid

    st.sidebar.success(f"🟢 Logged in as:\n**{user_name}**")
    if user_email:
        st.sidebar.caption(f"📧 {user_email}")

    patient = get_patient_by_id(owner_uid, owner_uid=owner_uid)
    if patient:
        st.sidebar.markdown(f"👤 Profile: **{patient.get('name') or patient.get('full_name')}**")
        st.sidebar.caption(f"ID: `{owner_uid}`")
    else:
        st.sidebar.info("📝 No patient profile registered yet.")

    st.sidebar.markdown("---")

    # Module Navigation
    st.sidebar.page_link("pages/dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.page_link("pages/patient.py", label="Patient", icon="👤")
    st.sidebar.page_link("pages/medicines.py", label="Medicines", icon="💊")
    st.sidebar.page_link("pages/monitoring.py", label="Health Monitoring", icon="🩺")
    st.sidebar.page_link("pages/ai_insights.py", label="AI Insights", icon="🧠")
    st.sidebar.page_link("pages/reports.py", label="Reports", icon="📋")
    st.sidebar.page_link("pages/settings.py", label="Settings", icon="⚙️")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", key="sidebar_logout_btn", use_container_width=True):
        logout_user()

    st.sidebar.markdown("---")
    st.sidebar.caption("Smart Medicine Box Healthcare Platform")

