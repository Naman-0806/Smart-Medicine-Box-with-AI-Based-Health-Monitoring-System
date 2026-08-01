import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from firebase.config import get_firestore_client

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
    """Helper to resolve the current user's Firebase UID consistently."""
    if uid and str(uid).strip():
        return str(uid).strip()
    try:
        import streamlit as st
        resolved = st.session_state.get("user_uid") or st.session_state.get("owner_uid") or st.session_state.get("selected_patient_id")
        if resolved:
            return str(resolved).strip()
    except Exception:
        pass
    return None


def _migrate_legacy_patient_data_if_needed(client: Any, uid: str) -> None:
    """Automatically migrate patient data from /patients/{uid} to /users/{uid}/patient/profile if found."""
    if not client or not uid:
        return

    try:
        profile_ref = client.collection("users").document(uid).collection("patient").document("profile")
        profile_doc = profile_ref.get()

        # If profile document already exists, no migration needed
        if profile_doc.exists:
            return

        # Check for legacy document in /patients/{uid}
        legacy_pat_ref = client.collection("patients").document(uid)
        legacy_pat_doc = legacy_pat_ref.get()

        legacy_user_ref = client.collection("users").document(uid)
        legacy_user_doc = legacy_user_ref.get()

        legacy_data = {}
        if legacy_pat_doc.exists:
            legacy_data = legacy_pat_doc.to_dict() or {}
        elif legacy_user_doc.exists:
            legacy_data = legacy_user_doc.to_dict() or {}

        # If legacy data is found, migrate to users/{uid}/patient/profile
        if legacy_data and (legacy_data.get("name") or legacy_data.get("full_name") or legacy_data.get("patient_id")):
            print(f"[FIRESTORE MIGRATION] Migrating patient profile for '{uid}' to /users/{uid}/patient/profile...")
            profile_ref.set(legacy_data, merge=True)

            # Migrate any subcollections from /patients/{uid} to /users/{uid}
            if legacy_pat_doc.exists:
                for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations", "reports"]:
                    try:
                        sub_docs = list(legacy_pat_ref.collection(sub_col).stream())
                        for s_doc in sub_docs:
                            s_data = s_doc.to_dict() or {}
                            target_ref = client.collection("users").document(uid).collection(sub_col).document(s_doc.id)
                            if not target_ref.get().exists:
                                target_ref.set(s_data, merge=True)
                            s_doc.reference.delete()
                    except Exception as e_sub:
                        print(f"[FIRESTORE MIGRATION WARNING] Subcollection '{sub_col}' migration note: {e_sub}")

                # Clean up legacy patients/{uid} document after migration
                try:
                    legacy_pat_ref.delete()
                except Exception:
                    pass

            print(f"[FIRESTORE MIGRATION] Successfully migrated patient profile for '{uid}' to /users/{uid}/patient/profile.")
    except Exception as e:
        print(f"[FIRESTORE MIGRATION ERROR] Automatic migration failed for '{uid}': {e}")


def save_latest_health_vitals(patient_id: str, vitals_data: Dict[str, Any]) -> bool:
    """Save Heart Rate, Temperature, SpO2, Battery, Device Status directly under /users/{uid}/health/latest in Cloud Firestore."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(vitals_data, dict):
        return False

    client = get_firestore_client()
    if client is None:
        print("[FIRESTORE ERROR] save_latest_health_vitals failed: Firestore client not initialized.")
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
        latest_ref = client.collection("users").document(uid).collection("health").document("latest")
        latest_ref.set(latest_payload, merge=True)

        # Mirror update to profile document
        client.collection("users").document(uid).collection("patient").document("profile").set({
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


def save_patient_registration(patient_data: Dict[str, Any], owner_uid: Optional[str] = None) -> Tuple[bool, str]:
    """Save or update patient profile under /users/{uid}/patient/profile in Cloud Firestore."""
    uid = _resolve_user_uid(owner_uid)
    if not uid or not isinstance(patient_data, dict):
        return False, "Invalid authentication or patient data."

    client = get_firestore_client()
    if client is None:
        err_msg = "Firestore client could not be initialized. Please check FIREBASE_SERVICE_ACCOUNT_PATH."
        print(f"[FIRESTORE ERROR] {err_msg}")
        return False, err_msg

    now_iso = datetime.utcnow().isoformat()
    profile_ref = client.collection("users").document(uid).collection("patient").document("profile")

    try:
        _migrate_legacy_patient_data_if_needed(client, uid)
        existing_doc = profile_ref.get()
        existing_data = existing_doc.to_dict() if (existing_doc and existing_doc.exists) else {}

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
            "doctor_name": patient_data.get("doctor_name") or existing_data.get("doctor_name") or "Dr. Assigned",
            "hospital_name": patient_data.get("hospital_name") or existing_data.get("hospital_name") or "",
            "medicine_box_id": patient_data.get("medicine_box_id") or existing_data.get("medicine_box_id") or f"BOX-{uid[:6].upper()}",
            "device_serial_number": patient_data.get("device_serial_number") or existing_data.get("device_serial_number") or f"DEV-{uid[:6].upper()}",
            "device_status": existing_data.get("device_status", "Connected"),
            "battery_level": existing_data.get("battery_level", 90),
            "created_at": existing_data.get("created_at", now_iso),
            "updated_at": now_iso,
            "last_sync": now_iso,
        }

        # Perform Firestore write strictly to users/{uid}/patient/profile
        profile_ref.set(payload, merge=True)

        # Initialize users/{uid}/health/latest document
        save_latest_health_vitals(uid, {
            "heart_rate": 72.0,
            "temperature": 36.8,
            "spo2": 98.0,
            "battery": payload["battery_level"],
            "device_status": payload["device_status"]
        })

        # Update root user metadata document under users/{uid}
        try:
            client.collection("users").document(uid).set({
                "patient_profile_updated": now_iso,
                "name": payload["name"],
                "email": payload["email"],
                "phone_number": payload["phone_number"]
            }, merge=True)
        except Exception:
            pass

        # Clean up legacy patients/{uid} document if present
        try:
            legacy_ref = client.collection("patients").document(uid)
            if legacy_ref.get().exists:
                legacy_ref.delete()
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
    """Update existing patient document under /users/{uid}/patient/profile."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid or not isinstance(update_data, dict):
        return False, "Invalid patient ID or profile data."

    client = get_firestore_client()
    if client is None:
        err_msg = "Firestore client could not be initialized. Check FIREBASE_SERVICE_ACCOUNT_PATH."
        print(f"[FIRESTORE ERROR] {err_msg}")
        return False, err_msg

    try:
        _migrate_legacy_patient_data_if_needed(client, uid)
        profile_ref = client.collection("users").document(uid).collection("patient").document("profile")
        doc = profile_ref.get()

        doc_dict = doc.to_dict() if doc.exists else {}
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
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Perform Firestore write to users/{uid}/patient/profile
        profile_ref.set(payload, merge=True)

        # Update root user metadata document under users/{uid}
        try:
            client.collection("users").document(uid).set({
                "patient_profile_updated": datetime.utcnow().isoformat(),
                "name": payload["name"],
                "email": payload["email"]
            }, merge=True)
        except Exception:
            pass

        # Clean up legacy patients/{uid} document if present
        try:
            legacy_ref = client.collection("patients").document(uid)
            if legacy_ref.get().exists:
                legacy_ref.delete()
        except Exception:
            pass

        invalidate_firebase_cache()
        return True, "Patient profile updated successfully in Cloud Firestore!"
    except Exception as e:
        print(f"[FIRESTORE ERROR] update_patient_registration failed: {e}")
        return False, f"Firestore Error: {type(e).__name__}: {str(e)}"


def delete_patient(patient_id: str, owner_uid: Optional[str] = None) -> Tuple[bool, str]:
    """Delete patient profile document under /users/{uid}/patient/profile and associated user data."""
    uid = _resolve_user_uid(patient_id or owner_uid)
    if not uid:
        return False, "Authentication / User ID missing."

    client = get_firestore_client()
    if client is None:
        return False, "Firestore client not initialized."

    try:
        # Delete profile document users/{uid}/patient/profile
        prof_ref = client.collection("users").document(uid).collection("patient").document("profile")
        if prof_ref.get().exists:
            prof_ref.delete()

        # Delete subcollections under users/{uid}
        u_ref = client.collection("users").document(uid)
        for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations", "reports", "patient"]:
            try:
                sub_docs = list(u_ref.collection(sub_col).stream())
                for s_doc in sub_docs:
                    s_doc.reference.delete()
            except Exception:
                pass

        # Clean up legacy patients/{uid} and subcollections if present
        p_ref = client.collection("patients").document(uid)
        if p_ref.get().exists:
            for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations", "reports"]:
                try:
                    sub_docs = list(p_ref.collection(sub_col).stream())
                    for s_doc in sub_docs:
                        s_doc.reference.delete()
                except Exception:
                    pass
            p_ref.delete()

        if uid in _ESP32_LIVE_CACHE:
            del _ESP32_LIVE_CACHE[uid]
        invalidate_firebase_cache()
        return True, "Patient profile deleted successfully from Cloud Firestore!"
    except Exception as e:
        print(f"[FIRESTORE ERROR] delete_patient failed: {e}")
        return False, f"Firestore Error: {type(e).__name__}: {str(e)}"


def get_all_patients(owner_uid: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return patient document for the authenticated user (1 user = 1 patient profile at /users/{uid}/patient/profile)."""
    uid = _resolve_user_uid(owner_uid)
    if not uid:
        return []

    patient = get_patient_by_id(uid, owner_uid=uid, force_refresh=force_refresh)
    return [patient] if patient else []


def get_patient_by_id(patient_id: Optional[str] = None, owner_uid: Optional[str] = None, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieve patient profile document directly from /users/{uid}/patient/profile with live /users/{uid}/health/latest merge."""
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

    client = get_firestore_client()
    if client is None:
        return None

    try:
        # Perform automatic legacy migration if data exists under /patients/{uid}
        _migrate_legacy_patient_data_if_needed(client, uid)

        # Primary path: users/{uid}/patient/profile
        doc = client.collection("users").document(uid).collection("patient").document("profile").get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = uid
        data["patient_id"] = uid
        data.setdefault("uid", uid)
        data.setdefault("ownerUid", uid)
        data.setdefault("owner_uid", uid)

        # Load live /users/{uid}/health/latest for Heart Rate, Temp, SpO2, Battery, Device Status
        try:
            latest_doc = client.collection("users").document(uid).collection("health").document("latest").get()
            if latest_doc.exists:
                l_data = latest_doc.to_dict() or {}
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


def process_esp32_data(
    heart_rate: float,
    spo2: float,
    temperature: float,
    patient_id: Optional[str] = None,
    blood_pressure: Optional[str] = "120/80"
) -> Dict[str, Any]:
    """Process ESP32 vitals reading and save under /users/{uid}/health/latest and /users/{uid}/health/{reading_id}."""
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
    """Retrieve vitals & health metrics directly from /users/{uid}/health/latest and /users/{uid}/patient/profile."""
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

    client = get_firestore_client()
    if client:
        try:
            latest_doc = client.collection("users").document(uid).collection("health").document("latest").get()
            if latest_doc.exists:
                l_data = latest_doc.to_dict() or {}
                for k in ["heart_rate", "spo2", "temperature", "blood_pressure", "battery", "battery_level", "device_status"]:
                    if l_data.get(k) is not None:
                        metrics[k] = l_data.get(k)
        except Exception:
            pass

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

    # Defaults if still None
    if metrics["heart_rate"] is None:
        metrics["heart_rate"] = 72.0
    if metrics["spo2"] is None:
        metrics["spo2"] = 98.0
    if metrics["temperature"] is None:
        metrics["temperature"] = 36.8
    if metrics["blood_pressure"] is None:
        metrics["blood_pressure"] = "120/80"
    if metrics["battery_level"] is None:
        metrics["battery_level"] = metrics.get("battery") or 90
    if metrics["battery"] is None:
        metrics["battery"] = metrics.get("battery_level") or 90
    if metrics["device_status"] is None:
        metrics["device_status"] = "Connected"

    score = 100
    try:
        hr = float(metrics.get("heart_rate"))
        if hr > 100 or hr < 60:
            score -= 15
    except (TypeError, ValueError):
        pass

    try:
        spo2 = float(metrics.get("spo2"))
        if spo2 < 95:
            score -= int((95 - spo2) * 5)
    except (TypeError, ValueError):
        pass

    try:
        temp = float(metrics.get("temperature"))
        if temp > 37.5 or temp < 36.0:
            score -= 10
    except (TypeError, ValueError):
        pass

    metrics["health_score"] = max(0, min(100, score))
    return metrics


def get_patient_medicines(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return medicines exclusively from subcollection /users/{uid}/medicines (with auto-migration)."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    try:
        meds_ref = client.collection("users").document(uid).collection("medicines")
        docs = list(meds_ref.stream())

        # If no medicines found in users/{uid}/medicines, check legacy patients/{uid}/medicines
        if not docs:
            legacy_ref = client.collection("patients").document(uid).collection("medicines")
            legacy_docs = list(legacy_ref.stream())
            if legacy_docs:
                for l_doc in legacy_docs:
                    l_data = l_doc.to_dict() or {}
                    meds_ref.document(l_doc.id).set(l_data, merge=True)
                    try:
                        l_doc.reference.delete()
                    except Exception:
                        pass
                docs = list(meds_ref.stream())

        items: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            items.append({
                "id": doc.id,
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
    """Add or update a medicine document under /users/{uid}/medicines/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(medicine_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
        print("[FIRESTORE ERROR] save_patient_medicine failed: Firestore client not initialized.")
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
        client.collection("users").document(uid).collection("medicines").document(doc_id).set(payload, merge=True)
        invalidate_firebase_cache()
        return doc_id
    except Exception as e:
        print(f"[FIRESTORE ERROR] save_patient_medicine failed: {e}")
        return None


def delete_patient_medicine(patient_id: str, medicine_id: str) -> bool:
    """Delete a medicine document from subcollection /users/{uid}/medicines/{medicine_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not medicine_id:
        return False

    client = get_firestore_client()
    if client is None:
        return False

    try:
        client.collection("users").document(uid).collection("medicines").document(medicine_id).delete()
        invalidate_firebase_cache()
        return True
    except Exception as e:
        print(f"[FIRESTORE ERROR] delete_patient_medicine failed: {e}")
        return False


def get_medicine_schedule(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return medicine schedule DataFrame from subcollection /users/{uid}/medicines."""
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


def save_patient_alert(patient_id: Optional[str], alert_data: Dict[str, Any]) -> Optional[str]:
    """Save alert document under /users/{uid}/alerts/{alert_id}."""
    uid = _resolve_user_uid(patient_id)
    if not isinstance(alert_data, dict) or not uid:
        return None

    client = get_firestore_client()
    doc_id = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    text = alert_data.get("text") or alert_data.get("message") or alert_data.get("alert") or ""
    alert_type = alert_data.get("type") or "emergency"
    payload = {
        "id": doc_id,
        "text": str(text),
        "type": alert_type,
        "created_at": datetime.utcnow().isoformat(),
    }

    if client:
        try:
            client.collection("users").document(uid).collection("alerts").document(doc_id).set(payload)
            return doc_id
        except Exception:
            pass
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
    """Return alert data for user from subcollection /users/{uid}/alerts."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    metrics = get_health_metrics(uid)
    emergency_alerts = check_and_trigger_vitals_alerts(uid, metrics)

    firebase_alerts: List[Dict[str, Any]] = []
    client = get_firestore_client()
    if client:
        try:
            docs = list(client.collection("users").document(uid).collection("alerts").stream())
            items = [d.to_dict() for d in docs if d.to_dict()]
            if items:
                for item in items:
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
    """Save an AI recommendation document under /users/{uid}/ai_recommendations/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not recommendation_text:
        return None

    client = get_firestore_client()
    if client is None:
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
        client.collection("users").document(uid).collection("ai_recommendations").document(doc_id).set(payload, merge=True)
        return doc_id
    except Exception as e:
        print(f"[FIRESTORE ERROR] save_ai_recommendation failed: {e}")
        return None


def get_ai_recommendations(patient_id: Optional[str] = None) -> List[str]:
    """Return AI recommendations strictly for user from subcollection /users/{uid}/ai_recommendations."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    client = get_firestore_client()
    if client:
        try:
            docs = list(client.collection("users").document(uid).collection("ai_recommendations").stream())
            items = [d.to_dict() for d in docs if d.to_dict()]
            if items:
                recs = [str(item.get("recommendation") or item.get("text") or item.get("message") or "") for item in items if item]
                return [r for r in recs if r]
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


def save_health_reading(patient_id: str, reading_data: Dict[str, Any]) -> Optional[str]:
    """Store health reading under /users/{uid}/health/{doc_id} and update /users/{uid}/health/latest."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(reading_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
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
        client.collection("users").document(uid).collection("health").document(doc_id).set(payload)
        save_latest_health_vitals(uid, payload)
        return doc_id
    except Exception:
        return None


def get_patient_health_readings(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return health readings for patient directly from subcollection /users/{uid}/health."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    readings: List[Dict[str, Any]] = []
    try:
        docs = list(client.collection("users").document(uid).collection("health").stream())
        for doc in docs:
            if doc.id == "latest":
                continue
            data = doc.to_dict() or {}
            data["id"] = doc.id
            readings.append(data)
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


def get_dashboard_data(patient_id: Optional[str] = None, owner_uid: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
    """Return dashboard data for the authenticated patient directly from /users/{uid}/patient/profile."""
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


def save_patient_report(patient_id: str, report_metadata: Dict[str, Any]) -> Optional[str]:
    """Store report under /users/{uid}/reports/{doc_id}."""
    uid = _resolve_user_uid(patient_id)
    if not uid or not isinstance(report_metadata, dict):
        return None

    client = get_firestore_client()
    if client is None:
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
        client.collection("users").document(uid).collection("reports").document(doc_id).set(payload)
        invalidate_firebase_cache()
        return doc_id
    except Exception:
        return None


def get_patient_reports(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return generated reports for patient from /users/{uid}/reports."""
    uid = _resolve_user_uid(patient_id)
    if not uid:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    try:
        docs = list(client.collection("users").document(uid).collection("reports").stream())
        reports: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            reports.append(data)

        reports.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return reports
    except Exception:
        return []


def get_firebase_data() -> Dict[str, Any]:
    """Backward-compatible wrapper for dashboard data."""
    return get_dashboard_data()
