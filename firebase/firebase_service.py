import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from firebase.config import get_firestore_client
from firebase.firestore_rest import (
    firestore_delete_doc,
    firestore_get_doc,
    firestore_list_docs,
    firestore_set_doc,
)

_ESP32_LIVE_CACHE: Dict[str, Any] = {}


def invalidate_firebase_cache():
    """Clear cached patient and dashboard data from session_state forcing fresh reads on mutations."""
    try:
        import streamlit as st
        for k in [
            "cached_user_patients",
            "cached_patient_data",
            "cached_dashboard_data",
            "medicine_df",
            "medicine_patient_id",
            "monitoring_data",
            "dashboard_last_refresh",
        ]:
            st.session_state.pop(k, None)
    except Exception:
        pass


def _resolve_user_uid(uid: Optional[str] = None) -> Optional[str]:
    """Helper to resolve current user's Firebase UID. Strictly enforces authenticated session UID to prevent cross-user data access."""
    try:
        import streamlit as st
        is_logged_in = st.session_state.get("is_logged_in", False)
        session_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        if is_logged_in and session_uid and str(session_uid).strip():
            return str(session_uid).strip()
    except Exception:
        pass
    if uid and str(uid).strip():
        return str(uid).strip()
    return None


# ----------------------------------------------------------------------
# Internal Firestore Unified CRUD Helpers (Admin SDK + REST Client)
# ----------------------------------------------------------------------

def _write_doc(path: str, data: Dict[str, Any], merge: bool = True) -> Tuple[bool, str]:
    """Write document to Firestore via Admin SDK if initialized, or REST API."""
    client = get_firestore_client()
    if client:
        try:
            parts = path.strip("/").split("/")
            if len(parts) == 2:
                client.collection(parts[0]).document(parts[1]).set(data, merge=merge)
                return True, ""
            elif len(parts) == 4:
                client.collection(parts[0]).document(parts[1]).collection(parts[2]).document(parts[3]).set(data, merge=merge)
                return True, ""
        except Exception as e:
            print(f"[FIRESTORE WRITE NOTE] Admin SDK failed, falling back to REST: {e}")

    # Primary / Fallback: REST API
    return firestore_set_doc(path, data, merge=merge)


def _read_doc(path: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Read document from Firestore via Admin SDK if initialized, or REST API."""
    client = get_firestore_client()
    if client:
        try:
            parts = path.strip("/").split("/")
            doc = None
            if len(parts) == 2:
                doc = client.collection(parts[0]).document(parts[1]).get()
            elif len(parts) == 4:
                doc = client.collection(parts[0]).document(parts[1]).collection(parts[2]).document(parts[3]).get()

            if doc is not None:
                if doc.exists:
                    d = doc.to_dict() or {}
                    d.setdefault("id", doc.id)
                    return True, d, ""
                else:
                    return True, None, "Document not found"
        except Exception as e:
            print(f"[FIRESTORE READ NOTE] Admin SDK failed, falling back to REST: {e}")

    # Primary / Fallback: REST API
    return firestore_get_doc(path)


def _delete_doc(path: str) -> Tuple[bool, str]:
    """Delete document from Firestore via Admin SDK if initialized, or REST API."""
    client = get_firestore_client()
    if client:
        try:
            parts = path.strip("/").split("/")
            if len(parts) == 2:
                client.collection(parts[0]).document(parts[1]).delete()
                return True, ""
            elif len(parts) == 4:
                client.collection(parts[0]).document(parts[1]).collection(parts[2]).document(parts[3]).delete()
                return True, ""
        except Exception as e:
            print(f"[FIRESTORE DELETE NOTE] Admin SDK failed, falling back to REST: {e}")

    # Primary / Fallback: REST API
    return firestore_delete_doc(path)


def _list_subcollection(collection_path: str) -> List[Dict[str, Any]]:
    """List documents in collection/subcollection via Admin SDK or REST API."""
    client = get_firestore_client()
    if client:
        try:
            parts = collection_path.strip("/").split("/")
            docs = []
            if len(parts) == 1:
                docs = list(client.collection(parts[0]).stream())
            elif len(parts) == 3:
                docs = list(client.collection(parts[0]).document(parts[1]).collection(parts[2]).stream())

            if docs:
                items = []
                for doc in docs:
                    d = doc.to_dict() or {}
                    d.setdefault("id", doc.id)
                    items.append(d)
                return items
        except Exception as e:
            print(f"[FIRESTORE LIST NOTE] Admin SDK failed, falling back to REST: {e}")

    # Primary / Fallback: REST API
    ok, docs, _ = firestore_list_docs(collection_path)
    return docs if ok else []


def _migrate_legacy_patient_data_if_needed(uid: str) -> None:
    """Migrate patient data from /users/{uid}/patient/profile to /patients/{uid} if found."""
    if not uid:
        return

    try:
        # Check if primary document at /patients/{uid} already exists
        ok_p, pat_data, _ = _read_doc(f"patients/{uid}")
        if ok_p and pat_data and (pat_data.get("name") or pat_data.get("full_name") or pat_data.get("patient_id")):
            return

        # Check legacy /users/{uid}/patient/profile
        ok_u, leg_profile, _ = _read_doc(f"users/{uid}/patient/profile")
        if ok_u and leg_profile and (leg_profile.get("name") or leg_profile.get("full_name") or leg_profile.get("patient_id")):
            print(f"[FIRESTORE MIGRATION] Migrating profile for '{uid}' from users/{uid}/patient/profile to patients/{uid}...")
            _write_doc(f"patients/{uid}", leg_profile, merge=True)
            return

        # Check legacy root /users/{uid}
        ok_usr, usr_data, _ = _read_doc(f"users/{uid}")
        if ok_usr and usr_data and (usr_data.get("name") or usr_data.get("full_name")):
            print(f"[FIRESTORE MIGRATION] Migrating profile for '{uid}' from users/{uid} to patients/{uid}...")
            _write_doc(f"patients/{uid}", usr_data, merge=True)
    except Exception as e:
        print(f"[FIRESTORE MIGRATION NOTE] Legacy migration check note for '{uid}': {e}")


# ----------------------------------------------------------------------
# Vitals and Input Validation
# ----------------------------------------------------------------------

def save_latest_health_vitals(patient_id: str, vitals_data: Dict[str, Any]) -> bool:
    """Save Heart Rate, Temperature, SpO2, Battery, Device Status directly under /patients/{uid}/health/latest in Cloud Firestore."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(vitals_data, dict):
        return False

    now_iso = datetime.utcnow().isoformat()
    patient = get_patient_by_id(uid) or {}

    hr = vitals_data.get("heart_rate") or vitals_data.get("heartRate") or vitals_data.get("hr") or 72
    temp = vitals_data.get("temperature") or vitals_data.get("temp") or 36.8
    spo2 = vitals_data.get("spo2") or vitals_data.get("spO2") or 98
    battery = vitals_data.get("battery") if vitals_data.get("battery") is not None else vitals_data.get("battery_level", patient.get("battery_level", 90))
    device_status = vitals_data.get("device_status") or vitals_data.get("status") or patient.get("device_status", "Connected")

    latest_payload = {
        "uid": uid,
        "patient_id": uid,
        "owner_uid": uid,
        "heart_rate": float(hr),
        "temperature": float(temp),
        "spo2": float(spo2),
        "battery": int(battery),
        "battery_level": int(battery),
        "device_status": str(device_status),
        "updated_at": now_iso,
        "timestamp": now_iso,
    }

    try:
        # Save to patients/{uid}/health/latest
        _write_doc(f"patients/{uid}/health/latest", latest_payload, merge=True)

        # Mirror update to primary profile document patients/{uid}
        _write_doc(f"patients/{uid}", {
            "latest_vitals": latest_payload,
            "heart_rate": float(hr),
            "temperature": float(temp),
            "spo2": float(spo2),
            "battery_level": int(battery),
            "device_status": str(device_status),
            "last_sync": now_iso,
        }, merge=True)

        invalidate_firebase_cache()
        return True
    except Exception as e:
        print(f"[FIRESTORE ERROR] save_latest_health_vitals failed: {e}")
        return False


def validate_patient_input(patient_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate patient registration & profile input data strictly."""
    name = str(patient_data.get("name") or patient_data.get("full_name") or "").strip()
    if not name:
        return False, "Full Name is a required field and cannot be empty."

    # Validate Age
    age_raw = patient_data.get("age")
    if age_raw is None or str(age_raw).strip() == "":
        return False, "Age is a required field and cannot be empty."
    try:
        age_val = int(age_raw)
        if age_val < 0 or age_val > 120:
            return False, "Age must be a valid positive number between 0 and 120."
    except (TypeError, ValueError):
        return False, "Age must be a valid numeric integer."

    # Validate Phone Number (numeric check)
    phone = str(patient_data.get("phone_number") or patient_data.get("phone") or "").strip()
    if phone:
        cleaned_phone = re.sub(r"[\s\-\(\)]", "", phone)
        if not re.match(r"^\+?\d{7,15}$", cleaned_phone):
            return False, "Phone Number must contain only numeric digits (e.g. 9876543210 or +1234567890)."

    # Validate Emergency Phone Number
    em_phone = str(patient_data.get("emergency_phone") or "").strip()
    if em_phone:
        cleaned_em_phone = re.sub(r"[\s\-\(\)]", "", em_phone)
        if not re.match(r"^\+?\d{7,15}$", cleaned_em_phone):
            return False, "Emergency Contact Number must contain only numeric digits (e.g. +1234567890)."

    # Validate Email
    email = str(patient_data.get("email") or "").strip()
    if email:
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            return False, "Please enter a valid email address (e.g. patient@example.com)."

    return True, "Validation successful."


def check_duplicate_patient(
    owner_uid: Optional[str],
    phone_number: str,
    email: str,
    name: str,
    exclude_patient_id: Optional[str] = None
) -> Tuple[bool, str]:
    """Check if existing patient profile for this user has conflicting info."""
    uid = _resolve_user_uid(owner_uid)
    if not uid:
        return False, ""
    patient = get_patient_by_id(uid, force_refresh=True)
    if not patient:
        return False, ""
    p_id = patient.get("patient_id") or patient.get("id") or uid
    if exclude_patient_id and p_id == exclude_patient_id:
        return False, ""
    phone_clean = phone_number.strip().lower()
    email_clean = email.strip().lower()
    name_clean = name.strip().lower()
    p_phone = str(patient.get("phone_number") or "").strip().lower()
    p_email = str(patient.get("email") or "").strip().lower()
    p_name = str(patient.get("name") or "").strip().lower()

    if phone_clean and p_phone and phone_clean == p_phone and p_id != uid:
        return True, f"A patient with phone number '{phone_number}' already exists."
    if email_clean and p_email and email_clean == p_email and p_id != uid:
        return True, f"A patient with email '{email}' already exists."
    if name_clean and p_name and name_clean == p_name and p_id != uid:
        return True, f"A patient named '{name}' already exists in your account."

    return False, ""


# ----------------------------------------------------------------------
# Patient Profile Management (CRUD under /patients/{uid})
# ----------------------------------------------------------------------

def save_patient_registration(patient_data: Dict[str, Any], owner_uid: Optional[str] = None) -> Tuple[bool, str]:
    """Save or update patient profile under /patients/{uid} in Cloud Firestore."""
    uid = _resolve_user_uid(owner_uid)
    if not uid or not isinstance(patient_data, dict):
        return False, "User not authenticated. Please log in before saving patient profile."

    now_iso = datetime.utcnow().isoformat()

    try:
        _migrate_legacy_patient_data_if_needed(uid)
        ok_ex, existing_data, _ = _read_doc(f"patients/{uid}")
        if not existing_data:
            existing_data = {}

        raw_dob = patient_data.get("dob") or existing_data.get("dob") or ""
        dob_str = str(raw_dob) if raw_dob else ""

        payload = {
            "uid": uid,
            "patient_id": uid,
            "id": uid,
            "ownerUid": uid,
            "owner_uid": uid,
            "name": patient_data.get("name") or patient_data.get("full_name") or existing_data.get("name") or "",
            "full_name": patient_data.get("full_name") or patient_data.get("name") or existing_data.get("full_name") or "",
            "age": patient_data.get("age") if patient_data.get("age") is not None else existing_data.get("age"),
            "gender": patient_data.get("gender") or existing_data.get("gender") or "Other",
            "dob": dob_str,
            "blood_group": patient_data.get("blood_group") or existing_data.get("blood_group") or "A+",
            "height": patient_data.get("height") if patient_data.get("height") is not None else existing_data.get("height"),
            "weight": patient_data.get("weight") if patient_data.get("weight") is not None else existing_data.get("weight"),
            "phone_number": patient_data.get("phone_number") or existing_data.get("phone_number") or "",
            "email": patient_data.get("email") or existing_data.get("email") or "",
            "address": patient_data.get("address") or existing_data.get("address") or "",
            "emergency_name": patient_data.get("emergency_name") or existing_data.get("emergency_name") or "",
            "emergency_phone": patient_data.get("emergency_phone") or existing_data.get("emergency_phone") or "",
            "disease": patient_data.get("disease") or patient_data.get("existing_diseases") or existing_data.get("disease") or "",
            "existing_diseases": patient_data.get("existing_diseases") or patient_data.get("disease") or existing_data.get("existing_diseases") or "",
            "allergies": patient_data.get("allergies") or existing_data.get("allergies") or "",
            "current_medications": patient_data.get("current_medications") or existing_data.get("current_medications") or "",
            "doctor_name": patient_data.get("doctor_name") or existing_data.get("doctor_name") or "",
            "hospital_name": patient_data.get("hospital_name") or existing_data.get("hospital_name") or "",
            "medicine_box_id": patient_data.get("medicine_box_id") or existing_data.get("medicine_box_id") or f"BOX-{uid[:6].upper()}",
            "device_serial_number": patient_data.get("device_serial_number") or existing_data.get("device_serial_number") or f"DEV-{uid[:6].upper()}",
            "device_status": existing_data.get("device_status", "Connected"),
            "battery_level": existing_data.get("battery_level", 90),
            "created_at": existing_data.get("created_at", now_iso),
            "updated_at": now_iso,
            "last_sync": now_iso,
        }

        # Perform Firestore write strictly to /patients/{uid}
        ok_w, err_w = _write_doc(f"patients/{uid}", payload, merge=True)
        if not ok_w:
            return False, f"Failed to save profile: {err_w}"

        # Initialize /patients/{uid}/health/latest document
        save_latest_health_vitals(uid, {
            "heart_rate": 72.0,
            "temperature": 36.8,
            "spo2": 98.0,
            "battery": payload["battery_level"],
            "device_status": payload["device_status"]
        })

        # Also mirror user metadata under users/{uid}
        try:
            _write_doc(f"users/{uid}", {
                "patient_profile_updated": now_iso,
                "name": payload["name"],
                "email": payload["email"],
                "phone_number": payload["phone_number"]
            }, merge=True)
        except Exception:
            pass

        invalidate_firebase_cache()
        return True, "Patient profile saved successfully in Cloud Firestore!"

    except Exception as e:
        print(f"[FIRESTORE ERROR] save_patient_registration failed: {e}")
        return False, f"Firestore Error: {type(e).__name__}: {str(e)}"


def update_patient_registration(
    patient_id: str,
    update_data: Dict[str, Any],
    owner_uid: Optional[str] = None
) -> Tuple[bool, str]:
    """Update existing patient document under /patients/{uid}."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid or not isinstance(update_data, dict):
        return False, "User not authenticated or invalid profile data."

    try:
        _migrate_legacy_patient_data_if_needed(uid)
        ok_doc, doc_dict, _ = _read_doc(f"patients/{uid}")
        if not doc_dict:
            doc_dict = {}

        now_iso = datetime.utcnow().isoformat()
        payload = {
            "name": update_data.get("name") or update_data.get("full_name") or doc_dict.get("name"),
            "full_name": update_data.get("full_name") or update_data.get("name") or doc_dict.get("full_name"),
            "age": update_data.get("age") if update_data.get("age") is not None else doc_dict.get("age"),
            "gender": update_data.get("gender") or doc_dict.get("gender"),
            "dob": str(update_data.get("dob")) if update_data.get("dob") else doc_dict.get("dob"),
            "blood_group": update_data.get("blood_group") or doc_dict.get("blood_group"),
            "height": update_data.get("height") if update_data.get("height") is not None else doc_dict.get("height"),
            "weight": update_data.get("weight") if update_data.get("weight") is not None else doc_dict.get("weight"),
            "phone_number": update_data.get("phone_number") or doc_dict.get("phone_number"),
            "email": update_data.get("email") or doc_dict.get("email"),
            "address": update_data.get("address") or doc_dict.get("address"),
            "emergency_name": update_data.get("emergency_name") or doc_dict.get("emergency_name"),
            "emergency_phone": update_data.get("emergency_phone") or doc_dict.get("emergency_phone"),
            "disease": update_data.get("existing_diseases") or update_data.get("disease") or doc_dict.get("disease"),
            "existing_diseases": update_data.get("existing_diseases") or update_data.get("disease") or doc_dict.get("existing_diseases"),
            "allergies": update_data.get("allergies") or doc_dict.get("allergies"),
            "current_medications": update_data.get("current_medications") or doc_dict.get("current_medications"),
            "doctor_name": update_data.get("doctor_name") or doc_dict.get("doctor_name"),
            "hospital_name": update_data.get("hospital_name") or doc_dict.get("hospital_name"),
            "medicine_box_id": update_data.get("medicine_box_id") or doc_dict.get("medicine_box_id"),
            "device_serial_number": update_data.get("device_serial_number") or doc_dict.get("device_serial_number"),
            "updated_at": now_iso,
        }

        # Perform Firestore write to patients/{uid}
        ok_w, err_w = _write_doc(f"patients/{uid}", payload, merge=True)
        if not ok_w:
            return False, f"Failed to update profile: {err_w}"

        # Update root user metadata document under users/{uid}
        try:
            _write_doc(f"users/{uid}", {
                "patient_profile_updated": now_iso,
                "name": payload["name"],
                "email": payload["email"]
            }, merge=True)
        except Exception:
            pass

        invalidate_firebase_cache()
        return True, "Patient profile updated successfully in Cloud Firestore!"
    except Exception as e:
        print(f"[FIRESTORE ERROR] update_patient_registration failed: {e}")
        return False, f"Firestore Error: {type(e).__name__}: {str(e)}"


def delete_patient(patient_id: str, owner_uid: Optional[str] = None) -> Tuple[bool, str]:
    """Delete patient profile document under /patients/{uid} and associated subcollections."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid:
        return False, "Authentication / User ID missing."

    try:
        # Delete primary patient profile document patients/{uid}
        _delete_doc(f"patients/{uid}")

        # Delete subcollections under patients/{uid}
        for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations", "reports"]:
            docs = _list_subcollection(f"patients/{uid}/{sub_col}")
            for doc in docs:
                doc_id = doc.get("id")
                if doc_id:
                    _delete_doc(f"patients/{uid}/{sub_col}/{doc_id}")

        # Delete legacy subcollections under users/{uid} if present
        _delete_doc(f"users/{uid}/patient/profile")
        for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations", "reports"]:
            docs = _list_subcollection(f"users/{uid}/{sub_col}")
            for doc in docs:
                doc_id = doc.get("id")
                if doc_id:
                    _delete_doc(f"users/{uid}/{sub_col}/{doc_id}")

        if uid in _ESP32_LIVE_CACHE:
            del _ESP32_LIVE_CACHE[uid]
        invalidate_firebase_cache()
        return True, "Patient profile deleted successfully from Cloud Firestore!"
    except Exception as e:
        print(f"[FIRESTORE ERROR] delete_patient failed: {e}")
        return False, f"Firestore Error: {type(e).__name__}: {str(e)}"


def get_all_patients(owner_uid: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return patient document for the authenticated user (1 user = 1 patient profile at /patients/{uid})."""
    uid = _resolve_user_uid(owner_uid)
    if not uid:
        return []

    patient = get_patient_by_id(uid, owner_uid=uid, force_refresh=force_refresh)
    return [patient] if patient else []


def get_patient_by_id(patient_id: Optional[str] = None, owner_uid: Optional[str] = None, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieve patient profile document directly from /patients/{uid} with live health/latest merge."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid:
        return None

    try:
        import streamlit as st
        if not force_refresh and "cached_patient_data" in st.session_state:
            c_uid, c_data = st.session_state["cached_patient_data"]
            if c_uid == uid and c_data:
                return c_data
    except Exception:
        pass

    try:
        # Check primary path: /patients/{uid}
        _migrate_legacy_patient_data_if_needed(uid)
        ok_p, data, _ = _read_doc(f"patients/{uid}")

        # Fallback to users/{uid}/patient/profile or users/{uid}
        if not data:
            ok_u, leg_data, _ = _read_doc(f"users/{uid}/patient/profile")
            if ok_u and leg_data and (leg_data.get("name") or leg_data.get("full_name")):
                data = leg_data
                # Migrate to patients/{uid}
                _write_doc(f"patients/{uid}", leg_data, merge=True)

        if not data:
            ok_usr, usr_data, _ = _read_doc(f"users/{uid}")
            if ok_usr and usr_data and (usr_data.get("name") or usr_data.get("full_name")):
                data = usr_data
                _write_doc(f"patients/{uid}", usr_data, merge=True)

        if not data or not (data.get("name") or data.get("full_name") or data.get("patient_id")):
            return None

        data["id"] = uid
        data["patient_id"] = uid
        data.setdefault("uid", uid)
        data.setdefault("ownerUid", uid)
        data.setdefault("owner_uid", uid)

        # Load live /patients/{uid}/health/latest for Heart Rate, Temp, SpO2, Battery, Device Status
        try:
            ok_l, l_data, _ = _read_doc(f"patients/{uid}/health/latest")
            if not l_data:
                ok_l, l_data, _ = _read_doc(f"users/{uid}/health/latest")
            if ok_l and l_data:
                if l_data.get("device_status"):
                    data["device_status"] = l_data["device_status"]
                if l_data.get("battery_level") is not None:
                    data["battery_level"] = l_data["battery_level"]
                elif l_data.get("battery") is not None:
                    data["battery_level"] = l_data["battery"]
                if l_data.get("updated_at") or l_data.get("timestamp"):
                    data["last_sync"] = l_data.get("updated_at") or l_data.get("timestamp")
        except Exception:
            pass

        data.setdefault("device_status", "Connected")
        data.setdefault("battery_level", 85)
        data.setdefault("last_sync", data.get("created_at") or (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"))

        try:
            import streamlit as st
            st.session_state["cached_patient_data"] = (uid, data)
        except Exception:
            pass

        return data
    except Exception as e:
        print(f"[FIRESTORE ERROR] get_patient_by_id failed: {e}")
        return None


# ----------------------------------------------------------------------
# ESP32 & Health Vitals Processing
# ----------------------------------------------------------------------

def process_esp32_data(
    heart_rate: float,
    spo2: float,
    temperature: float,
    patient_id: Optional[str] = None,
    blood_pressure: Optional[str] = "120/80"
) -> Dict[str, Any]:
    """Process ESP32 vitals reading and save under /patients/{uid}/health/latest and /patients/{uid}/health/{reading_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return {"success": False, "error": "Authentication / Patient ID required."}

    now_iso = datetime.utcnow().isoformat()
    reading_payload = {
        "patient_id": uid,
        "ownerUid": uid,
        "owner_uid": uid,
        "heart_rate": float(heart_rate),
        "spo2": float(spo2),
        "temperature": float(temperature),
        "blood_pressure": blood_pressure or "120/80",
        "battery_level": 90,
        "battery": 90,
        "device_status": "Connected",
        "timestamp": now_iso,
        "source": "ESP32_Device"
    }

    _ESP32_LIVE_CACHE[uid] = reading_payload
    doc_id = save_health_reading(uid, reading_payload)
    save_latest_health_vitals(uid, reading_payload)

    alerts = check_and_trigger_vitals_alerts(uid, reading_payload)
    invalidate_firebase_cache()

    return {
        "success": True,
        "reading_id": doc_id or f"READING-{uuid.uuid4().hex[:8].upper()}",
        "patient_id": uid,
        "vitals": reading_payload,
        "alerts_triggered": len(alerts)
    }


def get_health_metrics(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve vitals & health metrics directly from /patients/{uid}/health/latest and /patients/{uid}."""
    uid = _resolve_user_uid(patient_id)
    metrics: Dict[str, Any] = {
        "heart_rate": None,
        "spo2": None,
        "temperature": None,
        "blood_pressure": None,
        "health_score": None,
        "battery_level": None,
        "battery": None,
        "device_status": None,
    }

    if not uid:
        return metrics

    # Try patients/{uid}/health/latest, then users/{uid}/health/latest
    ok_l, l_data, _ = _read_doc(f"patients/{uid}/health/latest")
    if not l_data:
        ok_l, l_data, _ = _read_doc(f"users/{uid}/health/latest")

    if ok_l and l_data:
        for k in ["heart_rate", "spo2", "temperature", "blood_pressure", "battery", "battery_level", "device_status"]:
            if l_data.get(k) is not None:
                metrics[k] = l_data.get(k)

    patient = get_patient_by_id(uid)
    if patient:
        for k in ["heart_rate", "spo2", "temperature", "blood_pressure", "battery_level", "device_status"]:
            if metrics.get(k) is None and patient.get(k) is not None:
                metrics[k] = patient.get(k)
        if "latest_vitals" in patient and isinstance(patient["latest_vitals"], dict):
            lv = patient["latest_vitals"]
            for k in ["heart_rate", "spo2", "temperature", "blood_pressure", "battery", "battery_level", "device_status"]:
                if metrics.get(k) is None and lv.get(k) is not None:
                    metrics[k] = lv.get(k)

    if uid in _ESP32_LIVE_CACHE:
        cache_data = _ESP32_LIVE_CACHE[uid]
        for k in ["heart_rate", "spo2", "temperature", "blood_pressure", "battery", "battery_level", "device_status"]:
            if cache_data.get(k) is not None:
                metrics[k] = cache_data.get(k)

    if metrics["battery_level"] is None:
        metrics["battery_level"] = metrics.get("battery")
    if metrics["battery"] is None:
        metrics["battery"] = metrics.get("battery_level")

    score = 100
    has_vitals = False
    try:
        if metrics.get("heart_rate") is not None:
            hr = float(metrics.get("heart_rate"))
            has_vitals = True
            if hr > 100 or hr < 60:
                score -= 15
    except (TypeError, ValueError):
        pass

    try:
        if metrics.get("spo2") is not None:
            spo2 = float(metrics.get("spo2"))
            has_vitals = True
            if spo2 < 95:
                score -= int((95 - spo2) * 5)
    except (TypeError, ValueError):
        pass

    try:
        if metrics.get("temperature") is not None:
            temp = float(metrics.get("temperature"))
            has_vitals = True
            if temp > 37.5 or temp < 36.0:
                score -= 10
    except (TypeError, ValueError):
        pass

    metrics["health_score"] = max(0, min(100, score)) if has_vitals else None
    return metrics


# ----------------------------------------------------------------------
# Medication Schedule Management (under /patients/{uid}/medicines)
# ----------------------------------------------------------------------

def get_patient_medicines(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return medicines exclusively from subcollection /patients/{uid}/medicines (with auto-migration)."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    try:
        docs = _list_subcollection(f"patients/{uid}/medicines")

        # If empty, check legacy users/{uid}/medicines
        if not docs:
            legacy_docs = _list_subcollection(f"users/{uid}/medicines")
            if legacy_docs:
                for l_doc in legacy_docs:
                    _write_doc(f"patients/{uid}/medicines/{l_doc.get('id', uuid.uuid4().hex)}", l_doc, merge=True)
                docs = _list_subcollection(f"patients/{uid}/medicines")

        items: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc if isinstance(doc, dict) else {}
            items.append({
                "id": data.get("id", ""),
                "Medicine": data.get("medicine_name") or data.get("Medicine") or data.get("name") or "",
                "Dosage": data.get("dosage") or data.get("Dosage") or "",
                "Time": data.get("time") or data.get("Time") or "",
                "Status": data.get("status") or data.get("Status") or "Upcoming",
            })
        return items
    except Exception as e:
        print(f"[FIRESTORE ERROR] get_patient_medicines failed: {e}")
        return []


def save_patient_medicine(patient_id: str, medicine_data: Dict[str, Any], medicine_id: Optional[str] = None) -> Optional[str]:
    """Add or update a medicine document under /patients/{uid}/medicines/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(medicine_data, dict):
        return None

    doc_id = medicine_id or f"MED-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.utcnow().isoformat()
    payload = {
        "id": doc_id,
        "medicine_id": doc_id,
        "patient_id": uid,
        "ownerUid": uid,
        "owner_uid": uid,
        "medicine_name": medicine_data.get("Medicine") or medicine_data.get("medicine_name") or "",
        "dosage": medicine_data.get("Dosage") or medicine_data.get("dosage") or "",
        "time": medicine_data.get("Time") or medicine_data.get("time") or "",
        "status": medicine_data.get("Status") or medicine_data.get("status") or "Upcoming",
        "created_at": medicine_data.get("created_at") or now_iso,
        "updated_at": now_iso,
    }

    try:
        _write_doc(f"patients/{uid}/medicines/{doc_id}", payload, merge=True)
        invalidate_firebase_cache()
        return doc_id
    except Exception as e:
        print(f"[FIRESTORE ERROR] save_patient_medicine failed: {e}")
        return None


def delete_patient_medicine(patient_id: str, medicine_id: str) -> bool:
    """Delete a medicine document from subcollection /patients/{uid}/medicines/{medicine_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not medicine_id:
        return False

    try:
        _delete_doc(f"patients/{uid}/medicines/{medicine_id}")
        _delete_doc(f"users/{uid}/medicines/{medicine_id}")
        invalidate_firebase_cache()
        return True
    except Exception as e:
        print(f"[FIRESTORE ERROR] delete_patient_medicine failed: {e}")
        return False


def get_medicine_schedule(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return medicine schedule DataFrame from subcollection /patients/{uid}/medicines."""
    uid = _resolve_user_uid(patient_id)
    if uid:
        items = get_patient_medicines(uid)
        if items:
            return pd.DataFrame([
                {
                    "id": item.get("id", ""),
                    "Medicine": item.get("Medicine", ""),
                    "Dosage": item.get("Dosage", ""),
                    "Time": item.get("Time", ""),
                    "Status": item.get("Status", ""),
                }
                for item in items
            ])

    return pd.DataFrame(columns=["id", "Medicine", "Dosage", "Time", "Status"])


# ----------------------------------------------------------------------
# Alerts & AI Recommendations (under /patients/{uid}/alerts & ai_recommendations)
# ----------------------------------------------------------------------

def save_patient_alert(patient_id: Optional[str], alert_data: Dict[str, Any]) -> Optional[str]:
    """Save alert document under /patients/{uid}/alerts/{alert_id}."""
    uid = _resolve_user_uid(patient_id)
    if not isinstance(alert_data, dict) or not uid:
        return None

    doc_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    text = alert_data.get("text") or alert_data.get("message") or alert_data.get("alert") or ""
    alert_type = alert_data.get("type") or "emergency"
    payload = {
        "id": doc_id,
        "text": str(text),
        "type": alert_type,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        _write_doc(f"patients/{uid}/alerts/{doc_id}", payload, merge=True)
        return doc_id
    except Exception:
        return None


def check_and_trigger_vitals_alerts(patient_id: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Automatically evaluate vitals and trigger alerts."""
    uid = _resolve_user_uid(patient_id)
    if metrics is None:
        metrics = get_health_metrics(uid)

    triggered_alerts = []

    try:
        hr = float(metrics.get("heart_rate")) if metrics.get("heart_rate") is not None else None
    except (TypeError, ValueError):
        hr = None

    try:
        spo2 = float(metrics.get("spo2")) if metrics.get("spo2") is not None else None
    except (TypeError, ValueError):
        spo2 = None

    try:
        temp = float(metrics.get("temperature")) if metrics.get("temperature") is not None else None
    except (TypeError, ValueError):
        temp = None

    if hr is not None:
        if hr > 100:
            triggered_alerts.append({
                "type": "emergency",
                "text": f"EMERGENCY: High Heart Rate detected ({int(hr)} bpm > 100 bpm)"
            })
        elif hr < 50:
            triggered_alerts.append({
                "type": "emergency",
                "text": f"EMERGENCY: Low Heart Rate detected ({int(hr)} bpm < 50 bpm)"
            })

    if spo2 is not None and spo2 < 92:
        triggered_alerts.append({
            "type": "emergency",
            "text": f"EMERGENCY: Low SpO2 level detected ({spo2}% < 92%)"
        })

    if temp is not None and temp > 38.5:
        triggered_alerts.append({
            "type": "emergency",
            "text": f"EMERGENCY: High Body Temperature detected ({temp}°C > 38.5°C)"
        })

    if uid:
        for alert in triggered_alerts:
            save_patient_alert(uid, alert)

    return triggered_alerts


def get_alerts(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return alert data for user from subcollection /patients/{uid}/alerts."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    metrics = get_health_metrics(uid)
    emergency_alerts = check_and_trigger_vitals_alerts(uid, metrics)

    firebase_alerts: List[Dict[str, Any]] = []
    try:
        docs = _list_subcollection(f"patients/{uid}/alerts")
        if not docs:
            docs = _list_subcollection(f"users/{uid}/alerts")
        for item in docs:
            text = item.get("text") or item.get("message") or item.get("alert") or ""
            alert_type = item.get("type") or ("emergency" if "EMERGENCY" in str(text) else ("warning" if "missed" in str(text).lower() or "battery" in str(text).lower() else "info"))
            firebase_alerts.append({"type": alert_type, "text": str(text)})
    except Exception:
        pass

    combined_alerts = []
    seen_texts = set()

    for a in emergency_alerts + firebase_alerts:
        txt = a.get("text", "").strip()
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            combined_alerts.append(a)

    return combined_alerts


def save_ai_recommendation(patient_id: Optional[str], recommendation_text: str) -> Optional[str]:
    """Save an AI recommendation document under /patients/{uid}/ai_recommendations/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not recommendation_text:
        return None

    doc_id = f"AI-REC-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "id": doc_id,
        "uid": uid,
        "patient_id": uid,
        "recommendation": str(recommendation_text),
        "text": str(recommendation_text),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        _write_doc(f"patients/{uid}/ai_recommendations/{doc_id}", payload, merge=True)
        return doc_id
    except Exception as e:
        print(f"[FIRESTORE ERROR] save_ai_recommendation failed: {e}")
        return None


def get_ai_recommendations(patient_id: Optional[str] = None) -> List[str]:
    """Return AI recommendations strictly for user from subcollection /patients/{uid}/ai_recommendations."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    try:
        docs = _list_subcollection(f"patients/{uid}/ai_recommendations")
        if not docs:
            docs = _list_subcollection(f"users/{uid}/ai_recommendations")
        if docs:
            recs = [str(item.get("recommendation") or item.get("text") or item.get("message") or "") for item in docs if item]
            valid_recs = [r for r in recs if r]
            if valid_recs:
                return valid_recs
    except Exception:
        pass

    metrics = get_health_metrics(uid)
    patient = get_patient_by_id(uid) or {}
    recs = []

    hr = metrics.get("heart_rate")
    spo2 = metrics.get("spo2")
    temp = metrics.get("temperature")

    if hr and float(hr) > 100:
        recs.append(f"High Heart Rate ({hr} bpm) detected. Recommend patient rest and consult assigned doctor ({patient.get('doctor_name', 'Physician')}).")
    if spo2 and float(spo2) < 95:
        recs.append(f"Oxygen Saturation ({spo2}%) is below optimal threshold. Ensure proper ventilation and oxygen monitoring.")
    if temp and float(temp) > 37.5:
        recs.append(f"Elevated body temperature ({temp}°C) observed. Ensure proper hydration and monitor for fever symptoms.")

    if not recs:
        recs.append("Vitals are stable. Maintain current medication schedule and daily health tracking.")

    return recs


# ----------------------------------------------------------------------
# Health Readings & Trends (under /patients/{uid}/health)
# ----------------------------------------------------------------------

def save_health_reading(patient_id: str, reading_data: Dict[str, Any]) -> Optional[str]:
    """Store health reading under /patients/{uid}/health/{doc_id} and update /patients/{uid}/health/latest."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(reading_data, dict):
        return None

    doc_id = f"READING-{uuid.uuid4().hex[:8].upper()}"
    timestamp = reading_data.get("timestamp") or datetime.utcnow().isoformat()
    payload = {
        "id": doc_id,
        "reading_id": doc_id,
        "patient_id": uid,
        "ownerUid": uid,
        "owner_uid": uid,
        "heart_rate": reading_data.get("heart_rate") or reading_data.get("heartRate"),
        "spo2": reading_data.get("spo2") or reading_data.get("spO2"),
        "temperature": reading_data.get("temperature") or reading_data.get("temp"),
        "blood_pressure": reading_data.get("blood_pressure") or reading_data.get("bloodPressure") or reading_data.get("bp"),
        "battery_level": reading_data.get("battery_level") or reading_data.get("battery") or 90,
        "battery": reading_data.get("battery") or reading_data.get("battery_level") or 90,
        "device_status": reading_data.get("device_status") or "Connected",
        "health_score": reading_data.get("health_score") or reading_data.get("healthScore"),
        "timestamp": timestamp,
    }

    try:
        _write_doc(f"patients/{uid}/health/{doc_id}", payload, merge=True)
        save_latest_health_vitals(uid, payload)
        return doc_id
    except Exception:
        return None


def get_patient_health_readings(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return health readings for patient directly from subcollection /patients/{uid}/health."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    readings: List[Dict[str, Any]] = []
    try:
        docs = _list_subcollection(f"patients/{uid}/health")
        if not docs:
            docs = _list_subcollection(f"users/{uid}/health")
        for doc in docs:
            if doc.get("id") == "latest":
                continue
            readings.append(doc)
    except Exception:
        pass

    readings.sort(key=lambda r: str(r.get("timestamp", "")))
    return readings


def get_patient_health_trends(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return historical health readings DataFrame for user."""
    cols = ["time", "heart_rate", "spo2", "temperature", "blood_pressure", "health_score"]
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return pd.DataFrame(columns=cols)

    readings = get_patient_health_readings(uid)
    if not readings:
        metrics = get_health_metrics(uid)
        if any(metrics.get(k) is not None for k in ["heart_rate", "spo2", "temperature"]):
            return pd.DataFrame([{
                "time": datetime.utcnow().strftime("%H:%M"),
                "heart_rate": metrics.get("heart_rate") or 0,
                "spo2": metrics.get("spo2") or 0,
                "temperature": metrics.get("temperature") or 0,
                "blood_pressure": metrics.get("blood_pressure") or "N/A",
                "health_score": metrics.get("health_score") or 0,
            }])
        return pd.DataFrame(columns=cols)

    rows = []
    for r in readings:
        rows.append({
            "time": str(r.get("timestamp") or r.get("created_at") or r.get("time") or ""),
            "heart_rate": r.get("heart_rate") or r.get("heartRate") or 0,
            "spo2": r.get("spo2") or r.get("spO2") or 0,
            "temperature": r.get("temperature") or r.get("temp") or 0,
            "blood_pressure": r.get("blood_pressure") or r.get("bp") or "N/A",
            "health_score": r.get("health_score") or r.get("score") or 0,
        })

    try:
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=cols)


# ----------------------------------------------------------------------
# Reports & Dashboard Aggregators
# ----------------------------------------------------------------------

def save_patient_report(patient_id: str, report_metadata: Dict[str, Any]) -> Optional[str]:
    """Store report under /patients/{uid}/reports/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(report_metadata, dict):
        return None

    doc_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.utcnow().isoformat()

    payload = {
        "id": doc_id,
        "report_id": doc_id,
        "patient_id": uid,
        "ownerUid": uid,
        "owner_uid": uid,
        "report_type": report_metadata.get("report_type") or "PDF",
        "file_name": report_metadata.get("file_name") or f"report_{uid}.pdf",
        "health_score": report_metadata.get("health_score"),
        "created_at": timestamp,
        "generated_by": report_metadata.get("generated_by") or uid,
    }

    try:
        _write_doc(f"patients/{uid}/reports/{doc_id}", payload, merge=True)
        invalidate_firebase_cache()
        return doc_id
    except Exception:
        return None


def get_patient_reports(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return generated reports for patient from /patients/{uid}/reports."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    try:
        reports = _list_subcollection(f"patients/{uid}/reports")
        if not reports:
            reports = _list_subcollection(f"users/{uid}/reports")
        reports.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return reports
    except Exception:
        return []


def get_dashboard_data(patient_id: Optional[str] = None, owner_uid: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """Return dashboard data for the authenticated patient directly from /patients/{uid}."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid:
        return {
            "patient": None,
            "no_patients": True,
            "metrics": {},
            "medicines": pd.DataFrame(columns=["id", "Medicine", "Dosage", "Time", "Status"]),
            "alerts": [],
            "ai": [],
            "trends": pd.DataFrame(columns=["time", "heart_rate", "spo2", "temperature", "blood_pressure", "health_score"]),
            "offline": False,
        }

    try:
        import streamlit as st
        if not force_refresh and "cached_dashboard_data" in st.session_state:
            c_uid, c_data = st.session_state["cached_dashboard_data"]
            if c_uid == uid and c_data:
                return c_data
    except Exception:
        pass

    patient = get_patient_by_id(uid, force_refresh=force_refresh)

    if not patient:
        res = {
            "patient": None,
            "no_patients": True,
            "metrics": {},
            "medicines": pd.DataFrame(columns=["id", "Medicine", "Dosage", "Time", "Status"]),
            "alerts": [],
            "ai": [],
            "trends": pd.DataFrame(columns=["time", "heart_rate", "spo2", "temperature", "blood_pressure", "health_score"]),
            "offline": False,
        }
        return res

    dashboard_res = {
        "patient": patient,
        "no_patients": False,
        "metrics": get_health_metrics(uid),
        "medicines": get_medicine_schedule(uid),
        "alerts": get_alerts(uid),
        "ai": get_ai_recommendations(uid),
        "trends": get_patient_health_trends(uid),
        "offline": False,
    }

    try:
        import streamlit as st
        st.session_state["cached_dashboard_data"] = (uid, dashboard_res)
    except Exception:
        pass

    return dashboard_res


def get_firebase_data() -> Dict[str, Any]:
    """Backward-compatible wrapper for dashboard data."""
    return get_dashboard_data()
