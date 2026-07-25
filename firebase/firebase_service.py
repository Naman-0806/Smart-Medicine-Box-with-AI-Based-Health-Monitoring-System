import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from firebase.config import get_firestore_client
from src.data import get_all_dummy_data


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


def _get_first_record(collection_name: str) -> Optional[Dict[str, Any]]:
    """Return the first document from a collection or None."""
    items = _get_collection_data(collection_name)
    return items[0] if items else None


def save_patient_registration(patient_data: Dict[str, Any]) -> Optional[str]:
    """Save patient data to Firebase under /patients/{patient_id}."""
    client = get_firestore_client()
    if client is None or not isinstance(patient_data, dict):
        return None

    patient_id = f"PT-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "patient_id": patient_id,
        "name": patient_data.get("name") or patient_data.get("full_name") or "",
        "age": patient_data.get("age"),
        "gender": patient_data.get("gender"),
        "blood_group": patient_data.get("blood_group"),
        "height": patient_data.get("height"),
        "weight": patient_data.get("weight"),
        "disease": patient_data.get("disease") or patient_data.get("existing_diseases") or "",
        "doctor_name": patient_data.get("doctor_name"),
        "phone_number": patient_data.get("phone_number"),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        client.collection("patients").document(patient_id).set(payload)
        return patient_id
    except Exception:
        return None


def get_all_patients() -> List[Dict[str, Any]]:
    """Read all patients from Firebase."""
    items = _get_collection_data("patients")
    return items or []


def get_patient_by_id(patient_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return a patient document from Firebase by patient ID."""
    if not patient_id:
        return None

    client = get_firestore_client()
    if client is None:
        return None

    try:
        doc = client.collection("patients").document(patient_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data
    except Exception:
        return None


def get_patient_data() -> Dict[str, Any]:
    """Return patient data from Firebase or the existing dummy data."""
    return _get_first_record("Patient") or get_all_dummy_data()["patient"]


def get_health_metrics(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Return health metrics from Firebase for the selected patient or fallback to dummy data."""
    if patient_id:
        patient = get_patient_by_id(patient_id)
        if patient:
            metrics = {
                "heart_rate": patient.get("heart_rate"),
                "spo2": patient.get("spo2"),
                "temperature": patient.get("temperature"),
                "blood_pressure": patient.get("blood_pressure"),
                "health_score": patient.get("health_score"),
            }
            if any(value is not None for value in metrics.values()):
                return metrics

    return _get_first_record("Health Metrics") or get_all_dummy_data()["metrics"]


def get_medicine_schedule() -> Any:
    """Return medicine data from Firebase or the existing dummy data."""
    items = _get_collection_data("Medicines")
    if items is None:
        return get_all_dummy_data()["medicines"]

    try:
        return pd.DataFrame([
            {
                "Medicine": item.get("medicine_name") or item.get("name") or item.get("Medicine") or "",
                "Dosage": item.get("dosage") or item.get("Dosage") or "",
                "Time": item.get("time") or item.get("Time") or "",
                "Status": item.get("status") or item.get("Status") or "",
            }
            for item in items
        ])
    except Exception:
        return get_all_dummy_data()["medicines"]


def get_alerts() -> List[Dict[str, Any]]:
    """Return alert data from Firebase or the existing dummy data."""
    items = _get_collection_data("Alerts")
    if items is None:
        return get_all_dummy_data()["alerts"]

    alerts: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("message") or item.get("alert") or ""
            alert_type = item.get("type") or ("warning" if "missed" in str(text).lower() or "battery" in str(text).lower() else "info")
            alerts.append({"type": alert_type, "text": str(text)})
    return alerts or get_all_dummy_data()["alerts"]


def get_ai_recommendations() -> List[str]:
    """Return AI recommendations from Firebase or the existing dummy data."""
    items = _get_collection_data("AI Recommendations")
    if items is None:
        return get_all_dummy_data()["ai"]

    recs = [str(item.get("recommendation") or item.get("text") or item.get("message") or "") for item in items if item]
    return [rec for rec in recs if rec] or get_all_dummy_data()["ai"]


def get_dashboard_data(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the dashboard data structure used by the UI."""
    dummy_data = get_all_dummy_data()
    patient = get_patient_by_id(patient_id) or get_patient_data()
    return {
        "patient": patient,
        "metrics": get_health_metrics(patient_id),
        "medicines": get_medicine_schedule(),
        "alerts": get_alerts(),
        "ai": get_ai_recommendations(),
        "trends": dummy_data["trends"],
        "offline": False,
    }


def get_firebase_data() -> Dict[str, Any]:
    """Backward-compatible wrapper for the dashboard data."""
    return get_dashboard_data()
