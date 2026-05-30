# VA Dental — Waterfront Family Dentistry Voice Agent

## Project Summary
A voice AI receptionist named **Aria** for **Waterfront Family Dentistry** (Frisco, TX).
Stack: Vapi.ai · Google Calendar API · Python/FastAPI · Railway

## Repository
- Repo: `harshaeeb/va_dental`
- Branch: `claude/quirky-curie-p7FZ2`
- Project folder: repo root (flat structure)

## Project Structure
```
va_dental/                       # repo root = Railway build root
├── main.py                      # FastAPI server, /health + /vapi/tool-call
├── calendar_service.py          # Google Calendar read/write
├── config.py                    # Builds Aria's system prompt from waterfront_faqs.json
├── data/
│   ├── waterfront_faqs.json     # ACTIVE clinic data (Waterfront Family Dentistry)
│   └── faqs.json                # Legacy demo data (Bright Smile Dental — unused)
├── vapi_setup/
│   └── create_assistant.py      # Run ONCE after deploy to register Aria in Vapi
├── waterfrontsmiles.com/        # Downloaded website copy (source for knowledge base)
├── requirements.txt
├── Dockerfile                   # Uses ${PORT:-8080}
├── railway.toml
└── .env.example
```

## Clinic Details (Waterfront Family Dentistry)
- **Address**: 255 W Lebanon St, Suite 300, Frisco, TX 75036
- **Phone**: 972-987-4343
- **Email**: office@waterfrontsmiles.com / info@waterfrontsmiles.com
- **Hours**: Mon 10–5, Tue–Thu 9–12 / 1–5 (lunch break noon–1), Fri 8–2, Sat–Sun Closed
- **Doctor**: Dr. Lavi (Dr. Lavanya Rudrapatna), 20+ years experience
- **Loyalty Program**: Waterfront Family Loyalty Program (uninsured patients)
  - 2 cleanings/exams per year, fluoride, X-rays, 1 emergency exam
  - Additional cleanings at 50% off, 20% off all other treatments

## Credentials & Config (non-secret)
- **Google Cloud project**: `va-dental-demo`
- **Service account**: `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com`
- **Google Calendar ID**: `harsha.eeb@gmail.com`
- **Clinic timezone**: `America/Chicago`
- **Vapi API key**: stored in `.env` as `VAPI_API_KEY` (gitignored)
- **Google credentials**: `google-credentials.json` (gitignored)

## Credentials Strategy
- **Railway**: set `GOOGLE_CREDENTIALS_JSON` env var to the full JSON content of `google-credentials.json`
- **Local**: set `GOOGLE_CREDENTIALS_PATH=./google-credentials.json` in `.env`
- `calendar_service.py` checks `GOOGLE_CREDENTIALS_JSON` first, falls back to file path

## Deployment Target: Railway
- Connected repo: `harshaeeb/va_dental`, branch `claude/quirky-curie-p7FZ2`
- **Root Directory**: leave blank (Dockerfile is at repo root)
- Railway auto-builds from `Dockerfile` on every push
- **Deployed URL**: https://vadental-production.up.railway.app

### Environment variables set in Railway dashboard
```
VAPI_API_KEY=<vapi private key>
GOOGLE_CREDENTIALS_JSON=<full contents of google-credentials.json>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Waterfront Family Dentistry
```

## Vapi Assistant Details
- **Assistant name**: `Waterfront Family Dentistry Receptionist`
- **Assistant ID**: `62e72b31-22e9-4078-b32a-17551f176bfa` *(may be stale — re-run create_assistant.py after system prompt changes)*
- **Model**: `gpt-4o-mini` (OpenAI via Vapi), temperature 0.4
- **Transcriber**: Deepgram nova-2 (en-US)
- **Vapi API key**: `598d5af2-695a-4c93-9772-4386e22b2867`
- Dashboard: dashboard.vapi.ai → Assistants
- To assign to phone number: Phone Numbers → click number → Inbound Settings → select assistant

## Vapi Tools (4 tools — all inline in model.tools)
| Tool | Description |
|------|-------------|
| `check_availability` | Queries Google Calendar for open slots on a date |
| `book_appointment` | Creates a Google Calendar event for the patient |
| `cancel_appointment` | Deletes a Google Calendar event by event ID (used for rescheduling) |
| `take_message` | Logs caller name/phone/message to Railway stdout |

## Post-Deploy Workflow (after any system prompt change)
1. Ensure `.env` has `VAPI_API_KEY=598d5af2-695a-4c93-9772-4386e22b2867`
2. Run: `python vapi_setup/create_assistant.py`
3. Copy the printed Assistant ID
4. Go to Vapi dashboard → Phone Numbers → assign the new assistant

## Current Status
- [x] FastAPI server deployed on Railway
- [x] Google Calendar API enabled and service account has calendar access
- [x] Vapi assistant registered with inline tools (gpt-4o-mini)
- [x] All 4 tools working: check_availability, book_appointment, cancel_appointment, take_message
- [x] `{{currentDateTime}}` injected into system prompt (correct year in bookings)
- [x] Datetime timezone bug fixed (`replace(tzinfo=None)` in calendar_service.py)
- [x] Waterfront Family Dentistry knowledge base built from live website HTML
- [x] config.py surfaces providers, technology, loyalty program in system prompt
- [ ] Phone number assigned in Vapi dashboard

## Key Architecture Decisions
- **Inline tools** (not pre-created Vapi toolIds): avoids LLM result routing issues
- **No `request-complete` messages**: removing them fixed agent silence after tool calls
- **Lazy-load CalendarService**: server starts cleanly without credentials present
- **`GOOGLE_CREDENTIALS_JSON` env var**: avoids needing a credentials file on Railway
- **`strftime("%-I:%M %p")`**: Linux-only format — works on Railway, breaks on Windows

## Known Bugs Fixed
| Bug | Fix |
|-----|-----|
| Agent silent after tool call | Removed all `request-complete` Vapi messages |
| LLM loops 4-5x, gets stuck | Switched from pre-created toolIds to inline tools |
| Wrong year (2024) in bookings | Injected `{{currentDateTime}}` into system prompt |
| Duplicate bookings on reschedule | Implemented `cancel_appointment` tool |
| `offset-naive vs offset-aware` datetime crash | `.replace(tzinfo=None)` on Calendar event times |
| `pipeline-error-anthropic-llm-failed` | Switched model from Anthropic to OpenAI gpt-4o-mini |

## Important Notes
- Calendar must be shared with `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com` ("Make changes to events")
- Local git push always fails (proxy 403) — use MCP `mcp__github__push_files` for all GitHub writes
- `waterfrontsmiles.com/` folder in repo contains downloaded website copy (source for knowledge base) — not served
- `data/faqs.json` kept for reference but not used; active file is `data/waterfront_faqs.json`
