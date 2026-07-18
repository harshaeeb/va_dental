from nexhealth import client


def find_or_create_patient(
    first_name: str,
    last_name: str,
    phone: str,
    email: str = None,
    date_of_birth: str = None,
    is_new_patient: bool = False,
) -> str:
    """Return NexHealth patient ID, creating the patient record if not found."""
    if not is_new_patient:
        # Search by phone, then verify last name matches
        clean_phone = "".join(c for c in phone if c.isdigit())
        result = client.get("/patients", params={"phone": clean_phone, "per_page": 10})
        patients = result.get("data", {}).get("patients", [])
        for p in patients:
            if (p.get("last_name") or "").lower() == last_name.lower():
                return str(p["id"])

    body: dict = {
        "patient": {
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
        }
    }
    if email:
        body["patient"]["email"] = email
    if date_of_birth:
        body["patient"]["date_of_birth"] = date_of_birth

    result = client.post("/patients", body)
    return str(result["data"]["patient"]["id"])
