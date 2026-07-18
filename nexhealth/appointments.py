from datetime import datetime
from nexhealth import client

# Maps Aria's appointment_type values to NexHealth appointment type names
_TYPE_NAME_MAP = {
    "cleaning": "routine cleaning",
    "checkup": "preventive exam",
    "emergency": "emergency visit",
    "consultation": "consultation",
    "whitening": "teeth whitening",
}

_appt_type_cache: dict = {}


def _get_appt_type_id(appointment_type: str) -> str | None:
    global _appt_type_cache
    if not _appt_type_cache:
        result = client.get("/appointment_types")
        types = result.get("data", {}).get("appointment_types", [])
        _appt_type_cache = {t["name"].lower(): str(t["id"]) for t in types}

    target = _TYPE_NAME_MAP.get(appointment_type.lower(), appointment_type.lower())
    for name, tid in _appt_type_cache.items():
        if target in name or name in target:
            return tid
    # Fallback: return first available type ID
    return next(iter(_appt_type_cache.values()), None)


def _format_slot(slot: dict) -> str:
    iso = slot.get("time") or slot.get("start_time", "")
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%A, %B %-d at %-I:%M %p")
    except Exception:
        return iso


def _hour_of(slot: dict) -> int:
    iso = slot.get("time") or slot.get("start_time", "")
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).hour
    except Exception:
        return -1


def _filter_window(slots: list, window: str) -> list:
    windows = {"morning": (8, 12), "afternoon": (12, 17), "evening": (17, 21)}
    if window not in windows:
        return slots
    lo, hi = windows[window]
    return [s for s in slots if lo <= _hour_of(s) < hi]


def get_availability(
    appointment_type: str,
    date_start: str,
    date_end: str,
    preferred_time_window: str = "any",
) -> str:
    appt_type_id = _get_appt_type_id(appointment_type)
    params = {"start_date": date_start, "end_date": date_end, "per_page": 20}
    if appt_type_id:
        params["appointment_type_id"] = appt_type_id

    result = client.get("/appointment_slots", params=params)
    slots = result.get("data", {}).get("appointment_slots", [])

    if not slots:
        return (
            f"No availability found between {date_start} and {date_end}. "
            "Would you like me to check a different date range?"
        )

    if preferred_time_window and preferred_time_window != "any":
        filtered = _filter_window(slots, preferred_time_window)
        if filtered:
            slots = filtered

    top = slots[:3]
    formatted = []
    for slot in top:
        provider = (slot.get("provider") or {}).get("name", "our team")
        slot_id = str(slot["id"])
        formatted.append(f"{_format_slot(slot)} with {provider} [slot:{slot_id}]")

    return "I found these openings: " + ", or ".join(formatted) + ". Which works best for you?"


def create_appointment(
    slot_id: str,
    patient_id: str,
    appointment_type: str,
    notes: str = None,
) -> dict:
    appt_type_id = _get_appt_type_id(appointment_type)
    body: dict = {
        "appointment": {
            "appointment_slot_id": slot_id,
            "patient_id": patient_id,
        }
    }
    if appt_type_id:
        body["appointment"]["appointment_type_id"] = appt_type_id
    if notes:
        body["appointment"]["notes"] = notes

    result = client.post("/appointments", body)
    appt = result.get("data", {}).get("appointment", {})
    return {
        "appointment_id": str(appt.get("id", "")),
        "start_time": appt.get("start_time", ""),
        "provider": (appt.get("provider") or {}).get("name", ""),
    }


def find_appointment(patient_phone: str, appointment_date: str) -> str | None:
    """Find an appointment ID by patient phone and date (for cancel/reschedule)."""
    result = client.get("/appointments", params={
        "start_date": appointment_date,
        "end_date": appointment_date,
        "per_page": 20,
    })
    appointments = result.get("data", {}).get("appointments", [])
    clean_phone = "".join(c for c in patient_phone if c.isdigit())
    for appt in appointments:
        p_phone = "".join(
            c for c in (appt.get("patient") or {}).get("phone", "") if c.isdigit()
        )
        if clean_phone and clean_phone in p_phone:
            return str(appt["id"])
    return None


def cancel_by_id(appointment_id: str) -> None:
    client.delete(f"/appointments/{appointment_id}")
