import os
from typing import Any

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None


_FIREBASE_APP = None


def initialize_firebase() -> Any:
    """Initialize Firebase Admin SDK if it is available and configured."""
    global _FIREBASE_APP

    if _FIREBASE_APP is not None:
        return _FIREBASE_APP

    if firebase_admin is None or credentials is None or firestore is None:
        return None

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not service_account_path:
        return None

    if not os.path.exists(service_account_path):
        return None

    try:
        cred = credentials.Certificate(service_account_path)
        _FIREBASE_APP = firebase_admin.initialize_app(cred)
        return _FIREBASE_APP
    except Exception:
        return None


def get_firestore_client() -> Any:
    """Return a Firestore client when Firebase is initialized."""
    initialize_firebase()
    if firebase_admin is None or firestore is None:
        return None
    if getattr(firebase_admin, "_apps", None):
        return firestore.client()
    return None
