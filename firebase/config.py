import os
from typing import Any

# Load environment variables from .env file if it exists
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception:
        pass

try:
    # pyrefly: ignore [missing-import]
    import firebase_admin
    # pyrefly: ignore [missing-import]
    from firebase_admin import auth, credentials, firestore
except Exception:
    firebase_admin = None
    auth = None
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


def get_firebase_auth() -> Any:
    """Return firebase_admin.auth module when Firebase is initialized."""
    initialize_firebase()
    if firebase_admin is None or auth is None:
        return None
    if getattr(firebase_admin, "_apps", None):
        return auth
    return None


def get_firebase_web_api_key() -> str:
    """Return Firebase Web API Key for client REST authentication."""
    key = (
        os.getenv("FIREBASE_WEB_API_KEY")
        or os.getenv("FIREBASE_API_KEY")
        or os.getenv("WEB_API_KEY")
        or ""
    )
    return key


def get_firebase_project_id() -> str:
    """Return Firebase Project ID."""
    proj = (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("PROJECT_ID")
        or os.getenv("GCP_PROJECT")
        or ""
    )
    if proj:
        return proj

    # Check if project ID is in service account filename
    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    if sa_path and "-firebase-adminsdk" in sa_path:
        base = os.path.basename(sa_path)
        proj_part = base.split("-firebase-adminsdk")[0]
        if proj_part:
            return proj_part

    return "smart-medicine-box-51870"


