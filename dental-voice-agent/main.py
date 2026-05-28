from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import os

load_dotenv()

app = FastAPI(title="Bright Smile Dental Voice Agent")

# Pre-load service durations for lookup by name
with open("data/faqs.json") as f:
    FAQ_DATA = json.load(f)

SERVICE_DURATIONS: dict[str, int] = {
    s["name"].lower(): s["duration_minutes"] for s in FAQ_DATA["services"]
}

# Lazy-load CalendarService only when Google credentials are available
_calendar = None


def get_calendar():
    global _calendar
    if _calendar is None:
        has_json = bool(os.getenv("GOOGLE_CREDENTIALS_JSON"))
        has_file = bool(os.getenv("GOOGLE_CREDENTIALS_PATH")) and os.path.exists(
            os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        )
        if not has_json and not has_file:
            raise RuntimeError(
                "Google credentials not configured. "
                "Set GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS_PATH."
            )
        from calendar_service import CalendarService
        _calendar = CalendarService()
    return _calendar


@app.get("/health")
def health():
    return {"status": "ok", "clinic": os.getenv("CLINIC_NAME", "Bright Smile Dental")}


@app.post("/vapi/tool-call")
async def handle_tool_call(request: Request):
    body = await request.json()
    message = body.get("message", {})
    tool_calls = message.get("toolCallList", [])

    results = []
    for call in tool_calls:
        tool_name = call.get("name")
        args = call.get("arguments", {})
        call_id = call.get("id")

        try:
            if tool_name == "check_availability":
                slots = get_calendar().get_available_slots(
                    date_str=args["date"],
                    duration_minutes=args["duration_minutes"],
                )
                if slots:
                    result_text = (
                        f"Available slots on {args['date']}: {', '.join(slots)}"
                    )
                else:
                    result_text = (
                        f"No availability found on {args['date']}. "
                        "Suggest the caller try the next business day."
                    )

            elif tool_name == "book_appointment":
                service_key = args["service"].lower()
                duration = SERVICE_DURATIONS.get(service_key, 30)

                get_calendar().book_appointment(
                    patient_name=args["patient_name"],
                    patient_phone=args["patient_phone"],
                    service=args["service"],
                    date_str=args["date"],
                    time_str=args["time"],
                    duration_minutes=duration,
                )
                result_text = (
                    f"Appointment confirmed! {args['patient_name']} is booked for "
                    f"{args['service']} on {args['date']} at {args['time']}."
                )

            elif tool_name == "take_message":
                print(
                    f"[MESSAGE] From: {args.get('caller_name')} "
                    f"({args.get('caller_phone')}) — {args.get('message')}"
                )
                result_text = "Message recorded. A team member will follow up shortly."

            else:
                result_text = f"Unknown tool '{tool_name}'."

        except Exception as e:
            print(f"[ERROR] Tool '{tool_name}' failed: {e}")
            result_text = (
                "I wasn't able to complete that action right now. "
                "I'll have someone from our team follow up with you directly."
            )

        results.append({"toolCallId": call_id, "result": result_text})

    return JSONResponse({"results": results})
