import json
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import requests
import streamlit as st

from firebase.config import get_firebase_web_api_key, get_firestore_client
from src.ui import apply_theme_styles


def validate_email(email: str) -> bool:
    """Validate email syntax format."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate phone number (minimum 7 digits, digits/dashes/plus only)."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    pattern = r"^\+?\d{7,15}$"
    return bool(re.match(pattern, cleaned))


def _firebase_rest_auth(endpoint: str, payload: dict) -> Tuple[bool, dict, str]:
    """Execute Firebase Identity Toolkit REST API request."""
    api_key = get_firebase_web_api_key()
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:{endpoint}?key={api_key}"

    try:
        response = requests.post(url, json=payload, timeout=10)

        print("========== FIREBASE RESPONSE ==========")
        print("Status:", response.status_code)
        print("Body:", response.text)
        print("=======================================")

        res_data = response.json()

        if response.status_code == 200:
            return True, res_data, ""

        error_info = res_data.get("error", {})
        err_msg_code = str(error_info.get("message", "")).upper()
        return False, res_data, err_msg_code

    except Exception as e:
        return False, {}, str(e)


def _map_firebase_error(err_code: str, mode: str = "login") -> str:
    """Map Firebase Auth error string codes to clear user-facing messages."""
    if "EMAIL_EXISTS" in err_code:
        return "An account with this email address already exists."
    if "INVALID_EMAIL" in err_code:
        return "Please enter a valid email address."
    if "WEAK_PASSWORD" in err_code:
        return "Password must be at least 6 characters long."
    if "EMAIL_NOT_FOUND" in err_code or "USER_NOT_FOUND" in err_code:
        return "User account not found. Please check your credentials or sign up."
    if "INVALID_PASSWORD" in err_code or "WRONG_PASSWORD" in err_code or "INVALID_LOGIN_CREDENTIALS" in err_code:
        return "Incorrect password. Please try again."
    if "USER_DISABLED" in err_code:
        return "This user account has been disabled."
    if "TOO_MANY_ATTEMPTS" in err_code:
        return "Access temporarily disabled due to many failed attempts. Please try again later."

    if mode == "login":
        return "Authentication failed. Please check your email and password."
    return "Account registration failed. Please try again."


def signup_user(
    email: str,
    password: str,
    confirm_password: str,
    full_name: str = "",
    phone_number: str = ""
) -> Tuple[bool, str]:
    """Register a new user via Firebase Authentication and save user record in Firestore /users/{uid}."""
    email_clean = email.strip().lower()
    full_name_clean = full_name.strip()
    phone_clean = phone_number.strip()

    if not email_clean or not password:
        return False, "Email and password are required fields."

    if not validate_email(email_clean):
        return False, "Please enter a valid email address (e.g. user@example.com)."

    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if password != confirm_password:
        return False, "Passwords do not match."

    if phone_clean and not validate_phone(phone_clean):
        return False, "Please enter a valid phone number (e.g. +1234567890)."

    # Direct Firebase Auth via Identity Toolkit REST API
    success, res_data, err_code = _firebase_rest_auth(
        "signUp",
        {"email": email_clean, "password": password, "returnSecureToken": True}
    )
    if not success:
        return False, _map_firebase_error(err_code, mode="signup")

    uid = res_data.get("localId")
    if not uid:
        return False, "Failed to retrieve user ID from Firebase Authentication."

    now_iso = datetime.utcnow().isoformat()
    user_data = {
        "uid": uid,
        "full_name": full_name_clean or email_clean.split("@")[0],
        "email": email_clean,
        "phone_number": phone_clean,
        "created_at": now_iso,
    }

    # Store user profile document in Firestore at /users/{uid} using Firebase Admin SDK
    client = get_firestore_client()
    if client:
        try:
            client.collection("users").document(uid).set(user_data, merge=True)
        except Exception as e:
            print(f"[WARNING] Failed to save user profile to Firestore: {e}")

    # Store user session state
    st.session_state["is_logged_in"] = True
    st.session_state["user_uid"] = uid
    st.session_state["owner_uid"] = uid
    st.session_state["selected_patient_id"] = uid
    st.session_state["auth_user"] = user_data

    return True, "Account created successfully! Welcome."


def login_user(identifier: str, password: str) -> Tuple[bool, str]:
    """Authenticate user with email and password strictly through Firebase Authentication."""
    clean_id = identifier.strip().lower()

    if not clean_id or not password:
        return False, "Please enter both email address and password."

    if not validate_email(clean_id):
        return False, "Please enter a valid email address."

    # Direct Firebase Auth via Identity Toolkit REST API
    success, res_data, err_code = _firebase_rest_auth(
        "signInWithPassword",
        {"email": clean_id, "password": password, "returnSecureToken": True}
    )
    if not success:
        return False, _map_firebase_error(err_code, mode="login")

    uid = res_data.get("localId")
    if not uid:
        return False, "User account not found. Please check your credentials or sign up."

    # After successful authentication, load user profile from Firestore /users/{uid}
    client = get_firestore_client()
    user_data = None
    if client:
        try:
            doc = client.collection("users").document(uid).get()
            if doc.exists:
                user_data = doc.to_dict()
        except Exception as e:
            print(f"[WARNING] Failed to fetch user profile from Firestore: {e}")

    if not user_data:
        user_data = {
            "uid": uid,
            "full_name": clean_id.split("@")[0],
            "email": clean_id,
            "phone_number": "",
        }

    # Store user session state
    st.session_state["is_logged_in"] = True
    st.session_state["user_uid"] = uid
    st.session_state["owner_uid"] = uid
    st.session_state["selected_patient_id"] = uid
    st.session_state["auth_user"] = user_data

    return True, "Login successful!"


def logout_user() -> None:
    """Log out the current user and clear session state completely."""
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    st.rerun()


def render_login_page():
    """Render the full Login & Signup page interface."""
    apply_theme_styles()

    st.markdown("# 🔐 Smart Medicine Box Authentication")
    st.caption("Please log in or create an account to access your smart medicine dashboard.")
    st.divider()

    col_center, _ = st.columns([2, 1])
    with col_center:
        tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Create Account (Sign Up)"])

        with tab_login:
            st.subheader("Login to your Account")
            with st.form("login_form_main"):
                login_id = st.text_input("Email Address", placeholder="user@example.com")
                login_pwd = st.text_input("Password", type="password", placeholder="••••••••")
                submitted_login = st.form_submit_button("Log In", type="primary")

                if submitted_login:
                    success, msg = login_user(login_id, login_pwd)
                    if success:
                        st.success(msg)
                        st.switch_page("pages/dashboard.py")
                    else:
                        st.error(msg)

        with tab_signup:
            st.subheader("Register a New Account")
            with st.form("signup_form_main"):
                su_name = st.text_input("Full Name", placeholder="Jane Doe")
                su_email = st.text_input("Email Address *", placeholder="user@example.com")
                su_phone = st.text_input("Phone Number (Optional)", placeholder="+1234567890")
                su_pwd = st.text_input("Password *", type="password", placeholder="Minimum 6 characters")
                su_pwd2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat password")
                submitted_signup = st.form_submit_button("Create Account", type="primary")

                if submitted_signup:
                    success, msg = signup_user(
                        email=su_email,
                        password=su_pwd,
                        confirm_password=su_pwd2,
                        full_name=su_name,
                        phone_number=su_phone,
                    )
                    if success:
                        st.success(msg)
                        st.switch_page("pages/dashboard.py")
                    else:
                        st.error(msg)


def require_auth():
    """Single reusable authentication guard for securing all application pages."""
    user_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
    is_logged_in = st.session_state.get("is_logged_in", False)

    if not is_logged_in or not user_uid:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
            header[data-testid="stHeader"] {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        render_login_page()
        st.stop()

    from components.sidebar import render_sidebar
    render_sidebar()