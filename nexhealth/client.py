import os
import httpx
from nexhealth.auth import get_bearer_token

BASE_URL = os.getenv("NEXHEALTH_BASE_URL", "https://nexhealth.info")
API_VERSION = os.getenv("NEXHEALTH_API_VERSION", "v20240412")
SUBDOMAIN = os.getenv("NEXHEALTH_SUBDOMAIN", "")
LOCATION_ID = os.getenv("NEXHEALTH_LOCATION_ID", "")
TIMEOUT = 5.0


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_bearer_token()}",
        "Nex-Api-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def _base_params() -> dict:
    return {"subdomain": SUBDOMAIN, "location_id": LOCATION_ID}


def get(path: str, params: dict = None) -> dict:
    p = _base_params()
    if params:
        p.update(params)
    resp = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=p, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def post(path: str, body: dict) -> dict:
    resp = httpx.post(
        f"{BASE_URL}{path}", headers=_headers(), params=_base_params(), json=body, timeout=TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def patch(path: str, body: dict) -> dict:
    resp = httpx.patch(
        f"{BASE_URL}{path}",
        headers=_headers(),
        params={"subdomain": SUBDOMAIN},
        json=body,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def delete(path: str) -> dict:
    resp = httpx.delete(
        f"{BASE_URL}{path}",
        headers=_headers(),
        params={"subdomain": SUBDOMAIN},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
