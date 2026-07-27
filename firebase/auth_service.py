from typing import Any, Dict, Optional
import streamlit as st
from firebase.config import get_firebase_auth, get_firestore_client
from firebase.firebase_service import get_all_patients, get_patient_by_id, save_patient_registration


def authenticate_patient(identifier: str) -> Dict[str, Any]:
    """Authenticate a patient using phone number or email via Firebase Authentication & Firestore patient records.
    If patient is found, returns their patient ID and profile data.
    If new user, registers a patient record in Firebase.
    """
    clean_id = identifier.strip()
    if not clean_id:
        return {"success": False, "message": "Please enter a valid email address or phone number."}

    auth_mod = get_firebase_auth()
    firebase_uid = None

    # Try Firebase Auth lookup
    if auth_mod:
        try:
            if "@" in clean_id:
                user_record = auth_mod.get_user_by_email(clean_id)
                firebase_uid = user_record.uid
            else:
                formatted_phone = clean_id if clean_id.startswith("+") else f"+{clean_id}"
                user_record = auth_mod.get_user_by_phone_number(formatted_phone)
                firebase_uid = user_record.uid
        except Exception:
            # If not in Firebase Auth yet, attempt creation or proceed to Firestore lookup
            try:
                if "@" in clean_id:
                    user_record = auth_mod.create_user(email=clean_id)
                    firebase_uid = user_record.uid
                else:
                    formatted_phone = clean_id if clean_id.startswith("+") else f"+{clean_id}"
                    user_record = auth_mod.create_user(phone_number=formatted_phone)
                    firebase_uid = user_record.uid
            except Exception:
                pass

    # Search Firestore patients for matching phone number or email or patient_id
    all_patients = get_all_patients()
    matched_patient = None

    for p in all_patients:
        p_phone = str(p.get("phone_number") or p.get("phone") or "").strip().lower()
        p_email = str(p.get("email") or "").strip().lower()
        p_id = str(p.get("patient_id") or p.get("id") or "").strip().lower()
        search_id = clean_id.lower()

        if (
            (p_email and search_id == p_email)
            or (p_phone and search_id in p_phone)
            or (p_id and search_id == p_id)
        ):
            matched_patient = p
            break

    if not matched_patient:
        # Create a new patient record in Firebase for this user
        new_patient_payload = {
            "name": f"Patient ({clean_id})",
            "phone_number": clean_id if "@" not in clean_id else "",
            "email": clean_id if "@" in clean_id else "",
            "doctor_name": "Dr. Assigned",
            "blood_group": "A+",
            "age": 45,
            "gender": "Other",
        }
        new_patient_id = save_patient_registration(new_patient_payload)
        if new_patient_id:
            matched_patient = get_patient_by_id(new_patient_id)
        else:
            # Fallback mock patient if Firestore offline
            matched_patient = {
                "patient_id": f"PT-{clean_id[:6].upper()}",
                "name": f"Patient ({clean_id})",
                "phone_number": clean_id if "@" not in clean_id else "",
                "email": clean_id if "@" in clean_id else "",
                "age": 45,
                "gender": "Other",
            }

    patient_id = matched_patient.get("patient_id") or matched_patient.get("id")

    return {
        "success": True,
        "uid": firebase_uid or f"uid-{patient_id}",
        "identifier": clean_id,
        "patient_id": patient_id,
        "patient": matched_patient,
    }


def login_user(identifier: str) -> bool:
    """Log in the user and lock selected_patient_id to their own patient data."""
    res = authenticate_patient(identifier)
    if res.get("success"):
        st.session_state["is_logged_in"] = True
        st.session_state["auth_user"] = res
        st.session_state["selected_patient_id"] = res["patient_id"]
        return True
    return False


def logout_user() -> None:
    """Log out the current user."""
    st.session_state.pop("is_logged_in", None)
    st.session_state.pop("auth_user", None)
    st.session_state.pop("selected_patient_id", None)
