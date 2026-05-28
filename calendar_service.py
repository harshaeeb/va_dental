from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    def __init__(self):
        # Prefer inline JSON env var (Railway) over file path (Cloud Run / local)
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            import json as _json
            creds = service_account.Credentials.from_service_account_info(
                _json.loads(creds_json), scopes=SCOPES
            )
        else:
            creds = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_CREDENTIALS_PATH"), scopes=SCOPES
            )
        self.service = build("calendar", "v3", credentials=creds)
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        self.timezone = os.getenv("CLINIC_TIMEZONE", "America/Chicago")

    def get_available_slots(self, date_str: str, duration_minutes: int) -> list[str]:
        """
        Returns up to 6 available start times as human-readable strings.
        Checks business hours 8 AM–5 PM, with 15-minute buffer between appointments.
        """
        date = datetime.strptime(date_str, "%Y-%m-%d")
        day_start = date.replace(hour=8, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=17, minute=0, second=0, microsecond=0)

        events_result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=day_start.isoformat() + "Z",
                timeMax=day_end.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        busy_blocks = [
            (
                datetime.fromisoformat(e["start"]["dateTime"].replace("Z", "")),
                datetime.fromisoformat(e["end"]["dateTime"].replace("Z", "")),
            )
            for e in events_result.get("items", [])
            if "dateTime" in e.get("start", {})
        ]

        available = []
        slot_start = day_start
        while slot_start + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            buffered_end = slot_end + timedelta(minutes=15)
            is_free = all(
                buffered_end <= busy_start or slot_start >= busy_end
                for busy_start, busy_end in busy_blocks
            )
            if is_free:
                available.append(slot_start.strftime("%-I:%M %p"))
            slot_start += timedelta(minutes=30)

        return available[:6]

    def book_appointment(
        self,
        patient_name: str,
        patient_phone: str,
        service: str,
        date_str: str,
        time_str: str,
        duration_minutes: int,
    ) -> dict:
        """Creates the Google Calendar event. Returns confirmation dict."""
        dt_str = f"{date_str} {time_str}"
        start_dt = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"{service} — {patient_name}",
            "description": (
                f"Patient: {patient_name}\n"
                f"Phone: {patient_phone}\n"
                f"Service: {service}\n"
                f"Booked via: Voice Agent"
            ),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": self.timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": self.timezone},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 1440},
                    {"method": "popup", "minutes": 60},
                ],
            },
        }

        result = (
            self.service.events()
            .insert(calendarId=self.calendar_id, body=event)
            .execute()
        )

        return {
            "event_id": result["id"],
            "confirmed": True,
            "summary": f"{patient_name} booked for {service} on {date_str} at {time_str}",
        }
