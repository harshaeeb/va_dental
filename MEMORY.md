# Project Memory — VA Dental Voice Agent
*Import this file at the start of a new session to restore full context.*

---

## What This Project Is
A production voice AI receptionist named **Aria** for **Waterfront Family Dentistry** in Frisco, TX.
Aria answers inbound calls via Vapi.ai, checks Google Calendar availability, books/cancels appointments, and takes messages.

---

## Tech Stack
| Layer | Technology |
|-------|----------|
| Voice AI platform | Vapi.ai (inline tools, gpt-4o-mini, Deepgram STT) |
| Backend webhook | Python / FastAPI on Railway |
| Calendar | Google Calendar API (service account) |
| Clinic knowledge | `data/waterfront_faqs.json` |
| Hosting | Railway (auto-deploy from GitHub branch) |

---

## Repository
- **GitHub**: `harshaeeb/va_dental`
- **Active branch**: `claude/quirky-curie-p7FZ2`
- **Railway URL**: https://vadental-production.up.railway.app
- **Local git push is broken** (proxy 403) — always use MCP `mcp__github__push_files` for GitHub writes

---

## Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI server — `/health` + `/vapi/tool-call` webhook |
| `calendar_service.py` | Google Calendar CRUD (get slots, book, cancel) |
| `config.py` | Builds Aria's system prompt from `waterfront_faqs.json` |
| `data/waterfront_faqs.json` | **Active** clinic data — hours, services, FAQs, insurance, loyalty program, providers, technology |
| `data/faqs.json` | Legacy Bright Smile Dental demo data — unused |
| `vapi_setup/create_assistant.py` | One-time script to register Aria in Vapi after deploy |
| `waterfrontsmiles.com/` | Downloaded website HTML — source for knowledge base |

---

## Clinic Details (Waterfront Family Dentistry)
- **Address**: 255 W Lebanon St, Suite 300, Frisco, TX 75036
- **Phone**: 972-987-4343
- **Email**: office@waterfrontsmiles.com / info@waterfrontsmiles.com
- **Hours**: Mon 10–5 | Tue–Thu 9–12 then 1–5 (lunch noon–1) | Fri 8–2 | Sat–Sun Closed
- **Doctor**: Dr. Lavi (Dr. Lavanya Rudrapatna), 20+ years experience
- **Loyalty Program**: 2 cleanings/year, fluoride, X-rays, 1 emergency exam, +50% off extra cleanings, 20% off all treatments

---

## Credentials & Config (non-secret)
- **Google Cloud project**: `va-dental-demo`
- **Service account**: `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com`
- **Google Calendar ID**: `harsha.eeb@gmail.com`
- **Clinic timezone**: `America/Chicago`
- **Vapi API key**: `598d5af2-695a-4c93-9772-4386e22b2867` (also in local `.env`)
- **Google credentials file**: `google-credentials.json` (gitignored — never commit)

### Railway env vars
```
VAPI_API_KEY=598d5af2-695a-4c93-9772-4386e22b2867
GOOGLE_CREDENTIALS_JSON=<full JSON content of google-credentials.json>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Waterfront Family Dentistry
```

---

## Vapi Assistant
- **Name**: Waterfront Family Dentistry Receptionist
- **Assistant ID**: `62e72b31-22e9-4078-b32a-17551f176bfa` *(re-run `create_assistant.py` after prompt changes)*
- **Model**: gpt-4o-mini (OpenAI via Vapi), temperature 0.4
- **Tools**: `check_availability`, `book_appointment`, `cancel_appointment`, `take_message`
- **Tool type**: Inline (in `model.tools`) — NOT pre-created toolIds

---

## Architecture Rules (must preserve)
1. **Inline tools only** — pre-created Vapi toolIds break LLM result routing
2. **No `request-complete` messages** — they cause agent silence after tool calls
3. **`{{currentDateTime}}` in system prompt** — required for correct year in bookings
4. **`cancel_appointment` before rebook** — prevents duplicate calendar events
5. **`replace(tzinfo=None)`** on Google Calendar event datetimes — prevents offset-naive/aware crash
6. **Lazy-load `CalendarService`** — server must start without credentials

---

## Vapi Payload Format (inline tools)
```json
{
  "message": {
    "toolCallList": [{
      "id": "call_xxx",
      "function": {
        "name": "check_availability",
        "arguments": "{\"date\": \"2026-06-01\", \"duration_minutes\": 60}"
      }
    }]
  }
}
```
`arguments` arrives as a **JSON string** — `main.py` parses it with `json.loads()`.

---

## Workflow: After Changing System Prompt
1. Edit `data/waterfront_faqs.json` and/or `config.py`
2. Push to GitHub branch `claude/quirky-curie-p7FZ2`
3. Wait for Railway to redeploy (~30s)
4. Re-run `python vapi_setup/create_assistant.py` to update Vapi assistant
5. Note new Assistant ID and reassign to phone number in Vapi dashboard if changed

## Workflow: Adding a New Clinic
1. Create `data/<clinic>_faqs.json` in same schema as `waterfront_faqs.json`
2. Update `main.py` line 12 and `config.py` line 4 to point to new file
3. Update assistant name/messages in `vapi_setup/create_assistant.py`
4. Push and redeploy

---

## Bugs Fixed (don't reintroduce)
| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Agent silent after "let me check..." | `request-complete` Vapi filler plays, LLM generates empty follow-up | Remove all `request-complete` messages from tool definitions |
| Agent loops 4-5x then hangs | Pre-created toolIds — LLM doesn't receive tool results | Use inline tools in `model.tools` |
| Wrong year (2024) in bookings | LLM uses training data year | Inject `{{currentDateTime}}` into system prompt |
| Duplicate calendar events on reschedule | No cancel tool | `cancel_appointment` tool + rule in system prompt |
| `can't compare offset-naive and offset-aware datetimes` | Google Calendar returns timezone-aware datetimes | `.replace(tzinfo=None)` after `fromisoformat()` |
| `pipeline-error-anthropic-llm-failed` | Vapi needs separate Anthropic API key | Switched to `openai/gpt-4o-mini` |
| `ReadTimeout` in create_assistant.py | Default httpx timeout too short | Added `timeout=30.0` |
