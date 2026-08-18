import json
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import requests
import streamlit as st

from firebase.config import get_firebase_web_api_key, get_firestore_client
from firebase.firestore_rest import (
    firestore_get_doc,
    firestore_set_doc,
    get_jwt_project_id,
)
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
    if not api_key:
        err_msg = "FIREBASE_WEB_API_KEY environment variable is not set or empty."
        print(f"[FIREBASE AUTH ERROR] {err_msg}")
        return False, {}, "MISSING_API_KEY"

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:{endpoint}?key={api_key}"

    try:
        response = requests.post(url, json=payload, timeout=10)

        print("========== FIREBASE RESPONSE ==========")
        print("Status:", response.status_code)
        print("Body:", response.text)
        print("=======================================")

        try:
            res_data = response.json()
        except Exception:
            res_data = {}

        if response.status_code == 200:
            return True, res_data if isinstance(res_data, dict) else {}, ""

        error_info = res_data.get("error", {}) if isinstance(res_data, dict) else {}
        err_msg_code = str(error_info.get("message", "")).upper()
        if not err_msg_code:
            err_msg_code = f"HTTP_{response.status_code}"

        print(f"[FIREBASE AUTH ERROR] Endpoint: {endpoint} | Status: {response.status_code} | Exact Firebase Error: {response.text}")
        return False, res_data if isinstance(res_data, dict) else {}, err_msg_code

    except requests.exceptions.Timeout:
        print(f"[FIREBASE AUTH ERROR] Endpoint: {endpoint} | Network Timeout")
        return False, {}, "NETWORK_TIMEOUT"
    except requests.exceptions.ConnectionError:
        print(f"[FIREBASE AUTH ERROR] Endpoint: {endpoint} | Connection Error")
        return False, {}, "CONNECTION_ERROR"
    except Exception as e:
        print(f"[FIREBASE AUTH EXCEPTION] Endpoint: {endpoint} | Exception: {type(e).__name__}: {e}")
        return False, {}, f"NETWORK_ERROR_{type(e).__name__}"


def _map_firebase_error(err_code: str, mode: str = "login") -> str:
    """Map Firebase Auth error string codes to clear user-facing messages."""
    err_upper = err_code.upper()
    if "NETWORK_TIMEOUT" in err_upper or "TIMEOUT" in err_upper:
        return "Connection timed out. Please check your internet connection and try again."
    if "CONNECTION_ERROR" in err_upper or "NETWORK_ERROR" in err_upper:
        return "Unable to connect to authentication server. Please verify your internet connection."
    if "EMAIL_EXISTS" in err_upper:
        return "An account with this email address already exists."
    if "INVALID_EMAIL" in err_upper:
        return "Please enter a valid email address."
    if "WEAK_PASSWORD" in err_upper or "PASSWORD_TOO_SHORT" in err_upper:
        return "Password must be at least 6 characters long."
    if "OPERATION_NOT_ALLOWED" in err_upper:
        return "Email/Password sign-in is disabled in Firebase Console."
    if "MISSING_API_KEY" in err_upper or "INVALID_KEY" in err_upper or "API_KEY_INVALID" in err_upper:
        return "Invalid or missing Firebase API Key. Please check FIREBASE_WEB_API_KEY."
    if "EMAIL_NOT_FOUND" in err_upper or "USER_NOT_FOUND" in err_upper:
        return "User account not found. Please check your credentials or sign up."
    if "INVALID_PASSWORD" in err_upper or "WRONG_PASSWORD" in err_upper or "INVALID_LOGIN_CREDENTIALS" in err_upper:
        return "Incorrect password. Please try again."
    if "USER_DISABLED" in err_upper:
        return "This user account has been disabled."
    if "TOO_MANY_ATTEMPTS" in err_upper:
        return "Access temporarily disabled due to many failed attempts. Please try again later."

    if err_code and not err_code.startswith("HTTP_"):
        if mode == "login":
            return f"Authentication failed: {err_code}"
        return f"Account registration failed: {err_code}"

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
        err_msg = "Email and password are required fields."
        print(f"[FIREBASE AUTH ERROR] Signup failed: {err_msg}")
        return False, err_msg

    if not validate_email(email_clean):
        err_msg = "Please enter a valid email address (e.g. user@example.com)."
        print(f"[FIREBASE AUTH ERROR] Signup failed: {err_msg}")
        return False, err_msg

    if len(password) < 6:
        err_msg = "Password must be at least 6 characters long."
        print(f"[FIREBASE AUTH ERROR] Signup failed: {err_msg}")
        return False, err_msg

    if password != confirm_password:
        err_msg = "Passwords do not match."
        print(f"[FIREBASE AUTH ERROR] Signup failed: {err_msg}")
        return False, err_msg

    if phone_clean and not validate_phone(phone_clean):
        err_msg = "Please enter a valid phone number (e.g. +1234567890)."
        print(f"[FIREBASE AUTH ERROR] Signup failed: {err_msg}")
        return False, err_msg

    # Direct Firebase Auth via Identity Toolkit REST API
    success, res_data, err_code = _firebase_rest_auth(
        "signUp",
        {"email": email_clean, "password": password, "returnSecureToken": True}
    )
    if not success:
        user_facing_msg = _map_firebase_error(err_code, mode="signup")
        print(f"[FIREBASE AUTH ERROR] Signup failed for {email_clean}: {err_code} -> {user_facing_msg}")
        return False, user_facing_msg

    uid = res_data.get("localId")
    id_token = res_data.get("idToken")
    refresh_token = res_data.get("refreshToken")
    expires_in = int(res_data.get("expiresIn") or 3600)

    if not uid:
        err_msg = "Failed to retrieve user ID from Firebase Authentication."
        print(f"[FIREBASE AUTH ERROR] Signup failed for {email_clean}: {err_msg}")
        return False, err_msg

    project_id = get_jwt_project_id(id_token)

    now_iso = datetime.utcnow().isoformat()
    user_data = {
        "uid": uid,
        "full_name": full_name_clean or email_clean.split("@")[0],
        "email": email_clean,
        "phone_number": phone_clean,
        "created_at": now_iso,
    }

    # Store tokens in session state first so REST requests can authenticate
    st.session_state["id_token"] = id_token
    st.session_state["refresh_token"] = refresh_token
    st.session_state["token_expires_at"] = time.time() + expires_in
    if project_id:
        st.session_state["project_id"] = project_id

    # Store user profile document in Firestore at /users/{uid} using REST or Admin SDK
    client = get_firestore_client()
    if client:
        try:
            client.collection("users").document(uid).set(user_data, merge=True)
        except Exception as e:
            print(f"[WARNING] Admin SDK write failed, attempting REST: {e}")
            firestore_set_doc(f"users/{uid}", user_data, id_token=id_token, project_id=project_id)
    else:
        firestore_set_doc(f"users/{uid}", user_data, id_token=id_token, project_id=project_id)

    # Store user session state
    st.session_state["is_logged_in"] = True
    st.session_state["user_uid"] = uid
    st.session_state["owner_uid"] = uid
    st.session_state["selected_patient_id"] = uid
    st.session_state["auth_user"] = user_data
    try:
        st.query_params["session_uid"] = uid
    except Exception:
        pass

    print(f"[FIREBASE AUTH SUCCESS] Successfully registered real Firebase user: {email_clean} (UID: {uid})")
    return True, "Account created successfully! Welcome."


def login_user(identifier: str, password: str) -> Tuple[bool, str]:
    """Authenticate user with email and password strictly through Firebase Authentication."""
    clean_id = identifier.strip().lower()

    if not clean_id or not password:
        err_msg = "Please enter both email address and password."
        print(f"[FIREBASE AUTH ERROR] Login failed: {err_msg}")
        return False, err_msg

    if not validate_email(clean_id):
        err_msg = "Please enter a valid email address."
        print(f"[FIREBASE AUTH ERROR] Login failed: {err_msg}")
        return False, err_msg

    # Direct Firebase Auth via Identity Toolkit REST API
    success, res_data, err_code = _firebase_rest_auth(
        "signInWithPassword",
        {"email": clean_id, "password": password, "returnSecureToken": True}
    )
    if not success:
        user_facing_msg = _map_firebase_error(err_code, mode="login")
        print(f"[FIREBASE AUTH ERROR] Login failed for {clean_id}: {err_code} -> {user_facing_msg}")
        return False, user_facing_msg

    uid = res_data.get("localId")
    id_token = res_data.get("idToken")
    refresh_token = res_data.get("refreshToken")
    expires_in = int(res_data.get("expiresIn") or 3600)

    if not uid:
        err_msg = "User account not found. Please check your credentials or sign up."
        print(f"[FIREBASE AUTH ERROR] Login failed for {clean_id}: {err_msg}")
        return False, err_msg

    project_id = get_jwt_project_id(id_token)

    # Store tokens in session state
    st.session_state["id_token"] = id_token
    st.session_state["refresh_token"] = refresh_token
    st.session_state["token_expires_at"] = time.time() + expires_in
    if project_id:
        st.session_state["project_id"] = project_id

    # After successful authentication, load user profile from Firestore /users/{uid}
    user_data = None
    client = get_firestore_client()
    if client:
        try:
            doc = client.collection("users").document(uid).get()
            if doc.exists:
                user_data = doc.to_dict()
        except Exception as e:
            print(f"[WARNING] Failed to fetch user profile via Admin SDK: {e}")

    if not user_data:
        ok, rest_data, _ = firestore_get_doc(f"users/{uid}", id_token=id_token, project_id=project_id)
        if ok and rest_data:
            user_data = rest_data

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
    try:
        st.query_params["session_uid"] = uid
    except Exception:
        pass

    print(f"[FIREBASE AUTH SUCCESS] Successfully authenticated real Firebase user: {clean_id} (UID: {uid})")
    return True, "Login successful!"


def logout_user() -> None:
    """Log out the current user and clear session state completely."""
    for key in list(st.session_state.keys()):
        st.session_state.pop(key, None)
    try:
        st.query_params.clear()
    except Exception:
        pass
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
                    try:
                        with st.spinner("Authenticating with Firebase..."):
                            success, msg = login_user(login_id, login_pwd)
                        if success:
                            st.success(msg)
                            st.switch_page("pages/dashboard.py")
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Authentication error: {str(e)}")

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
                    try:
                        with st.spinner("Creating your Firebase account..."):
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
                    except Exception as e:
                        st.error(f"Registration error: {str(e)}")


def require_auth():
    """Single reusable authentication guard for securing all application pages."""
    if not st.session_state.get("is_logged_in"):
        try:
            param_uid = st.query_params.get("session_uid") or st.query_params.get("uid")
            if param_uid and str(param_uid).strip():
                uid = str(param_uid).strip()
                client = get_firestore_client()
                user_data = None
                if client:
                    try:
                        doc = client.collection("users").document(uid).get()
                        if doc.exists:
                            user_data = doc.to_dict()
                    except Exception:
                        pass
                if not user_data:
                    user_data = {"uid": uid, "email": ""}
                st.session_state["is_logged_in"] = True
                st.session_state["user_uid"] = uid
                st.session_state["owner_uid"] = uid
                st.session_state["selected_patient_id"] = uid
                st.session_state["auth_user"] = user_data
        except Exception:
            pass

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