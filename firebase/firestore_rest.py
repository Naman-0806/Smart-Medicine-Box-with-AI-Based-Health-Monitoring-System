import base64
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
import streamlit as st

from firebase.config import get_firebase_project_id, get_firebase_web_api_key


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Safely decode JWT payload without verifying signature."""
    try:
        parts = token.strip().split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem:
                payload_b64 += "=" * (4 - rem)
            payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
            return json.loads(payload_json)
    except Exception:
        pass
    return {}


def get_jwt_project_id(token: Optional[str] = None) -> Optional[str]:
    """Extract Firebase project_id from ID token payload."""
    if not token:
        try:
            token = st.session_state.get("id_token")
        except Exception:
            token = None
    if not token:
        return None

    payload = _decode_jwt_payload(token)
    if not payload:
        return None

    # Try common Firebase JWT fields
    if "project_id" in payload:
        return str(payload["project_id"])
    if "aud" in payload and not str(payload["aud"]).startswith("http"):
        return str(payload["aud"])
    if "iss" in payload:
        iss = str(payload["iss"])
        if "securetoken.google.com/" in iss:
            return iss.split("securetoken.google.com/")[-1]
    return None


def get_active_project_id() -> str:
    """Get project ID from session state, token, env, or default."""
    try:
        if "project_id" in st.session_state and st.session_state["project_id"]:
            return str(st.session_state["project_id"]).strip()
    except Exception:
        pass

    # Try token
    token_proj = get_jwt_project_id()
    if token_proj:
        try:
            st.session_state["project_id"] = token_proj
        except Exception:
            pass
        return token_proj

    # Try config / env
    proj_id = get_firebase_project_id()
    if proj_id:
        return proj_id

    return "smart-medicine-box-51870"


def refresh_id_token() -> Optional[str]:
    """Refresh expired Firebase ID token using refresh_token."""
    refresh_tok = None
    try:
        refresh_tok = st.session_state.get("refresh_token")
    except Exception:
        pass

    if not refresh_tok:
        return None

    api_key = get_firebase_web_api_key()
    if not api_key:
        return None

    url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            new_id_token = data.get("id_token") or data.get("idToken")
            new_refresh_token = data.get("refresh_token") or data.get("refreshToken") or refresh_tok
            expires_in = int(data.get("expires_in") or data.get("expiresIn") or 3600)

            try:
                st.session_state["id_token"] = new_id_token
                st.session_state["refresh_token"] = new_refresh_token
                st.session_state["token_expires_at"] = time.time() + expires_in
                if "project_id" in data:
                    st.session_state["project_id"] = data["project_id"]
            except Exception:
                pass

            return new_id_token
    except Exception as e:
        print(f"[FIRESTORE REST] Token refresh failed: {e}")

    return None


def get_active_id_token() -> Optional[str]:
    """Return a valid, active ID token from session_state, refreshing if expired."""
    try:
        id_token = st.session_state.get("id_token")
        expires_at = st.session_state.get("token_expires_at", 0)

        # If token is expiring within 60 seconds, refresh it
        if id_token and expires_at and (time.time() > (expires_at - 60)):
            refreshed = refresh_id_token()
            if refreshed:
                return refreshed

        if id_token:
            return id_token
    except Exception:
        pass
    return None


# ----------------------------------------------------------------------
# Serialization Helpers for Firestore REST API
# ----------------------------------------------------------------------

def to_firestore_value(val: Any) -> Dict[str, Any]:
    """Convert Python value to Firestore REST Value JSON."""
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, str):
        return {"stringValue": val}
    if isinstance(val, (list, tuple, set)):
        return {"arrayValue": {"values": [to_firestore_value(v) for v in val]}}
    if isinstance(val, dict):
        return {"mapValue": {"fields": {k: to_firestore_value(v) for k, v in val.items()}}}
    return {"stringValue": str(val)}


def from_firestore_value(field_val: Dict[str, Any]) -> Any:
    """Convert Firestore REST Value JSON to Python value."""
    if not isinstance(field_val, dict):
        return field_val

    if "stringValue" in field_val:
        return field_val["stringValue"]
    if "integerValue" in field_val:
        try:
            return int(field_val["integerValue"])
        except (ValueError, TypeError):
            return field_val["integerValue"]
    if "doubleValue" in field_val:
        try:
            return float(field_val["doubleValue"])
        except (ValueError, TypeError):
            return field_val["doubleValue"]
    if "booleanValue" in field_val:
        return bool(field_val["booleanValue"])
    if "nullValue" in field_val:
        return None
    if "timestampValue" in field_val:
        return field_val["timestampValue"]
    if "arrayValue" in field_val:
        arr = field_val.get("arrayValue", {})
        values = arr.get("values", []) if isinstance(arr, dict) else []
        return [from_firestore_value(v) for v in values]
    if "mapValue" in field_val:
        m = field_val.get("mapValue", {})
        fields = m.get("fields", {}) if isinstance(m, dict) else {}
        return {k: from_firestore_value(v) for k, v in fields.items()}
    if "referenceValue" in field_val:
        return field_val["referenceValue"]

    return None


def to_firestore_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a Python dictionary into Firestore 'fields' object."""
    return {str(k): to_firestore_value(v) for k, v in data.items()}


def from_firestore_doc(doc_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extract Python dictionary from Firestore REST Document JSON."""
    if not isinstance(doc_json, dict):
        return {}

    fields = doc_json.get("fields", {})
    res = {}
    for k, v in fields.items():
        res[k] = from_firestore_value(v)

    # Extract document ID from resource name
    # e.g. "projects/.../databases/(default)/documents/patients/uid"
    name = doc_json.get("name", "")
    if name:
        doc_id = name.split("/")[-1]
        res.setdefault("id", doc_id)

    return res


# ----------------------------------------------------------------------
# Core REST Client Methods
# ----------------------------------------------------------------------

def _get_headers(id_token: Optional[str] = None) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = id_token or get_active_id_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def firestore_get_doc(
    path: str,
    id_token: Optional[str] = None,
    project_id: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Fetch a single Firestore document via REST API.
    Returns (success, data_dict_or_None, error_msg).
    """
    clean_path = path.strip().strip("/")
    proj = project_id or get_active_project_id()
    api_key = get_firebase_web_api_key()

    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{clean_path}"
    params = {}
    if api_key:
        params["key"] = api_key

    headers = _get_headers(id_token)

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        # Handle 401 Unauthorized by attempting token refresh once
        if resp.status_code == 401:
            refreshed_token = refresh_id_token()
            if refreshed_token:
                headers = _get_headers(refreshed_token)
                resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            doc_data = from_firestore_doc(resp.json())
            return True, doc_data, ""
        elif resp.status_code == 404:
            return True, None, "Document not found."
        else:
            err_text = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", err_text)
            except Exception:
                err_msg = err_text
            return False, None, f"Firestore Error ({resp.status_code}): {err_msg}"

    except requests.exceptions.Timeout:
        return False, None, "Network timeout connecting to Cloud Firestore."
    except requests.exceptions.ConnectionError:
        return False, None, "Unable to connect to Cloud Firestore. Check internet connection."
    except Exception as e:
        return False, None, f"Firestore request failed: {e}"


def firestore_set_doc(
    path: str,
    data: Dict[str, Any],
    merge: bool = True,
    id_token: Optional[str] = None,
    project_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Create or update a Firestore document via REST API (PATCH).
    Returns (success, error_msg_if_failed).
    """
    clean_path = path.strip().strip("/")
    proj = project_id or get_active_project_id()
    api_key = get_firebase_web_api_key()

    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{clean_path}"
    params: Dict[str, Any] = {}
    if api_key:
        params["key"] = api_key

    if merge and data:
        # Pass updateMask.fieldPaths for each top-level key to ensure merge behavior
        params["updateMask.fieldPaths"] = list(data.keys())

    headers = _get_headers(id_token)
    payload = {"fields": to_firestore_fields(data)}

    try:
        resp = requests.patch(url, headers=headers, params=params, json=payload, timeout=10)

        # Handle 401 Unauthorized by attempting token refresh once
        if resp.status_code == 401:
            refreshed_token = refresh_id_token()
            if refreshed_token:
                headers = _get_headers(refreshed_token)
                resp = requests.patch(url, headers=headers, params=params, json=payload, timeout=10)

        if resp.status_code == 200:
            return True, ""
        else:
            err_text = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", err_text)
            except Exception:
                err_msg = err_text
            return False, f"Firestore Write Error ({resp.status_code}): {err_msg}"

    except requests.exceptions.Timeout:
        return False, "Network timeout while saving to Cloud Firestore."
    except requests.exceptions.ConnectionError:
        return False, "Unable to connect to Cloud Firestore. Check internet connection."
    except Exception as e:
        return False, f"Firestore write failed: {e}"


def firestore_delete_doc(
    path: str,
    id_token: Optional[str] = None,
    project_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Delete a single Firestore document via REST API.
    Returns (success, error_msg_if_failed).
    """
    clean_path = path.strip().strip("/")
    proj = project_id or get_active_project_id()
    api_key = get_firebase_web_api_key()

    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{clean_path}"
    params = {}
    if api_key:
        params["key"] = api_key

    headers = _get_headers(id_token)

    try:
        resp = requests.delete(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 401:
            refreshed_token = refresh_id_token()
            if refreshed_token:
                headers = _get_headers(refreshed_token)
                resp = requests.delete(url, headers=headers, params=params, timeout=10)

        if resp.status_code in (200, 404):
            return True, ""
        else:
            err_text = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", err_text)
            except Exception:
                err_msg = err_text
            return False, f"Firestore Delete Error ({resp.status_code}): {err_msg}"

    except requests.exceptions.Timeout:
        return False, "Network timeout while deleting from Cloud Firestore."
    except requests.exceptions.ConnectionError:
        return False, "Unable to connect to Cloud Firestore. Check internet connection."
    except Exception as e:
        return False, f"Firestore delete failed: {e}"


def firestore_list_docs(
    collection_path: str,
    id_token: Optional[str] = None,
    project_id: Optional[str] = None,
    page_size: int = 100
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    List all documents in a Firestore collection or subcollection.
    Returns (success, list_of_doc_dicts, error_msg).
    """
    clean_path = collection_path.strip().strip("/")
    proj = project_id or get_active_project_id()
    api_key = get_firebase_web_api_key()

    url = f"https://firestore.googleapis.com/v1/projects/{proj}/databases/(default)/documents/{clean_path}"
    params: Dict[str, Any] = {"pageSize": page_size}
    if api_key:
        params["key"] = api_key

    headers = _get_headers(id_token)

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 401:
            refreshed_token = refresh_id_token()
            if refreshed_token:
                headers = _get_headers(refreshed_token)
                resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            res_json = resp.json()
            raw_docs = res_json.get("documents", [])
            docs = [from_firestore_doc(d) for d in raw_docs if isinstance(d, dict)]
            return True, docs, ""
        elif resp.status_code == 404:
            return True, [], ""
        else:
            err_text = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", err_text)
            except Exception:
                err_msg = err_text
            return False, [], f"Firestore List Error ({resp.status_code}): {err_msg}"

    except requests.exceptions.Timeout:
        return False, [], "Network timeout listing documents from Cloud Firestore."
    except requests.exceptions.ConnectionError:
        return False, [], "Unable to connect to Cloud Firestore. Check internet connection."
    except Exception as e:
        return False, [], f"Firestore list failed: {e}"
