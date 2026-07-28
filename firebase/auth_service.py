import hashlib
import os
import re
import uuid
from typing import Any, Dict, Optional, Tuple
import streamlit as st

from firebase.config import get_firebase_auth, get_firestore_client
from src.ui import apply_theme_styles


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash password securely using PBKDF2-HMAC-SHA256 with a unique salt."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(stored_hash: str, password_attempt: str) -> bool:
    """Verify a plain-text password attempt against a stored PBKDF2 salt:hash string."""
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        attempt_key = hashlib.pbkdf2_hmac("sha256", password_attempt.encode("utf-8"), salt, 100000)
        return attempt_key.hex() == key_hex
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """Validate email syntax format."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate phone number (minimum 7 digits, digits/dashes/plus only)."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    pattern = r"^\+?\d{7,15}$"
    return bool(re.match(pattern, cleaned))


def signup_user(
    email: str,
    password: str,
    confirm_password: str,
    full_name: str = "",
    phone_number: str = ""
) -> Tuple[bool, str]:
    """Register a new user in Firebase Auth and Firestore `/users` collection."""
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

    auth_mod = get_firebase_auth()
    client = get_firestore_client()
    firebase_uid = None

    # Check if user already exists in Firestore `/users`
    if client:
        try:
            users_ref = client.collection("users")
            query = list(users_ref.where("email", "==", email_clean).limit(1).stream())
            if query:
                return False, "An account with this email already exists."
        except Exception:
            pass

    # Try creating user in Firebase Auth SDK
    if auth_mod:
        try:
            user_record = auth_mod.create_user(
                email=email_clean,
                password=password,
                display_name=full_name_clean or email_clean.split("@")[0]
            )
            firebase_uid = user_record.uid
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "email-already-in-use" in err_msg:
                return False, "An account with this email already exists in Firebase Auth."

    uid = firebase_uid or f"usr-{uuid.uuid4().hex[:12]}"
    pwd_hash = hash_password(password)

    user_data = {
        "uid": uid,
        "email": email_clean,
        "full_name": full_name_clean or email_clean.split("@")[0],
        "phone_number": phone_clean,
        "password_hash": pwd_hash,
    }

    if client:
        try:
            client.collection("users").document(uid).set(user_data)
        except Exception:
            pass

    # Store logged-in user UID in Streamlit session_state
    st.session_state["is_logged_in"] = True
    st.session_state["user_uid"] = uid
    st.session_state["owner_uid"] = uid
    st.session_state["auth_user"] = user_data

    return True, "Account created successfully! Welcome."


def login_user(identifier: str, password: str) -> Tuple[bool, str]:
    """Authenticate user against Firebase Auth or Firestore `/users` using hashed credentials."""
    clean_id = identifier.strip().lower()

    if not clean_id or not password:
        return False, "Please enter both identifier and password."

    auth_mod = get_firebase_auth()
    client = get_firestore_client()

    user_data = None
    target_uid = None

    # Search Firestore `/users` by email or phone
    if client:
        try:
            users_ref = client.collection("users")
            if "@" in clean_id:
                docs = list(users_ref.where("email", "==", clean_id).limit(1).stream())
            else:
                docs = list(users_ref.where("phone_number", "==", clean_id).limit(1).stream())

            if docs:
                user_data = docs[0].to_dict()
                target_uid = docs[0].id
        except Exception:
            pass

    # Lookup via Firebase Auth if user not found in local Firestore query
    if auth_mod and not user_data:
        try:
            if "@" in clean_id:
                fb_user = auth_mod.get_user_by_email(clean_id)
                target_uid = fb_user.uid
                user_data = {
                    "uid": fb_user.uid,
                    "email": fb_user.email,
                    "full_name": fb_user.display_name or clean_id.split("@")[0],
                    "phone_number": fb_user.phone_number or "",
                }
        except Exception:
            pass

    if not user_data:
        return False, "User account not found. Please check your credentials or sign up."

    # Verify password
    stored_hash = user_data.get("password_hash")
    if stored_hash:
        if not verify_password(stored_hash, password):
            return False, "Incorrect password. Please try again."
    else:
        new_hash = hash_password(password)
        user_data["password_hash"] = new_hash
        if client and target_uid:
            try:
                client.collection("users").document(target_uid).set({"password_hash": new_hash}, merge=True)
            except Exception:
                pass

    uid = user_data.get("uid") or target_uid or f"usr-{uuid.uuid4().hex[:12]}"
    
    # Store logged-in user UID in Streamlit session_state
    st.session_state["is_logged_in"] = True
    st.session_state["user_uid"] = uid
    st.session_state["owner_uid"] = uid
    st.session_state["auth_user"] = user_data

    return True, "Login successful!"


def logout_user() -> None:
    """Log out the current user and clear session state."""
    for key in [
        "is_logged_in",
        "user_uid",
        "owner_uid",
        "auth_user",
        "selected_patient_id",
        "patient_registration_data",
        "registration_complete",
        "edit_profile",
        "medicine_df",
        "medicine_patient_id",
        "monitoring_data",
        "dashboard_last_refresh",
    ]:
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
                login_id = st.text_input("Email Address or Phone", placeholder="user@example.com")
                login_pwd = st.text_input("Password", type="password", placeholder="••••••••")
                submitted_login = st.form_submit_button("Log In", type="primary")

                if submitted_login:
                    success, msg = login_user(login_id, login_pwd)
                    if success:
                        st.success(msg)
                        st.rerun()
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
                        st.rerun()
                    else:
                        st.error(msg)


def require_auth():
    """Check if user is logged in. If not, show ONLY authentication screen and stop execution."""
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


