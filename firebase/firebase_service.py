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


def get_patient_data() -> Dict[str, Any]:
    """Return patient data from Firebase or the existing dummy data."""
    return _get_first_record("Patient") or get_all_dummy_data()["patient"]


def get_health_metrics() -> Dict[str, Any]:
    """Return health metrics from Firebase or the existing dummy data."""
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


def get_dashboard_data() -> Dict[str, Any]:
    """Return the dashboard data structure used by the UI."""
    dummy_data = get_all_dummy_data()
    return {
        "patient": get_patient_data(),
        "metrics": get_health_metrics(),
        "medicines": get_medicine_schedule(),
        "alerts": get_alerts(),
        "ai": get_ai_recommendations(),
        "trends": dummy_data["trends"],
        "offline": False,
    }


def get_firebase_data() -> Dict[str, Any]:
    """Backward-compatible wrapper for the dashboard data."""
    return get_dashboard_data()
