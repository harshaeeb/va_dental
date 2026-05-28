# VA Dental — Bright Smile Dental Voice Agent

## Project Summary
A voice AI receptionist named **Aria** for **Bright Smile Dental** (demo clinic).  
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
├── config.py                    # Builds Aria's system prompt from faqs.json
├── data/faqs.json               # Clinic data: hours, services, FAQs, insurance
├── vapi_setup/
│   └── create_assistant.py      # Run ONCE after deploy to register Aria in Vapi
├── requirements.txt
├── Dockerfile                   # Uses ${PORT:-8080}
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
- **Local**: set `GOOGLE_CREDENTIALS_PATH=./google-credentials.json` in `.env`
- `calendar_service.py` checks `GOOGLE_CREDENTIALS_JSON` first, falls back to file path

## Deployment Target: Railway
- Connect `harshaeeb/va_dental` GitHub repo in Railway dashboard
- Set branch to `claude/quirky-curie-p7FZ2`
- **Root Directory**: leave blank (Dockerfile is at repo root)
- Railway auto-builds from `Dockerfile`

### Environment variables to set in Railway dashboard
```
VAPI_API_KEY=<vapi private key>
GOOGLE_CREDENTIALS_JSON=<full contents of google-credentials.json>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Bright Smile Dental
```

## Post-Deploy: Register Aria in Vapi
1. Update `SERVER_URL` in `vapi_setup/create_assistant.py` with the Railway URL
2. Run: `python vapi_setup/create_assistant.py`
3. Copy the printed `Assistant ID`
4. Go to Vapi dashboard → Phone Numbers → assign `Bright Smile Dental Receptionist`

## Current Status
- [x] All code written and validated
- [x] Pushed to GitHub branch `claude/quirky-curie-p7FZ2` at repo root
- [x] Dockerfile uses `${PORT:-8080}` (Railway compatible)
- [x] `calendar_service.py` supports `GOOGLE_CREDENTIALS_JSON` env var (Railway)
- [x] Google credentials JSON obtained (project: va-dental-demo)
- [x] Vapi API key obtained
- [ ] Railway project deployed successfully
- [ ] `SERVER_URL` updated in `vapi_setup/create_assistant.py`
- [ ] Vapi assistant registered
- [ ] Phone number assigned in Vapi dashboard

## Vapi Tools (3 tools)
| Tool | Description |
|------|-------------|
| `check_availability` | Queries Google Calendar for open slots on a date |
| `book_appointment` | Creates a Google Calendar event for the patient |
| `take_message` | Logs caller name/phone/message to server stdout |

## Important Notes
- Calendar must be shared with `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com` with "Make changes to events" permission
- `CalendarService` is lazy-loaded — server starts fine without credentials
- `strftime("%-I:%M %p")` is Linux-only — works on Railway, not Windows
