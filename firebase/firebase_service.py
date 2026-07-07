from typing import Any, Dict, List, Optional

from firebase.config import get_firestore_client
from src.data import get_all_dummy_data


def _get_collection_data(collection_name: str) -> Optional[List[Dict[str, Any]]]:
    """Read a Firestore collection and return its documents as dictionaries."""
    try:
        client = get_firestore_client()
        if client is None:
            return None

        docs = client.collection(collection_name).stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            if data is None:
                continue
            data["id"] = doc.id
            items.append(data)
        return items
    except Exception:
        return None


def get_patient() -> Optional[Dict[str, Any]]:
    """Read the patient document from Firestore if available."""
    try:
        items = _get_collection_data("Patient")
        if not items:
            return None
        return items[0]
    except Exception:
        return None


def get_health_metrics() -> Optional[Dict[str, Any]]:
    """Read the health metrics document from Firestore if available."""
    try:
        items = _get_collection_data("Health Metrics")
        if not items:
            return None
        return items[0]
    except Exception:
        return None


def get_medicines() -> Optional[List[Dict[str, Any]]]:
    """Read medicines from Firestore if available."""
    return _get_collection_data("Medicines")


def get_alerts() -> Optional[List[Dict[str, Any]]]:
    """Read alerts from Firestore if available."""
    return _get_collection_data("Alerts")


def get_firebase_data() -> Dict[str, Any]:
    """Return data from Firebase or fall back to the existing dummy data."""
    dummy_data = get_all_dummy_data()

    patient = get_patient() or dummy_data["patient"]
    metrics = get_health_metrics() or dummy_data["metrics"]
    medicines = get_medicines()
    alerts = get_alerts()

    if medicines is None:
        medicines = dummy_data["medicines"]
    if alerts is None:
        alerts = dummy_data["alerts"]

    if isinstance(medicines, list) and medicines and isinstance(medicines[0], dict):
        medicines_df = None
        try:
            import pandas as pd

            medicines_df = pd.DataFrame([
                {
                    "Medicine": item.get("medicine_name") or item.get("name") or item.get("Medicine") or "",
                    "Dosage": item.get("dosage") or item.get("Dosage") or "",
                    "Time": item.get("time") or item.get("Time") or "",
                    "Status": item.get("status") or item.get("Status") or "",
                }
                for item in medicines
            ])
        except Exception:
            medicines_df = dummy_data["medicines"]
    else:
        medicines_df = dummy_data["medicines"]

    alerts_struct = []
    if isinstance(alerts, list):
        for alert in alerts:
            if isinstance(alert, dict):
                text = alert.get("text") or alert.get("message") or alert.get("alert") or ""
                alert_type = alert.get("type") or ("warning" if "missed" in str(text).lower() or "battery" in str(text).lower() else "info")
                alerts_struct.append({"type": alert_type, "text": text})
            elif isinstance(alert, str):
                alerts_struct.append({"type": "warning" if "Missed" in alert or "Low battery" in alert else "info", "text": alert})

    if not alerts_struct:
        alerts_struct = dummy_data["alerts"]

    return {
        "patient": patient,
        "metrics": metrics,
        "medicines": medicines_df if medicines_df is not None else dummy_data["medicines"],
        "alerts": alerts_struct,
        "ai": dummy_data["ai"],
        "trends": dummy_data["trends"],
    }
