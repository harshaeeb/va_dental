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

# ── UPDATE THIS after Railway deployment ──────────────────────────────────────────────────────────
SERVER_URL = "https://vadental-production.up.railway.app/vapi/tool-call"
# ────────────────────────────────────────────────────────────────────────────────
HEADERS = {
    "Authorization": f"Bearer {VAPI_API_KEY}",
    "Content-Type": "application/json",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check available appointment slots at the dental clinic "
                "for a specific date and service duration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to check, in YYYY-MM-DD format",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Length of the appointment in minutes",
                    },
                },
                "required": ["date", "duration_minutes"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {
                "type": "request-start",
                "content": "Let me check what's available for you...",
            },
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
            "description": "Book a confirmed appointment for a patient at the dental clinic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Full name of the patient",
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient's callback phone number",
                    },
                    "service": {
                        "type": "string",
                        "description": "Name of the dental service",
                    },
                    "date": {
                        "type": "string",
                        "description": "Appointment date in YYYY-MM-DD format",
                    },
                    "time": {
                        "type": "string",
                        "description": "Appointment time, e.g. '2:00 PM'",
                    },
                },
                "required": [
                    "patient_name",
                    "patient_phone",
                    "service",
                    "date",
                    "time",
                ],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {
                "type": "request-start",
                "content": "Let me book that for you now...",
            },
            {
                "type": "request-failed",
                "content": "I wasn't able to complete the booking. Our team will call you to confirm.",
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
                    "caller_name": {
                        "type": "string",
                        "description": "Caller's full name",
                    },
                    "caller_phone": {
                        "type": "string",
                        "description": "Best callback number",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message content",
                    },
                },
                "required": ["caller_name", "caller_phone", "message"],
            },
        },
        "server": {"url": SERVER_URL},
        "messages": [
            {
                "type": "request-start",
                "content": "Got it, let me note that down...",
            },
        ],
    },
]


def main():
    print("Creating Vapi tools...")
    tool_ids = []
    for tool in TOOLS:
        resp = httpx.post("https://api.vapi.ai/tool", headers=HEADERS, json=tool, timeout=30.0)
        if not resp.is_success:
            print(f"  ERROR {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        tid = resp.json()["id"]
        tool_ids.append(tid)
        print(f"  ✓ {tool['function']['name']} → {tid}")

    assistant_config = {
        "name": "Bright Smile Dental Receptionist",
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "systemPrompt": build_system_prompt(),
            "temperature": 0.4,
            "toolIds": tool_ids,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
        },
        "firstMessage": (
            "Thank you for calling Bright Smile Dental! This is Aria. "
            "How can I help you today?"
        ),
        "endCallMessage": (
            "Thank you for calling Bright Smile Dental. Have a wonderful day!"
        ),
        "endCallPhrases": [
            "goodbye",
            "bye",
            "that's all",
            "thank you bye",
            "no that's all",
        ],
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "backgroundDenoisingEnabled": True,
        "serverUrl": SERVER_URL,
    }

    print("\nCreating assistant...")
    resp = httpx.post(
        "https://api.vapi.ai/assistant", headers=HEADERS, json=assistant_config, timeout=30.0
    )
    if not resp.is_success:
        print(f"  ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    assistant = resp.json()
    assistant_id = assistant["id"]

    print(f"\n{'='*60}")
    print(f"  ✓ Assistant created successfully!")
    print(f"  Assistant ID: {assistant_id}")
    print(f"{'='*60}")
    print("\nNext step:")
    print("  1. Go to https://dashboard.vapi.ai → Phone Numbers")
    print("  2. Click your number → Inbound Settings")
    print(f"  3. Set Assistant to: Bright Smile Dental Receptionist")
    print("  4. Save — your agent is live!")


if __name__ == "__main__":
    main()
