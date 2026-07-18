"""
Run this script ONCE after Railway deployment to register Aria in Vapi.ai.

Prerequisites:
  1. .env file is populated with VAPI_API_KEY
  2. SERVER_URL below is updated to your Railway deployment URL

Usage:
  cd va_dental
  python vapi_setup/create_assistant.py

On success, it prints your assistant ID. Copy it — you'll need it to assign
the assistant to a phone number in the Vapi dashboard.
"""

import httpx
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from config import build_system_prompt

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
if not VAPI_API_KEY:
    print("ERROR: VAPI_API_KEY not set in .env")
    sys.exit(1)

SUPERVISOR_PHONE = os.getenv("SUPERVISOR_PHONE", "+14699825114")

SERVER_URL = "https://vadental-production.up.railway.app/vapi/tool-call"

HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

APPT_TYPE_ENUM = ["cleaning", "checkup", "emergency", "consultation", "whitening", "other"]

# Tools defined inline — avoids toolIds routing issues in Vapi
INLINE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check available appointment slots at the dental clinic for a given "
                "service type and date range. Always call this before booking to find "
                "slots to offer the caller. Convert relative dates ('next Monday', "
                "'this week') to YYYY-MM-DD before calling."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_type": {
                        "type": "string",
                        "enum": APPT_TYPE_ENUM,
                        "description": "Type of dental service requested",
                    },
                    "preferred_date_start": {
                        "type": "string",
                        "description": "Earliest acceptable date, YYYY-MM-DD",
                    },
                    "preferred_date_end": {
                        "type": "string",
                        "description": (
                            "Latest acceptable date, YYYY-MM-DD. "
                            "If caller gives a single day, set this equal to preferred_date_start."
                        ),
                    },
                    "preferred_time_window": {
                        "type": "string",
                        "enum": ["morning", "afternoon", "any"],
                        "description": "Caller's preferred time of day, if stated",
                    },
                },
                "required": ["appointment_type", "preferred_date_start", "preferred_date_end"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {"type": "request-start", "content": "Let me check what's available for you..."},
            {
                "type": "request-failed",
                "content": "I'm having trouble checking the calendar. Let me have someone call you back.",
            },
        ],
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a confirmed appointment for a patient. Only call this after the "
                "caller has explicitly confirmed a specific slot from check_availability results. "
                "Collect first name, last name, and phone number before calling."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {
                        "type": "string",
                        "description": "The slot identifier returned by check_availability (in [slot:...] brackets)",
                    },
                    "patient_first_name": {"type": "string", "description": "Patient's first name"},
                    "patient_last_name": {"type": "string", "description": "Patient's last name"},
                    "patient_phone": {"type": "string", "description": "Patient's callback phone number"},
                    "appointment_type": {
                        "type": "string",
                        "enum": APPT_TYPE_ENUM,
                        "description": "Type of dental service",
                    },
                    "is_new_patient": {
                        "type": "boolean",
                        "description": "True if the caller has not been to this clinic before",
                    },
                    "patient_date_of_birth": {
                        "type": "string",
                        "description": "YYYY-MM-DD — ask only if caller volunteers it or is a new patient",
                    },
                    "patient_email": {
                        "type": "string",
                        "description": "Email address — ask only if caller volunteers it",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional context from the caller, e.g. specific concern",
                    },
                },
                "required": [
                    "slot_id",
                    "patient_first_name",
                    "patient_last_name",
                    "patient_phone",
                    "appointment_type",
                    "is_new_patient",
                ],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {"type": "request-start", "content": "Let me book that for you now..."},
            {
                "type": "request-failed",
                "content": "I wasn't able to complete the booking. Our team will call you to confirm.",
            },
        ],
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": (
                "Move an existing appointment to a new date and time. "
                "First call check_availability to find a new slot, confirm it with the caller, "
                "then call this tool. Do NOT call cancel_appointment separately — this tool handles it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number — used to locate the existing appointment",
                    },
                    "current_appointment_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD of the appointment being moved, to disambiguate",
                    },
                    "current_appointment_id": {
                        "type": "string",
                        "description": "Booking ID from the original confirmation, if the caller has it",
                    },
                    "new_slot_id": {
                        "type": "string",
                        "description": "The new slot identifier from check_availability",
                    },
                    "appointment_type": {
                        "type": "string",
                        "enum": APPT_TYPE_ENUM,
                    },
                    "patient_first_name": {"type": "string"},
                    "patient_last_name": {"type": "string"},
                },
                "required": ["patient_phone", "new_slot_id", "appointment_type"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {"type": "request-start", "content": "Let me move that appointment for you..."},
            {
                "type": "request-failed",
                "content": "I wasn't able to reschedule that appointment. Please call us directly.",
            },
        ],
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": (
                "Cancel an existing appointment. Always confirm the appointment details "
                "verbally with the caller before calling this — cancellation requires "
                "staff follow-up to reverse."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's phone number — used to look up the appointment",
                    },
                    "appointment_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD of the appointment to cancel",
                    },
                    "appointment_id": {
                        "type": "string",
                        "description": "Booking ID from the original confirmation, if available",
                    },
                    "cancellation_reason": {
                        "type": "string",
                        "description": "Optional — only include if the caller volunteers a reason",
                    },
                },
                "required": ["patient_phone", "appointment_date"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {"type": "request-start", "content": "Let me cancel that appointment..."},
            {
                "type": "request-failed",
                "content": "I wasn't able to cancel that appointment. Please call us directly to cancel.",
            },
        ],
    },
    {
        "type": "function",
        "function": {
            "name": "take_message",
            "description": "Record a message from the caller to be passed to clinic staff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_name": {"type": "string", "description": "Caller's full name"},
                    "caller_phone": {"type": "string", "description": "Best callback number"},
                    "message": {"type": "string", "description": "The message content"},
                },
                "required": ["caller_name", "caller_phone", "message"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {"type": "request-start", "content": "Got it, let me note that down..."},
        ],
    },
    {
        "type": "transferCall",
        "function": {
            "name": "transfer_to_supervisor",
            "description": (
                "Transfer the caller to a live team member. Use this ONLY when: "
                "(1) the caller asks to speak to a person, representative, supervisor, or the doctor, or "
                "(2) you are unable to book or confirm an appointment due to a calendar or system error."
            ),
        },
        "destinations": [
            {
                "type": "number",
                "number": SUPERVISOR_PHONE,
                "message": "Please hold for just a moment — I'm connecting you with a team member right now.",
                "description": "Clinic supervisor",
            }
        ],
    },
]


def main():
    assistant_config = {
        "name": "Waterfront Family Dentistry Receptionist",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "systemPrompt": build_system_prompt(),
            "temperature": 0.4,
            "tools": INLINE_TOOLS,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
        },
        "firstMessage": (
            "Thank you for calling Waterfront Family Dentistry! This is Aria. "
            "How can I help you today?"
        ),
        "endCallMessage": "Thank you for calling Waterfront Family Dentistry. Have a wonderful day!",
        "endCallPhrases": ["goodbye", "bye", "that's all", "thank you bye", "no that's all"],
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundDenoisingEnabled": True,
    }

    print("Creating assistant with inline tools...")
    resp = httpx.post(
        "https://api.vapi.ai/assistant", headers=HEADERS, json=assistant_config, timeout=30.0
    )
    if not resp.is_success:
        print(f"  ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    assistant = resp.json()
    assistant_id = assistant["id"]

    print(f"\n{'='*60}")
    print(f"  Assistant created successfully!")
    print(f"  Assistant ID: {assistant_id}")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("  1. Go to https://dashboard.vapi.ai -> Phone Numbers")
    print("  2. Click your number -> Inbound Settings")
    print("  3. Set Assistant to: Waterfront Family Dentistry Receptionist")
    print("  4. Save — your agent is live!")


if __name__ == "__main__":
    main()
