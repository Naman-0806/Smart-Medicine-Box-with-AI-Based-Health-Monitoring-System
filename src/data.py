import pandas as pd
from datetime import datetime, timedelta
import random

# Patient (dictionary)
patient = {
    "name": "John Doe",
    "age": 68,
    "patient_id": "PM-00123",
    "blood_group": "O+",
    "device_status": "Connected",
    "battery_level": 78,
    "last_sync": (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
}

# Health metrics (dictionary)
health_metrics = {
    "heart_rate": 76,
    "spo2": 97,
    "temperature": 36.7,
    "health_score": 88,
}

# Medicine list (list of dictionaries)
medicines = [
    {"medicine_name": "Aspirin", "dosage": "81 mg", "time": "08:00", "status": "Taken"},
    {"medicine_name": "Lisinopril", "dosage": "10 mg", "time": "12:00", "status": "Missed"},
    {"medicine_name": "Metformin", "dosage": "500 mg", "time": "20:00", "status": "Upcoming"},
]

# Alerts (list of strings)
alerts = [
    "Missed dose: Lisinopril 12:00",
    "Low battery: Device battery at 78%",
    "Device synced 5 minutes ago",
]

# AI recommendations (list of strings)
ai_recommendations = [
    "Review blood pressure medication; consider dosage check at next visit.",
    "Encourage more frequent activity; schedule a follow-up in 2 weeks.",
]

# Chart data (lists / simple series)
def _generate_time_series(hours=24):
    now = datetime.now()
    times = [(now - timedelta(hours=hours - i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(hours)]
    return times

chart_times = _generate_time_series(24)
chart_heart_rate = [int(70 + random.gauss(0, 3) + (i % 3)) for i in range(24)]
chart_spo2 = [int(96 + random.gauss(0, 0.5)) for _ in range(24)]
chart_temperature = [round(36.5 + random.gauss(0, 0.05), 1) for _ in range(24)]


def get_all_dummy_data():
    """Return all dummy data in a structure consumable by the UI.

    Converts lists to pandas.DataFrame where convenient for display.
    """
    medicines_df = pd.DataFrame([
        {"Medicine": m["medicine_name"], "Dosage": m["dosage"], "Time": m["time"], "Status": m["status"]}
        for m in medicines
    ])

    # Keep alerts as list of dicts for UI compatibility
    alerts_struct = [{"type": "warning" if "Missed" in a or "Low battery" in a else "info", "text": a} for a in alerts]

    # Trends DataFrame
    trends = pd.DataFrame({
        "time": chart_times,
        "heart_rate": chart_heart_rate,
        "spo2": chart_spo2,
        "temperature": chart_temperature,
    })

    return {
        "patient": patient,
        "metrics": health_metrics,
        "medicines": medicines_df,
        "alerts": alerts_struct,
        "ai": ai_recommendations,
        "trends": trends,
    }

