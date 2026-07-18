from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import os

load_dotenv()

app = FastAPI(title="Waterfront Family Dentistry Voice Agent")

# Lazy-load PMS backend — Google Calendar, NexHealth, or Dual (set via PMS_BACKEND env var)
_pms = None


def get_pms():
    global _pms
    if _pms is None:
        from pms.backend import get_backend
        _pms = get_backend()
    return _pms


@app.get("/health")
def health():
    return {
        "status": "ok",
        "clinic": os.getenv("CLINIC_NAME", "Waterfront Family Dentistry"),
        "pms_backend": os.getenv("PMS_BACKEND", "google"),
    }


@app.post("/vapi/tool-call")
async def handle_tool_call(request: Request):
    body = await request.json()
    message = body.get("message", {})

    # Support both inline tool format (function.name) and pre-created tool format (name)
    raw_calls = message.get("toolCallList", [])

    results = []
    for call in raw_calls:
        if "function" in call:
            tool_name = call["function"].get("name")
            raw_args = call["function"].get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except Exception:
                    raw_args = {}
            args = raw_args
        else:
            tool_name = call.get("name")
            args = call.get("arguments", {})
        call_id = call.get("id")

        try:
            if tool_name == "check_availability":
                result_text = get_pms().get_availability(args)

            elif tool_name == "book_appointment":
                result_text = get_pms().book_appointment(args)

            elif tool_name == "cancel_appointment":
                result_text = get_pms().cancel_appointment(args)

            elif tool_name == "reschedule_appointment":
                result_text = get_pms().reschedule_appointment(args)

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
