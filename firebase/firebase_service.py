import uuid
from datetime import datetime, timedelta
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
        if "patient_id" not in data:
            data["patient_id"] = patient_id
        data.setdefault("device_status", "Connected")
        data.setdefault("battery_level", 85)
        data.setdefault("last_sync", data.get("created_at") or (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"))
        return data
    except Exception:
        return None


def get_patient_data() -> Dict[str, Any]:
    """Return patient data from Firebase or the existing dummy data."""
    return _get_first_record("Patient") or get_all_dummy_data()["patient"]


_ESP32_LIVE_CACHE: Dict[str, Any] = {}


def process_esp32_data(
    heart_rate: float,
    spo2: float,
    temperature: float,
    patient_id: Optional[str] = None,
    blood_pressure: Optional[str] = "120/80"
) -> Dict[str, Any]:
    """Receive heart_rate, spo2, and temperature from ESP32, store received values in Firebase, and evaluate emergency alerts."""
    if not patient_id:
        try:
            import streamlit as st
            patient_id = st.session_state.get("selected_patient_id")
        except Exception:
            patient_id = None
    if not patient_id:
        patients = get_all_patients()
        if patients:
            patient_id = patients[0].get("patient_id") or patients[0].get("id")
        else:
            patient_id = "PT-ESP32-DEFAULT"

    now_iso = datetime.utcnow().isoformat()
    reading_payload = {
        "patient_id": patient_id,
        "heart_rate": float(heart_rate),
        "spo2": float(spo2),
        "temperature": float(temperature),
        "blood_pressure": blood_pressure or "120/80",
        "timestamp": now_iso,
        "source": "ESP32_Device"
    }

    # Store in memory live cache for instant precedence
    _ESP32_LIVE_CACHE[patient_id] = reading_payload
    _ESP32_LIVE_CACHE["latest"] = reading_payload

    # Save to Firebase subcollection /patients/{patient_id}/readings
    doc_id = save_health_reading(patient_id, reading_payload)

    # Save to patient document latest_vitals
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

    # Automatically trigger & save emergency alerts if vitals breach thresholds
    alerts = check_and_trigger_vitals_alerts(patient_id, reading_payload)

    return {
        "success": True,
        "reading_id": doc_id or f"READING-{uuid.uuid4().hex[:8].upper()}",
        "patient_id": patient_id,
        "vitals": reading_payload,
        "alerts_triggered": len(alerts)
    }


def get_health_metrics(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Return health metrics (heart rate, SpO2, temperature, blood pressure, health score) from Firebase for the selected patient.
    Prioritizes live ESP32 & Firebase sensor data over dummy values.
    """
    default_metrics = get_all_dummy_data()["metrics"]
    metrics: Dict[str, Any] = {}

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

    # Check ESP32 live cache first
    if patient_id and patient_id in _ESP32_LIVE_CACHE:
        metrics.update(_extract_metrics_from_dict(_ESP32_LIVE_CACHE[patient_id]))
    elif "latest" in _ESP32_LIVE_CACHE and not patient_id:
        metrics.update(_extract_metrics_from_dict(_ESP32_LIVE_CACHE["latest"]))


    if patient_id:
        patient = get_patient_by_id(patient_id)
        if patient:
            metrics.update(_extract_metrics_from_dict(patient))
            if "latest_vitals" in patient and isinstance(patient["latest_vitals"], dict):
                metrics.update(_extract_metrics_from_dict(patient["latest_vitals"]))

        if client and len(metrics) < 4:
            try:
                sub_docs = list(client.collection("patients").document(patient_id).collection("readings").limit(10).stream())
                if sub_docs:
                    latest_doc = sub_docs[-1].to_dict() or {}
                    extracted = _extract_metrics_from_dict(latest_doc)
                    for k, v in extracted.items():
                        metrics.setdefault(k, v)
            except Exception:
                pass

    if client and ("heart_rate" not in metrics or "spo2" not in metrics or "temperature" not in metrics):
        try:
            esp_docs = list(client.collection("esp32_telemetry").limit(1).stream())
            if esp_docs:
                extracted = _extract_metrics_from_dict(esp_docs[0].to_dict() or {})
                for k, v in extracted.items():
                    metrics.setdefault(k, v)
        except Exception:
            pass

    # Dynamic calculation of health_score if live vitals are available
    if any(k in metrics for k in ["heart_rate", "spo2", "temperature"]):
        score = 100
        try:
            hr = float(metrics.get("heart_rate", 75))
            if hr > 100 or hr < 60:
                score -= 15
        except (TypeError, ValueError):
            pass

        try:
            spo2 = float(metrics.get("spo2", 98))
            if spo2 < 95:
                score -= int((95 - spo2) * 5)
        except (TypeError, ValueError):
            pass

        try:
            temp = float(metrics.get("temperature", 36.8))
            if temp > 37.5 or temp < 36.0:
                score -= 10
        except (TypeError, ValueError):
            pass

        metrics["health_score"] = max(0, min(100, score))

    # Do not use dummy values if live data exists; fallback ONLY for missing keys
    for key in ["heart_rate", "spo2", "temperature", "blood_pressure", "health_score"]:
        if key not in metrics or metrics[key] is None:
            metrics[key] = default_metrics.get(key)

    return metrics



def get_patient_medicines(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return medicines for a specific patient from Firebase subcollection patients/{patient_id}/medicines."""
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
    """Add or update a medicine document in Firebase under /patients/{patient_id}/medicines/{medicine_id}."""
    if not patient_id or not isinstance(medicine_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
        return None

    doc_id = medicine_id or f"MED-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "id": doc_id,
        "medicine_name": medicine_data.get("Medicine") or medicine_data.get("medicine_name") or "",
        "dosage": medicine_data.get("Dosage") or medicine_data.get("dosage") or "",
        "time": medicine_data.get("Time") or medicine_data.get("time") or "",
        "status": medicine_data.get("Status") or medicine_data.get("status") or "Upcoming",
        "updated_at": datetime.utcnow().isoformat(),
    }

    try:
        client.collection("patients").document(patient_id).collection("medicines").document(doc_id).set(payload)
        return doc_id
    except Exception:
        return None


def delete_patient_medicine(patient_id: str, medicine_id: str) -> bool:
    """Delete a medicine document from Firebase under /patients/{patient_id}/medicines/{medicine_id}."""
    if not patient_id or not medicine_id:
        return False

    client = get_firestore_client()
    if client is None:
        return False

    try:
        client.collection("patients").document(patient_id).collection("medicines").document(medicine_id).delete()
        return True
    except Exception:
        return False


def get_medicine_schedule(patient_id: Optional[str] = None) -> Any:
    """Return medicine data from Firebase for the selected patient or fallback to general collection/dummy data."""
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

    items = _get_collection_data("Medicines")
    if items is None:
        return get_all_dummy_data()["medicines"]

    try:
        return pd.DataFrame([
            {
                "id": item.get("id", ""),
                "Medicine": item.get("medicine_name") or item.get("name") or item.get("Medicine") or "",
                "Dosage": item.get("dosage") or item.get("Dosage") or "",
                "Time": item.get("time") or item.get("Time") or "",
                "Status": item.get("status") or item.get("Status") or "",
            }
            for item in items
        ])
    except Exception:
        return get_all_dummy_data()["medicines"]


def save_patient_alert(patient_id: Optional[str], alert_data: Dict[str, Any]) -> Optional[str]:
    """Save an alert document into Firebase under /patients/{patient_id}/alerts/{alert_id}."""
    if not isinstance(alert_data, dict):
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
            if patient_id:
                client.collection("patients").document(patient_id).collection("alerts").document(doc_id).set(payload)
            else:
                client.collection("Alerts").document(doc_id).set(payload)
            return doc_id
        except Exception:
            pass
    return None


def check_and_trigger_vitals_alerts(patient_id: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Automatically check health metrics against emergency thresholds and trigger & save Firebase alerts:
    - Heart Rate > 100 or < 50
    - SpO2 < 92
    - Temperature > 38.5°C
    """
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

    # Heart Rate check: >100 or <50
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

    # SpO2 check: <92
    if spo2 is not None and spo2 < 92:
        triggered_alerts.append({
            "type": "emergency",
            "text": f"EMERGENCY: Low SpO2 level detected ({spo2}% < 92%)"
        })


    # Temperature check: >38.5°C
    if temp is not None and temp > 38.5:
        triggered_alerts.append({
            "type": "emergency",
            "text": f"EMERGENCY: High Body Temperature detected ({temp}°C > 38.5°C)"
        })

    # Save triggered alerts to Firebase
    for alert in triggered_alerts:
        save_patient_alert(patient_id, alert)

    return triggered_alerts


def get_alerts(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return alert data from Firebase for the selected patient, automatically checking vitals thresholds."""
    metrics = get_health_metrics(patient_id)
    emergency_alerts = check_and_trigger_vitals_alerts(patient_id, metrics)

    firebase_alerts: List[Dict[str, Any]] = []
    if patient_id:
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

    if not firebase_alerts:
        items = _get_collection_data("Alerts")
        if items:
            for item in items:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("message") or item.get("alert") or ""
                    alert_type = item.get("type") or ("emergency" if "EMERGENCY" in str(text) else ("warning" if "missed" in str(text).lower() or "battery" in str(text).lower() else "info"))
                    firebase_alerts.append({"type": alert_type, "text": str(text)})

    combined_alerts = []
    seen_texts = set()

    for a in emergency_alerts + firebase_alerts + get_all_dummy_data()["alerts"]:
        txt = a.get("text", "").strip()
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            combined_alerts.append(a)

    return combined_alerts



def get_ai_recommendations(patient_id: Optional[str] = None) -> List[str]:
    """Return AI recommendations from Firebase for the selected patient or fallback."""
    if patient_id:
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

    items = _get_collection_data("AI Recommendations")
    if items is None:
        return get_all_dummy_data()["ai"]

    recs = [str(item.get("recommendation") or item.get("text") or item.get("message") or "") for item in items if item]
    return [rec for rec in recs if rec] or get_all_dummy_data()["ai"]


def save_health_reading(patient_id: str, reading_data: Dict[str, Any]) -> Optional[str]:
    """Store a health reading document in Firebase under /patients/{patient_id}/readings."""
    if not patient_id or not isinstance(reading_data, dict):
        return None

    client = get_firestore_client()
    if client is None:
        return None

    doc_id = f"READING-{uuid.uuid4().hex[:8].upper()}"
    timestamp = reading_data.get("timestamp") or datetime.utcnow().isoformat()
    payload = {
        "id": doc_id,
        "patient_id": patient_id,
        "heart_rate": reading_data.get("heart_rate") or reading_data.get("heartRate"),
        "spo2": reading_data.get("spo2") or reading_data.get("spO2"),
        "temperature": reading_data.get("temperature") or reading_data.get("temp"),
        "blood_pressure": reading_data.get("blood_pressure") or reading_data.get("bloodPressure") or reading_data.get("bp"),
        "health_score": reading_data.get("health_score") or reading_data.get("healthScore"),
        "timestamp": timestamp,
    }

    try:
        client.collection("patients").document(patient_id).collection("readings").document(doc_id).set(payload)
        return doc_id
    except Exception:
        return None


def get_patient_health_readings(patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return stored health readings for a patient from Firebase subcollection /patients/{patient_id}/readings."""
    if not patient_id:
        return []

    client = get_firestore_client()
    if client is None:
        return []

    try:
        docs = client.collection("patients").document(patient_id).collection("readings").stream()
        readings: List[Dict[str, Any]] = []
        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            readings.append(data)

        readings.sort(key=lambda r: str(r.get("timestamp", "")))
        return readings
    except Exception:
        return []


def get_patient_health_trends(patient_id: Optional[str] = None) -> pd.DataFrame:
    """Return a DataFrame of historical health readings for a patient, falling back to dummy trends if unavailable."""
    dummy_trends = get_all_dummy_data()["trends"]
    if not patient_id:
        return dummy_trends

    readings = get_patient_health_readings(patient_id)
    if not readings:
        patient = get_patient_by_id(patient_id)
        if patient and any(k in patient for k in ["heart_rate", "spo2", "temperature", "blood_pressure"]):
            metrics = get_health_metrics(patient_id)
            save_health_reading(patient_id, metrics)
            readings = get_patient_health_readings(patient_id)

    if not readings:
        return dummy_trends

    rows = []
    for r in readings:
        rows.append({
            "time": str(r.get("timestamp") or r.get("created_at") or r.get("time") or ""),
            "heart_rate": r.get("heart_rate") or r.get("heartRate") or 72,
            "spo2": r.get("spo2") or r.get("spO2") or 97,
            "temperature": r.get("temperature") or r.get("temp") or 36.8,
            "blood_pressure": r.get("blood_pressure") or r.get("bp") or "120/80",
            "health_score": r.get("health_score") or r.get("score") or 85,
        })

    try:
        return pd.DataFrame(rows)
    except Exception:
        return dummy_trends


def get_dashboard_data(patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the dashboard data structure used by the UI."""
    dummy_data = get_all_dummy_data()
    patient = get_patient_by_id(patient_id) or get_patient_data()
    return {
        "patient": patient,
        "metrics": get_health_metrics(patient_id),
        "medicines": get_medicine_schedule(patient_id),
        "alerts": get_alerts(patient_id),
        "ai": get_ai_recommendations(patient_id),
        "trends": get_patient_health_trends(patient_id),
        "offline": False,
    }


def get_firebase_data() -> Dict[str, Any]:
    """Backward-compatible wrapper for the dashboard data."""
    return get_dashboard_data()
