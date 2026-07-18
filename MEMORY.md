# Project Memory — VA Dental Voice Agent
*Import this file at the start of a new session to restore full context.*

---

## What This Project Is
A production voice AI receptionist named **Aria** for **Waterfront Family Dentistry** in Frisco, TX.
Aria answers inbound calls via Vapi.ai, checks availability, books/cancels/reschedules appointments, takes messages, and transfers calls to a live supervisor when needed.

---

## Tech Stack
| Layer | Technology |
|-------|----------|
| Voice AI platform | Vapi.ai (inline tools, gpt-4o-mini, Deepgram STT) |
| Backend webhook | Python / FastAPI on Railway |
| Calendar | Google Calendar API (service account) |
| PMS (optional) | NexHealth Synchronizer API |
| Clinic knowledge | `data/waterfront_faqs.json` |
| Hosting | Railway (auto-deploy from GitHub branch) |

---

## Repository
- **GitHub**: `harshaeeb/va_dental`
- **Active branch**: `claude/quirky-curie-p7FZ2`
- **Railway URL**: https://vadental-production.up.railway.app
- **Local git push is broken** (proxy 403) — always use MCP `mcp__github__push_files` for GitHub writes
- After any MCP push, sync local: `git fetch origin && git reset --hard origin/claude/quirky-curie-p7FZ2`
- Git config must be: `user.email = noreply@anthropic.com`, `user.name = Claude`

---

## Key Files
| File | Purpose |
|------|-------|
| `main.py` | FastAPI server — `/health` + `/vapi/tool-call` webhook; uses lazy-loaded `get_pms()` |
| `calendar_service.py` | Google Calendar CRUD (get slots, book, cancel) |
| `config.py` | Builds Aria's system prompt from `waterfront_faqs.json` |
| `pms/backend.py` | PMS adapter layer — `GoogleCalendarBackend`, `NexHealthBackend`, `DualBackend`, `get_backend()` |
| `pms/__init__.py` | Empty package marker |
| `nexhealth/auth.py` | Bearer token manager with 5-min pre-expiry cache |
| `nexhealth/client.py` | httpx wrapper — injects auth headers, 5s timeout |
| `nexhealth/appointments.py` | `get_availability`, `create_appointment`, `find_appointment`, `cancel_by_id` |
| `nexhealth/patients.py` | `find_or_create_patient` |
| `nexhealth/__init__.py` | Empty package marker |
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
- **Supervisor phone**: `+14699825114`

### Railway env vars (current — all required)
```
VAPI_API_KEY=598d5af2-695a-4c93-9772-4386e22b2867
GOOGLE_CREDENTIALS_JSON=<full JSON content of google-credentials.json>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Waterfront Family Dentistry
SUPERVISOR_PHONE=+14699825114
PMS_BACKEND=google
```

### NexHealth env vars (add when activating NexHealth)
```
NEXHEALTH_API_KEY=<your nexhealth api key>
NEXHEALTH_SUBDOMAIN=<your practice subdomain>
NEXHEALTH_LOCATION_ID=<your location id>
NEXHEALTH_API_VERSION=v20240412
NEXHEALTH_BASE_URL=https://nexhealth.info
PMS_BACKEND=dual
```
Sign up for a free sandbox at https://developer.nexhealth.com

---

## PMS Backend System
Controlled by `PMS_BACKEND` env var — change without redeploying:

| Value | Behavior |
|-------|-------|
| `google` | Google Calendar only (default) — works without NexHealth credentials |
| `nexhealth` | NexHealth Synchronizer API only |
| `dual` | NexHealth primary + Google Calendar mirror/fallback |

**Dual mode** (`dual`):
- `get_availability`: NexHealth first; falls back to GCal on error
- `book_appointment`: NexHealth primary + best-effort GCal mirror; falls back to GCal if NexHealth fails
- `cancel_appointment`: Cancels in both systems; returns NexHealth result
- `reschedule_appointment`: cancel existing + book new (default implementation in `PMSBackend` base class)

---

## Slot ID Encoding
Both backends expose slots via the same `[slot:XXX]` pattern so the LLM passes them back opaquely:
- **Google Calendar**: `slot_id = "YYYY-MM-DDTHH:MM"` (e.g. `"2026-07-25T10:00"`) — detected by `startswith("20")` and `"T" in slot_id`
- **NexHealth**: opaque integer string from NexHealth `/appointment_slots` response

---

## Vapi Assistant
- **Name**: Waterfront Family Dentistry Receptionist
- **Assistant ID**: `0998351c-6a73-4dea-ac45-7e88f5232f59` *(re-run `create_assistant.py` after any prompt or tool schema change)*
- **Model**: gpt-4o-mini (OpenAI via Vapi), temperature 0.4
- **Transcriber**: Deepgram nova-2, en-US
- **Tool type**: Inline (in `model.tools`) — NOT pre-created toolIds

### Vapi Tools (6 total)
| Tool | Type | Handler |
|------|------|-------|
| `check_availability` | `function` | FastAPI → PMS backend |
| `book_appointment` | `function` | FastAPI → PMS backend |
| `reschedule_appointment` | `function` | FastAPI → PMS backend |
| `cancel_appointment` | `function` | FastAPI → PMS backend |
| `take_message` | `function` | FastAPI → stdout log |
| `transfer_to_supervisor` | `transferCall` | Vapi-native PSTN (no FastAPI round-trip) |

### Tool Schemas (key required fields)
`check_availability`: `appointment_type` (enum), `preferred_date_start` (YYYY-MM-DD), `preferred_date_end` (YYYY-MM-DD), optional `preferred_time_window`

`book_appointment`: `slot_id`, `patient_first_name`, `patient_last_name`, `patient_phone`, `appointment_type` (enum), `is_new_patient` (bool), optional `patient_date_of_birth`, `patient_email`, `notes`

`reschedule_appointment`: `patient_phone`, `new_slot_id`, `appointment_type` (enum), optional `current_appointment_date`, `current_appointment_id`, `patient_first_name`, `patient_last_name`

`cancel_appointment`: `patient_phone`, `appointment_date`, optional `appointment_id`, `cancellation_reason`

`take_message`: `caller_name`, `caller_phone`, `message`

`appointment_type` enum: `["cleaning", "checkup", "emergency", "consultation", "whitening", "other"]`

---

## Call Transfer
Aria transfers to supervisor phone `+14699825114` using Vapi's native `transferCall` tool type. Triggers:
1. Caller explicitly asks to speak to a person, representative, supervisor, or the doctor
2. Aria cannot book or confirm due to a calendar or system error

System prompt rules:
- Say "Of course — let me connect you with one of our team members right now." then call `transfer_to_supervisor` immediately
- Do NOT ask for name/number before transferring
- If transfer fails, use `take_message` instead

`SUPERVISOR_PHONE` env var controls the destination number — change in Railway dashboard without redeploying.

---

## Architecture Rules (must preserve)
1. **Inline tools only** — pre-created Vapi toolIds break LLM result routing
2. **No `request-complete` messages** — they cause agent silence after tool calls
3. **`{{currentDateTime}}` in system prompt** — required for correct year in bookings
4. **`reschedule_appointment` handles both** — do NOT call cancel + book separately (avoid duplicate logic)
5. **`replace(tzinfo=None)`** on Google Calendar event datetimes — prevents offset-naive/aware crash
6. **Lazy-load `CalendarService` and PMS backend** — server must start without credentials
7. **5-second timeout** in NexHealth client — keeps live calls responsive
8. **`strftime("%-I:%M %p")`** is Linux-only — works on Railway, breaks on macOS/Windows

---

## Vapi Payload Format (inline tools)
```json
{
  "message": {
    "toolCallList": [{
      "id": "call_xxx",
      "function": {
        "name": "check_availability",
        "arguments": "{\"appointment_type\": \"cleaning\", \"preferred_date_start\": \"2026-07-25\", \"preferred_date_end\": \"2026-07-25\"}"
      }
    }]
  }
}
```
`arguments` arrives as a **JSON string** — `main.py` parses it with `json.loads()`.

---

## Workflow: After Changing System Prompt or Tool Schemas
1. Edit `data/waterfront_faqs.json` and/or `config.py` and/or `vapi_setup/create_assistant.py`
2. Push to GitHub branch `claude/quirky-curie-p7FZ2` via `mcp__github__push_files`
3. Sync local: `git fetch origin && git reset --hard origin/claude/quirky-curie-p7FZ2`
4. Wait for Railway to redeploy (~30s) — check https://vadental-production.up.railway.app/health
5. Locally: `cd va_dental && python vapi_setup/create_assistant.py`
6. Copy printed Assistant ID → Vapi dashboard → Phone Numbers → Inbound Settings → select assistant

## Workflow: Activating NexHealth for Demo
1. Sign up at https://developer.nexhealth.com to get sandbox credentials
2. Add NexHealth env vars to Railway dashboard (see above)
3. Change `PMS_BACKEND=dual` in Railway dashboard
4. Railway redeploys automatically (no code change needed)

## Workflow: Adding a New Clinic
1. Create `data/<clinic>_faqs.json` in same schema as `waterfront_faqs.json`
2. Update `config.py` line 4 to point to new file
3. Update assistant name/messages in `vapi_setup/create_assistant.py`
4. Push and redeploy

---

## Bugs Fixed (don't reintroduce)
| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Agent silent after "let me check..." | `request-complete` Vapi filler plays, LLM generates empty follow-up | Remove all `request-complete` messages from tool definitions |
| Agent loops 4-5x then hangs | Pre-created toolIds — LLM doesn't receive tool results | Use inline tools in `model.tools` |
| Wrong year (2024) in bookings | LLM uses training data year | Inject `{{currentDateTime}}` into system prompt |
| Duplicate calendar events on reschedule | No reschedule tool — was cancel+book separately | `reschedule_appointment` tool in system prompt + `PMSBackend.reschedule_appointment()` |
| `can't compare offset-naive and offset-aware datetimes` | Google Calendar returns timezone-aware datetimes | `.replace(tzinfo=None)` after `fromisoformat()` |
| `pipeline-error-anthropic-llm-failed` | Vapi needs separate Anthropic API key | Switched to `openai/gpt-4o-mini` |
| `ReadTimeout` in create_assistant.py | Default httpx timeout too short | Added `timeout=30.0` |

---

## Pending Actions (user must do)
- [x] Re-run `python vapi_setup/create_assistant.py` — done, ID: `0998351c-6a73-4dea-ac45-7e88f5232f59`
- [ ] Assign updated assistant to phone number in Vapi dashboard
- [ ] (Optional) Sign up at developer.nexhealth.com, add NexHealth env vars to Railway, set `PMS_BACKEND=dual`
- [ ] (Deferred) Add more call transfer triggers beyond the current two
