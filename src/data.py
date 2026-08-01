import pandas as pd


def get_all_dummy_data():
    """Return clean empty structures for unauthenticated or initial session state.

    No hardcoded demo or patient records exist in this system.
    """
    return {
        "patient": None,
        "metrics": {},
        "medicines": pd.DataFrame(columns=["Medicine", "Dosage", "Time", "Status"]),
        "alerts": [],
        "ai": [],
        "trends": pd.DataFrame(columns=["time", "heart_rate", "spo2", "temperature"]),
    }
