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
        for k in ["cached_user_patients", "cached_patient_data", "cached_dashboard_data", "medicine_df", "monitoring_data"]:
            st.session_state.pop(k, None)
    except Exception:
        pass


def _get_collection_data(collection_name: str) -> Optional[List[Dict[str, Any]]]:
    """Read a Firestore collection and return its documents as dictionaries."""
    try:
        client = get_firestore_client()
        if client is None:
            return None

        docs = client.collection(collection_name).stream()
        items: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict()
            if data is None:
                continue
            data["id"] = doc.id
            items.append(data)
        return items if items else None
    except Exception:
        return None


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
    """Check if a patient with matching phone, email, or name already exists for this owner."""
    if not owner_uid:
        return False, ""

    existing_patients = get_all_patients(owner_uid=owner_uid)
    phone_clean = phone_number.strip().lower()
    email_clean = email.strip().lower()
    name_clean = name.strip().lower()

    for p in existing_patients:
        p_id = p.get("patient_id") or p.get("id")
        if exclude_patient_id and p_id == exclude_patient_id:
            continue

        p_phone = str(p.get("phone_number") or "").strip().lower()
        p_email = str(p.get("email") or "").strip().lower()
        p_name = str(p.get("name") or "").strip().lower()

        if phone_clean and p_phone and phone_clean == p_phone:
            return True, f"A patient with phone number '{phone_number}' already exists."
        if email_clean and p_email and email_clean == p_email:
            return True, f"A patient with email '{email}' already exists."
        if name_clean and p_name and name_clean == p_name:
            return True, f"A patient named '{name}' already exists in your account."

    return False, ""


def save_patient_registration(patient_data: Dict[str, Any], owner_uid: Optional[str] = None) -> Optional[str]:
    """Save or update patient profile in Firebase under /patients/{uid} using the user's Auth UID."""
    client = get_firestore_client()
    if not isinstance(patient_data, dict):
        return None

    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    final_owner = owner_uid or patient_data.get("ownerUid") or patient_data.get("owner_uid") or "demo_user"
    patient_id = final_owner  # Store directly under patients/{uid}
    now_iso = datetime.utcnow().isoformat()

    doc_ref = client.collection("patients").document(patient_id) if client else None
    existing_doc = doc_ref.get() if doc_ref else None
    existing_data = existing_doc.to_dict() if (existing_doc and existing_doc.exists) else {}

    payload = {
        "patient_id": patient_id,
        "ownerUid": final_owner,
        "owner_uid": final_owner,
        "name": patient_data.get("name") or patient_data.get("full_name") or existing_data.get("name") or "",
        "full_name": patient_data.get("full_name") or patient_data.get("name") or existing_data.get("full_name") or "",
        "age": patient_data.get("age") if patient_data.get("age") is not None else existing_data.get("age"),
        "gender": patient_data.get("gender") or existing_data.get("gender") or "Other",
        "dob": str(patient_data.get("dob") or existing_data.get("dob") or ""),
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
        "medicine_box_id": patient_data.get("medicine_box_id") or existing_data.get("medicine_box_id") or f"BOX-{final_owner[:6].upper()}",
        "device_serial_number": patient_data.get("device_serial_number") or existing_data.get("device_serial_number") or f"DEV-{final_owner[:6].upper()}",
        "device_status": existing_data.get("device_status", "Connected"),
        "battery_level": existing_data.get("battery_level", 90),
        "created_at": existing_data.get("created_at", now_iso),
        "updated_at": now_iso,
        "last_sync": now_iso,
    }

    if doc_ref is not None:
        try:
            doc_ref.set(payload, merge=True)
            invalidate_firebase_cache()
            return patient_id
        except Exception:
            pass

    invalidate_firebase_cache()
    return patient_id


def update_patient_registration(
    patient_id: str,
    update_data: Dict[str, Any],
    owner_uid: Optional[str] = None
) -> bool:
    """Update an existing patient document in Firebase under /patients/{patient_id}."""
    if not patient_id or not isinstance(update_data, dict):
        return False

    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    client = get_firestore_client()
    if client is None:
        return False

    try:
        doc_ref = client.collection("patients").document(patient_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        doc_dict = doc.to_dict() or {}
        doc_owner = doc_dict.get("ownerUid") or doc_dict.get("owner_uid")
        if owner_uid and doc_owner and doc_owner != owner_uid:
            return False

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

        doc_ref.set(payload, merge=True)
        invalidate_firebase_cache()
        return True
    except Exception:
        return False


def delete_patient(patient_id: str, owner_uid: Optional[str] = None) -> bool:
    """Delete a patient document and its sub-collections from Firebase."""
    if not patient_id:
        return False

    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    client = get_firestore_client()
    if client is None:
        return False

    try:
        p_ref = client.collection("patients").document(patient_id)
        doc = p_ref.get()
        if not doc.exists:
            return False

        d_dict = doc.to_dict() or {}
        doc_owner = d_dict.get("ownerUid") or d_dict.get("owner_uid")
        if owner_uid and doc_owner and doc_owner != owner_uid:
            return False

        for sub_col in ["medicines", "health", "readings", "alerts", "ai_recommendations"]:
            try:
                sub_docs = list(p_ref.collection(sub_col).stream())
                for s_doc in sub_docs:
                    s_doc.reference.delete()
            except Exception:
                pass

        p_ref.delete()
        if patient_id in _ESP32_LIVE_CACHE:
            del _ESP32_LIVE_CACHE[patient_id]
        invalidate_firebase_cache()
        return True
    except Exception:
        return False


def get_all_patients(owner_uid: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Read patients belonging exclusively to current user's UID (ownerUid) from Firebase with session_state caching."""
    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    if not owner_uid:
        return []

    try:
        import streamlit as st
        if not force_refresh and "cached_user_patients" in st.session_state:
            cached_uid, cached_patients = st.session_state["cached_user_patients"]
            if cached_uid == owner_uid:
                return cached_patients
    except Exception:
        pass

    client = get_firestore_client()
    if client is None:
        return []

    try:
        patients_ref = client.collection("patients")
        docs_camel = list(patients_ref.where("ownerUid", "==", owner_uid).stream())
        docs_snake = list(patients_ref.where("owner_uid", "==", owner_uid).stream())

        seen_ids = set()
        items: List[Dict[str, Any]] = []

        for doc in docs_camel + docs_snake:
            if doc.id in seen_ids:
                continue
            seen_ids.add(doc.id)
            data = doc.to_dict() or {}
            doc_owner = data.get("ownerUid") or data.get("owner_uid")
            if doc_owner != owner_uid:
                continue
            data["id"] = doc.id
            if "patient_id" not in data:
                data["patient_id"] = doc.id
            items.append(data)

        try:
            import streamlit as st
            st.session_state["cached_user_patients"] = (owner_uid, items)
        except Exception:
            pass

        return items
    except Exception:
        return []


def get_patient_by_id(patient_id: Optional[str], owner_uid: Optional[str] = None, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """Return a patient document from Firebase by patient ID scoped strictly to current user's ownerUid with session_state caching."""
    if not patient_id:
        return None

    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    try:
        import streamlit as st
        if not force_refresh:
            if "cached_patient_data" in st.session_state:
                c_pid, c_uid, c_data = st.session_state["cached_patient_data"]
                if c_pid == patient_id and (not owner_uid or c_uid == owner_uid):
                    return c_data

            cached_patients = get_all_patients(owner_uid=owner_uid, force_refresh=False)
            for p in cached_patients:
                if p.get("patient_id") == patient_id or p.get("id") == patient_id:
                    st.session_state["cached_patient_data"] = (patient_id, owner_uid, p)
                    return p
    except Exception:
        pass

    client = get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection("patients").document(patient_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}

        doc_owner = data.get("ownerUid") or data.get("owner_uid")
        if owner_uid and doc_owner and doc_owner != owner_uid:
            return None

        data["id"] = doc.id
        if "patient_id" not in data:
            data["patient_id"] = patient_id
        data.setdefault("device_status", "Connected")
        data.setdefault("battery_level", 85)
        data.setdefault("last_sync", data.get("created_at") or (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"))

        try:
            import streamlit as st
            st.session_state["cached_patient_data"] = (patient_id, owner_uid, data)
        except Exception:
            pass

        return data
    except Exception:
        return None


def process_esp32_data(
    heart_rate: float,
    spo2: float,
    temperature: float,
    patient_id: Optional[str] = None,
    blood_pressure: Optional[str] = "120/80"
) -> Dict[str, Any]:
    """Receive heart_rate, spo2, and temperature from ESP32, store in Firebase, and evaluate emergency alerts."""
    if not patient_id:
        try:
            import streamlit as st
            patient_id = st.session_state.get("user_uid") or st.session_state.get("owner_uid") or st.session_state.get("selected_patient_id")
        except Exception:
            patient_id = None

    if not patient_id:
        return {"success": False, "error": "Authentication / Patient ID required."}

    now_iso = datetime.utcnow().isoformat()
    reading_payload = {
        "patient_id": patient_id,
        "ownerUid": patient_id,
        "owner_uid": patient_id,
        "heart_rate": float(heart_rate),
        "spo2": float(spo2),
        "temperature": float(temperature),
        "blood_pressure": blood_pressure or "120/80",
        "timestamp": now_iso,
        "source": "ESP32_Device"
    }

    _ESP32_LIVE_CACHE[patient_id] = reading_payload

    doc_id = save_health_reading(patient_id, reading_payload)

    client = get_firestore_client()
    if client and patient_id:
        try:
            client.collection("patients").document(patient_id).set({
                "latest_vitals": reading_payload,
                "heart_rate": float(heart_rate),
                "spo2": float(spo2),
                "temperature": float(temperature),
                "blood_pressure": blood_pressure or "120/80",
                "last_sync": now_iso
            }, merge=True)

            client.collection("esp32_telemetry").document(f"ESP-{uuid.uuid4().hex[:8].upper()}").set(reading_payload)
        except Exception:
            pass

    alerts = check_and_trigger_vitals_alerts(patient_id, reading_payload)

    return {
        "success": True,
        "reading_id": doc_id or f"READING-{uuid.uuid4().hex[:8].upper()}",
        "patient_id": patient_id,
        "vitals": reading_payload,
        "alerts_triggered": len(alerts)
    }


def get_health_metrics(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Return health metrics from Firebase sub-collections / live ESP32 data for selected patient."""
    metrics: Dict[str, Any] = {
        "heart_rate": None,
        "spo2": None,
        "temperature": None,
        "blood_pressure": None,
        "health_score": None,
    }

    if not patient_id:
        return metrics

    client = get_firestore_client()

    def _extract_metrics_from_dict(source: Dict[str, Any]) -> Dict[str, Any]:
        extracted = {}
        hr = source.get("heart_rate") or source.get("heartRate") or source.get("bpm") or source.get("hr")
        if hr is not None:
            extracted["heart_rate"] = hr

        spo2 = source.get("spo2") or source.get("spO2") or source.get("SPO2") or source.get("oxygen_saturation") or source.get("oxygen")
        if spo2 is not None:
            extracted["spo2"] = spo2

        temp = source.get("temperature") or source.get("temp") or source.get("body_temperature")
        if temp is not None:
            extracted["temperature"] = temp

        bp = source.get("blood_pressure") or source.get("bloodPressure") or source.get("bp")
        if bp is not None:
            extracted["blood_pressure"] = bp

        score = source.get("health_score") or source.get("healthScore") or source.get("score")
        if score is not None:
            extracted["health_score"] = score

        return extracted

    if patient_id in _ESP32_LIVE_CACHE:
        metrics.update(_extract_metrics_from_dict(_ESP32_LIVE_CACHE[patient_id]))

    patient = get_patient_by_id(patient_id)
    if patient:
        metrics.update(_extract_metrics_from_dict(patient))
        if "latest_vitals" in patient and isinstance(patient["latest_vitals"], dict):
            metrics.update(_extract_metrics_from_dict(patient["latest_vitals"]))

    if client:
        for sub_col in ["health", "readings"]:
            try:
                sub_docs = list(client.collection("patients").document(patient_id).collection(sub_col).limit(10).stream())
                if sub_docs:
                    latest_doc = sub_docs[-1].to_dict() or {}
                    extracted = _extract_metrics_from_dict(latest_doc)
                    for k, v in extracted.items():
                        metrics.setdefault(k, v)
            except Exception:
                pass

    if any(metrics.get(k) is not None for k in ["heart_rate", "spo2", "temperature"]):
        score = 100
        try:
            hr = float(metrics.get("heart_rate")) if metrics.get("heart_rate") is not None else 75.0
            if hr > 100 or hr < 60:
                score -= 15
        except (TypeError, ValueError):
            pass

        try:
            spo2 = float(metrics.get("spo2")) if metrics.get("spo2") is not None else 98.0
            if spo2 < 95:
                score -= int((95 - spo2) * 5)
        except (TypeError, ValueError):
            pass

        try:
            temp = float(metrics.get("temperature")) if metrics.get("temperature") is not None else 36.8
            if temp > 37.5 or temp < 36.0:
                score -= 10
        except (TypeError, ValueError):
            pass

        metrics["health_score"] = max(0, min(100, score))

    return metrics


def get_patient_medicines(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return medicines exclusively from subcollection /patients/{patient_id}/medicines."""
    if not patient_id:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    try:
        docs = client.collection("patients").document(patient_id).collection("medicines").stream()
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
    except Exception:
        return []


def save_patient_medicine(patient_id: str, medicine_data: Dict[str, Any], medicine_id: Optional[str] = None) -> Optional[str]:
    """Add or update a medicine document under /patients/{patient_id}/medicines/{doc_id} and root /medicines collection linked to user's UID."""
    if not patient_id or not isinstance(medicine_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
        return None

    doc_id = medicine_id or f"MED-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "id": doc_id,
        "medicine_id": doc_id,
        "patient_id": patient_id,
        "ownerUid": patient_id,
        "owner_uid": patient_id,
        "medicine_name": medicine_data.get("Medicine") or medicine_data.get("medicine_name") or "",
        "dosage": medicine_data.get("Dosage") or medicine_data.get("dosage") or "",
        "time": medicine_data.get("Time") or medicine_data.get("time") or "",
        "status": medicine_data.get("Status") or medicine_data.get("status") or "Upcoming",
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        # Write to patient subcollection
        client.collection("patients").document(patient_id).collection("medicines").document(doc_id).set(payload)
        # Write to root /medicines collection linked to ownerUid
        client.collection("medicines").document(doc_id).set(payload)
        invalidate_firebase_cache()
        return doc_id
    except Exception:
        return None


def delete_patient_medicine(patient_id: str, medicine_id: str) -> bool:
    """Delete a medicine document from Firebase under subcollection and root /medicines collection."""
    if not patient_id or not medicine_id:
        return False

    client = get_firestore_client()
    if client is None:
        return False

    try:
        client.collection("patients").document(patient_id).collection("medicines").document(medicine_id).delete()
        client.collection("medicines").document(medicine_id).delete()
        invalidate_firebase_cache()
        return True
    except Exception:
        return False


def get_medicine_schedule(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return medicine schedule DataFrame from subcollection /patients/{patient_id}/medicines."""
    if patient_id:
        items = get_patient_medicines(patient_id)
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
    """Save an alert document into Firebase under /patients/{patient_id}/alerts/{alert_id}."""
    if not isinstance(alert_data, dict) or not patient_id:
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
            client.collection("patients").document(patient_id).collection("alerts").document(doc_id).set(payload)
            return doc_id
        except Exception:
            pass
    return None


def check_and_trigger_vitals_alerts(patient_id: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Automatically check health metrics against emergency thresholds and trigger & save alerts."""
    if metrics is None:
        metrics = get_health_metrics(patient_id)

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

    if patient_id:
        for alert in triggered_alerts:
            save_patient_alert(patient_id, alert)

    return triggered_alerts


def get_alerts(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return alert data for the selected patient from subcollection /patients/{patient_id}/alerts."""
    if not patient_id:
        return []

    metrics = get_health_metrics(patient_id)
    emergency_alerts = check_and_trigger_vitals_alerts(patient_id, metrics)

    firebase_alerts: List[Dict[str, Any]] = []
    client = get_firestore_client()
    if client:
        try:
            docs = client.collection("patients").document(patient_id).collection("alerts").stream()
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


def get_ai_recommendations(patient_id: Optional[str] = None) -> List[str]:
    """Return AI recommendations strictly for the selected patient from subcollection /patients/{patient_id}/ai_recommendations."""
    if not patient_id:
        return []

    client = get_firestore_client()
    if client:
        try:
            docs = client.collection("patients").document(patient_id).collection("ai_recommendations").stream()
            items = [d.to_dict() for d in docs if d.to_dict()]
            if items:
                recs = [str(item.get("recommendation") or item.get("text") or item.get("message") or "") for item in items if item]
                return [r for r in recs if r]
        except Exception:
            pass

    # Generate dynamic patient-specific AI recommendation based on patient vitals & medicines
    metrics = get_health_metrics(patient_id)
    patient = get_patient_by_id(patient_id) or {}
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
    """Store a health reading document in Firebase under subcollection and root /health_metrics collection linked to user UID."""
    if not patient_id or not isinstance(reading_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
        return None

    doc_id = f"READING-{uuid.uuid4().hex[:8].upper()}"
    timestamp = reading_data.get("timestamp") or datetime.utcnow().isoformat()
    payload = {
        "id": doc_id,
        "reading_id": doc_id,
        "patient_id": patient_id,
        "ownerUid": patient_id,
        "owner_uid": patient_id,
        "heart_rate": reading_data.get("heart_rate") or reading_data.get("heartRate"),
        "spo2": reading_data.get("spo2") or reading_data.get("spO2"),
        "temperature": reading_data.get("temperature") or reading_data.get("temp"),
        "blood_pressure": reading_data.get("blood_pressure") or reading_data.get("bloodPressure") or reading_data.get("bp"),
        "health_score": reading_data.get("health_score") or reading_data.get("healthScore"),
        "timestamp": timestamp,
    }

    try:
        p_ref = client.collection("patients").document(patient_id)
        p_ref.collection("health").document(doc_id).set(payload)
        p_ref.collection("health_metrics").document(doc_id).set(payload)
        client.collection("health_metrics").document(doc_id).set(payload)
        return doc_id
    except Exception:
        return None


def get_patient_health_readings(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return stored health readings for a patient strictly from Firebase subcollection /patients/{patient_id}/health or root /health_metrics."""
    if not patient_id:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    readings: List[Dict[str, Any]] = []
    try:
        for col_name in ["health", "health_metrics"]:
            docs = client.collection("patients").document(patient_id).collection(col_name).stream()
            for doc in docs:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                readings.append(data)
            if readings:
                break

        if not readings:
            docs = client.collection("health_metrics").where("ownerUid", "==", patient_id).stream()
            for doc in docs:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                readings.append(data)
    except Exception:
        pass

    readings.sort(key=lambda r: str(r.get("timestamp", "")))
    return readings


def get_patient_health_trends(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return a DataFrame of historical health readings for a patient."""
    cols = ["time", "heart_rate", "spo2", "temperature", "blood_pressure", "health_score"]
    if not patient_id:
        return pd.DataFrame(columns=cols)

    readings = get_patient_health_readings(patient_id)
    if not readings:
        metrics = get_health_metrics(patient_id)
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
    """Return dashboard data for the selected patient belonging exclusively to owner_uid with session_state caching."""
    if not owner_uid:
        try:
            import streamlit as st
            owner_uid = st.session_state.get("user_uid") or st.session_state.get("owner_uid")
        except Exception:
            owner_uid = None

    try:
        import streamlit as st
        if not force_refresh and "cached_dashboard_data" in st.session_state:
            c_pid, c_uid, c_data = st.session_state["cached_dashboard_data"]
            if c_pid == patient_id and (not owner_uid or c_uid == owner_uid):
                return c_data
    except Exception:
        pass

    user_patients = get_all_patients(owner_uid=owner_uid, force_refresh=force_refresh)

    if not user_patients:
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

    active_patient_id = patient_id
    if not active_patient_id or not any(p.get("patient_id") == active_patient_id or p.get("id") == active_patient_id for p in user_patients):
        active_patient_id = user_patients[0].get("patient_id") or user_patients[0].get("id")

    patient = get_patient_by_id(active_patient_id, owner_uid=owner_uid, force_refresh=force_refresh) or user_patients[0]

    dashboard_res = {
        "patient": patient,
        "no_patients": False,
        "metrics": get_health_metrics(active_patient_id),
        "medicines": get_medicine_schedule(active_patient_id),
        "alerts": get_alerts(active_patient_id),
        "ai": get_ai_recommendations(active_patient_id),
        "trends": get_patient_health_trends(active_patient_id),
        "offline": False,
    }

    try:
        import streamlit as st
        st.session_state["cached_dashboard_data"] = (active_patient_id, owner_uid, dashboard_res)
    except Exception:
        pass

    return dashboard_res


def save_patient_report(patient_id: str, report_metadata: Dict[str, Any]) -> Optional[str]:
    """Store a generated report document under subcollection /patients/{patient_id}/reports and root /reports collection."""
    if not patient_id or not isinstance(report_metadata, dict):
        return None

    client = get_firestore_client()
    if client is None:
        return None

    doc_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.utcnow().isoformat()

    payload = {
        "id": doc_id,
        "report_id": doc_id,
        "patient_id": patient_id,
        "ownerUid": patient_id,
        "owner_uid": patient_id,
        "report_type": report_metadata.get("report_type") or "PDF",
        "file_name": report_metadata.get("file_name") or f"report_{patient_id}.pdf",
        "health_score": report_metadata.get("health_score"),
        "created_at": timestamp,
        "generated_by": report_metadata.get("generated_by") or patient_id,
    }

    try:
        client.collection("patients").document(patient_id).collection("reports").document(doc_id).set(payload)
        client.collection("reports").document(doc_id).set(payload)
        return doc_id
    except Exception:
        return None


def get_patient_reports(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return generated report history strictly for the selected patient from /patients/{patient_id}/reports."""
    if not patient_id:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    try:
        docs = client.collection("patients").document(patient_id).collection("reports").stream()
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
