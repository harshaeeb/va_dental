import os
import time
import httpx

_token_cache: dict = {"token": None, "expires_at": 0.0}

BASE_URL = os.getenv("NEXHEALTH_BASE_URL", "https://nexhealth.info")
API_VERSION = os.getenv("NEXHEALTH_API_VERSION", "v20240412")


def get_bearer_token() -> str:
    now = time.time()
    # Refresh 5 minutes before expiry
    if _token_cache["token"] and now < _token_cache["expires_at"] - 300:
        return _token_cache["token"]

    api_key = os.getenv("NEXHEALTH_API_KEY")
    if not api_key:
        raise RuntimeError("NEXHEALTH_API_KEY not set")

    resp = httpx.post(
        f"{BASE_URL}/authenticates",
        headers={"Nex-Api-Version": API_VERSION, "Authorization": api_key},
        timeout=10.0,
    )
    resp.raise_for_status()
    token = resp.json()["data"]["token"]
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + 3600
    return token
