# VA Dental — Bright Smile Dental Voice Agent

## Project Summary
A voice AI receptionist named **Aria** for **Bright Smile Dental** (demo clinic).  
Stack: Vapi.ai · Google Calendar API · Python/FastAPI · Railway

## Repository
- Repo: `harshaeeb/va_dental`
- Branch: `claude/quirky-curie-p7FZ2`
- Project folder: `dental-voice-agent/`

## Project Structure
```
dental-voice-agent/
├── main.py                      # FastAPI server, /health + /vapi/tool-call endpoints
├── calendar_service.py          # Google Calendar read/write (CalendarService class)
├── config.py                    # Builds Aria's system prompt from faqs.json
├── data/faqs.json               # Clinic data: hours, services, FAQs, insurance
├── vapi_setup/
│   └── create_assistant.py      # Run ONCE after deploy to register Aria in Vapi
├── requirements.txt
├── Dockerfile                   # Uses ${PORT:-8080} for Railway/Cloud Run compatibility
├── railway.toml
└── .env.example
```

## Credentials & Config (non-secret)
- **Google Cloud project**: `va-dental-demo`
- **Service account**: `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com`
- **Google Calendar ID**: `harsha.eeb@gmail.com`
- **Clinic timezone**: `America/Chicago`
- **Clinic name**: `Bright Smile Dental`
- **Vapi API key**: stored in `.env` as `VAPI_API_KEY` (gitignored)
- **Google credentials**: `google-credentials.json` (gitignored)

## Credentials Strategy
- **Railway**: set `GOOGLE_CREDENTIALS_JSON` env var to the full JSON content of `google-credentials.json`
- **Cloud Run**: mount via Secret Manager at `GOOGLE_CREDENTIALS_PATH=/app/google-credentials.json`
- `calendar_service.py` checks `GOOGLE_CREDENTIALS_JSON` first, falls back to file path

## Deployment Target: Railway
- Connect `harshaeeb/va_dental` GitHub repo in Railway dashboard
- Set branch to `claude/quirky-curie-p7FZ2`
- Railway auto-builds from `Dockerfile`

### Environment variables to set in Railway dashboard
```
VAPI_API_KEY=<vapi private key>
GOOGLE_CREDENTIALS_JSON=<full contents of google-credentials.json>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Bright Smile Dental
```

## Deployment Steps (Railway — dashboard method)
1. Go to railway.app → New Project → Deploy from GitHub repo
2. Select `harshaeeb/va_dental`, branch `claude/quirky-curie-p7FZ2`
3. Railway detects Dockerfile and builds automatically
4. Go to project → Variables tab → add all env vars above
5. For `GOOGLE_CREDENTIALS_JSON`: paste the full JSON from `google-credentials.json`
6. Go to Settings → Networking → Generate Domain → copy the URL
7. Update `SERVER_URL` in `vapi_setup/create_assistant.py` with the Railway URL
8. Run: `python vapi_setup/create_assistant.py`
9. Copy the printed `Assistant ID`
10. Go to Vapi dashboard → Phone Numbers → assign `Bright Smile Dental Receptionist`

## Post-Deploy: Register Aria in Vapi
1. Update `SERVER_URL` in `vapi_setup/create_assistant.py` with the Railway URL
2. Run: `python vapi_setup/create_assistant.py`
3. Copy the printed `Assistant ID`
4. Go to Vapi dashboard → Phone Numbers → assign `Bright Smile Dental Receptionist`

## Current Status
- [x] All code written and validated
- [x] Pushed to GitHub branch `claude/quirky-curie-p7FZ2`
- [x] Dockerfile uses `${PORT:-8080}` (Railway + Cloud Run compatible)
- [x] `calendar_service.py` supports `GOOGLE_CREDENTIALS_JSON` env var (Railway)
- [x] Google credentials JSON obtained (project: va-dental-demo)
- [x] Vapi API key obtained
- [ ] Railway project created and deployed
- [ ] `SERVER_URL` updated in `create_assistant.py`
- [ ] Vapi assistant registered (run `create_assistant.py` after deploy)
- [ ] Phone number assigned in Vapi dashboard

## Vapi Tools (3 tools)
| Tool | Description |
|------|-------------|
| `check_availability` | Queries Google Calendar for open slots on a date |
| `book_appointment` | Creates a Google Calendar event for the patient |
| `take_message` | Logs caller name/phone/message to server stdout |

## Important Notes
- Calendar must be shared with service account email (`sa-va-dental-demo@...`) with "Make changes to events" permission
- `CalendarService` is lazy-loaded — server starts fine without credentials, fails gracefully on tool calls
- `strftime("%-I:%M %p")` uses Linux-only `%-I` format — works on Railway (Linux), not Windows
- Sandbox SSL proxy blocks outbound Google API calls in this dev environment — works fine on Railway
