import json
import os
from abc import ABC, abstractmethod
from datetime import datetime


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class PMSBackend(ABC):
    @abstractmethod
    def get_availability(self, args: dict) -> str: ...

    @abstractmethod
    def book_appointment(self, args: dict) -> str: ...

    @abstractmethod
    def cancel_appointment(self, args: dict) -> str: ...

    def reschedule_appointment(self, args: dict) -> str:
        # Default: cancel existing then book new slot
        self.cancel_appointment({
            "patient_phone": args.get("patient_phone", ""),
            "appointment_date": args.get("current_appointment_date", ""),
            "appointment_id": args.get("current_appointment_id"),
        })
        return self.book_appointment({**args, "slot_id": args.get("new_slot_id", "")})


# ---------------------------------------------------------------------------
# Google Calendar backend (existing behaviour, refactored)
# ---------------------------------------------------------------------------

class GoogleCalendarBackend(PMSBackend):

    def _service_durations(self) -> dict:
        with open("data/waterfront_faqs.json") as f:
            faq = json.load(f)
        return {s["name"].lower(): s["duration_minutes"] for s in faq["services"]}

    def _duration_for(self, appointment_type: str) -> int:
        durations = self._service_durations()
        direct = durations.get(appointment_type.lower())
        if direct:
            return direct
        fallbacks = {
            "cleaning": 60, "checkup": 60, "emergency": 30,
            "consultation": 30, "whitening": 90,
        }
        return fallbacks.get(appointment_type.lower(), 45)

    def _calendar(self):
        from calendar_service import CalendarService
        if not hasattr(self, "_cal"):
            self._cal = CalendarService()
        return self._cal

    def get_availability(self, args: dict) -> str:
        date_str = args.get("preferred_date_start") or args.get("date", "")
        appt_type = args.get("appointment_type", "other")
        duration = self._duration_for(appt_type)

        slots = self._calendar().get_available_slots(
            date_str=date_str, duration_minutes=duration
        )
        if not slots:
            return (
                f"No availability found on {date_str}. "
                "Suggest the caller try the next business day."
            )
        # Encode date+24h-time into slot_id so book_appointment can parse it
        formatted = []
        for display in slots[:3]:
            slot_id = f"{date_str}T{_to_24h(display)}"
            formatted.append(f"{display} [slot:{slot_id}]")
        return "I have openings at " + ", or ".join(formatted) + " — which works best?"

    def book_appointment(self, args: dict) -> str:
        slot_id = args.get("slot_id", "")
        if "T" in slot_id and slot_id.startswith("20"):
            # slot_id encoded as "YYYY-MM-DDTHH:MM"
            date_str, time_24 = slot_id.split("T", 1)
            time_str = _to_12h(time_24)
        else:
            date_str = args.get("preferred_date_start") or args.get("date", "")
            time_str = args.get("appointment_time", "")

        first = args.get("patient_first_name", "")
        last = args.get("patient_last_name", "")
        patient_name = args.get("patient_name") or f"{first} {last}".strip()
        patient_phone = args.get("patient_phone", "")
        appt_type = args.get("appointment_type", "appointment")
        duration = self._duration_for(appt_type)

        confirmation = self._calendar().book_appointment(
            patient_name=patient_name,
            patient_phone=patient_phone,
            service=appt_type,
            date_str=date_str,
            time_str=time_str,
            duration_minutes=duration,
        )
        return (
            f"Appointment confirmed! {patient_name} is booked for {appt_type} "
            f"on {date_str} at {time_str}. Booking ID: {confirmation['event_id']}"
        )

    def cancel_appointment(self, args: dict) -> str:
        event_id = args.get("appointment_id") or args.get("event_id")
        if not event_id:
            return (
                "I need the Booking ID to cancel via calendar. "
                "Please call the clinic directly to cancel."
            )
        self._calendar().cancel_appointment(event_id=event_id)
        return "The appointment has been cancelled successfully."


# ---------------------------------------------------------------------------
# NexHealth backend
# ---------------------------------------------------------------------------

class NexHealthBackend(PMSBackend):

    def get_availability(self, args: dict) -> str:
        from nexhealth.appointments import get_availability
        return get_availability(
            appointment_type=args.get("appointment_type", "other"),
            date_start=args.get("preferred_date_start") or args.get("date", ""),
            date_end=(
                args.get("preferred_date_end")
                or args.get("preferred_date_start")
                or args.get("date", "")
            ),
            preferred_time_window=args.get("preferred_time_window", "any"),
        )

    def book_appointment(self, args: dict) -> str:
        from nexhealth.patients import find_or_create_patient
        from nexhealth.appointments import create_appointment

        patient_id = find_or_create_patient(
            first_name=args.get("patient_first_name", ""),
            last_name=args.get("patient_last_name", ""),
            phone=args.get("patient_phone", ""),
            email=args.get("patient_email"),
            date_of_birth=args.get("patient_date_of_birth"),
            is_new_patient=args.get("is_new_patient", False),
        )

        slot_id = args.get("slot_id", "").lstrip("slot:")
        result = create_appointment(
            slot_id=slot_id,
            patient_id=patient_id,
            appointment_type=args.get("appointment_type", "other"),
            notes=args.get("notes"),
        )

        first = args.get("patient_first_name", "")
        last = args.get("patient_last_name", "")
        name = f"{first} {last}".strip()
        return (
            f"Appointment confirmed in the scheduling system! {name} is booked for "
            f"{args.get('appointment_type')} on {result['start_time']} "
            f"with {result['provider']}. Booking ID: {result['appointment_id']}"
        )

    def cancel_appointment(self, args: dict) -> str:
        from nexhealth.appointments import find_appointment, cancel_by_id

        appt_id = args.get("appointment_id")
        if not appt_id:
            appt_id = find_appointment(
                patient_phone=args.get("patient_phone", ""),
                appointment_date=args.get("appointment_date", ""),
            )
        if not appt_id:
            return (
                "I wasn't able to locate that appointment in the scheduling system. "
                "Please have a team member assist directly."
            )
        cancel_by_id(appt_id)
        return "The appointment has been cancelled successfully in the scheduling system."


# ---------------------------------------------------------------------------
# Dual backend — NexHealth primary, Google Calendar mirror
# ---------------------------------------------------------------------------

class DualBackend(PMSBackend):
    def __init__(self, primary: NexHealthBackend, secondary: GoogleCalendarBackend):
        self._primary = primary
        self._secondary = secondary

    def get_availability(self, args: dict) -> str:
        try:
            return self._primary.get_availability(args)
        except Exception as e:
            print(f"[NEXHEALTH] Availability failed, falling back to Google Calendar: {e}")
            return self._secondary.get_availability(args)

    def book_appointment(self, args: dict) -> str:
        primary_result = None
        try:
            primary_result = self._primary.book_appointment(args)
        except Exception as e:
            print(f"[NEXHEALTH] Booking failed: {e}")

        # Mirror to Google Calendar regardless of NexHealth outcome
        try:
            self._secondary.book_appointment(args)
            print("[GCAL] Mirror booking created.")
        except Exception as e:
            print(f"[GCAL] Mirror booking failed: {e}")

        if primary_result:
            return primary_result
        # NexHealth failed — try GCal as full fallback
        try:
            return self._secondary.book_appointment(args)
        except Exception:
            return (
                "I wasn't able to complete the booking right now. "
                "Our team will follow up with you shortly to confirm."
            )

    def cancel_appointment(self, args: dict) -> str:
        result = None
        try:
            result = self._primary.cancel_appointment(args)
        except Exception as e:
            print(f"[NEXHEALTH] Cancel failed: {e}")
        try:
            self._secondary.cancel_appointment(args)
        except Exception as e:
            print(f"[GCAL] Cancel failed: {e}")
        return result or "The appointment has been cancelled."


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_backend() -> PMSBackend:
    mode = os.getenv("PMS_BACKEND", "google").lower()
    if mode == "nexhealth":
        return NexHealthBackend()
    if mode == "dual":
        return DualBackend(NexHealthBackend(), GoogleCalendarBackend())
    return GoogleCalendarBackend()


# ---------------------------------------------------------------------------
# Time helpers (used only by GoogleCalendarBackend)
# ---------------------------------------------------------------------------

def _to_24h(time_12h: str) -> str:
    """'10:00 AM' → '10:00'"""
    try:
        return datetime.strptime(time_12h.strip(), "%I:%M %p").strftime("%H:%M")
    except Exception:
        return time_12h


def _to_12h(time_24h: str) -> str:
    """'10:00' → '10:00 AM'"""
    try:
        return datetime.strptime(time_24h.strip(), "%H:%M").strftime("%-I:%M %p")
    except Exception:
        return time_24h
