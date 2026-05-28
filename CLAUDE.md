# VA Dental — Bright Smile Dental Voice Agent

## Project Summary
A voice AI receptionist named **Aria** for **Bright Smile Dental** (demo clinic).  
Stack: Vapi.ai · Google Calendar API · Python/FastAPI · Google Cloud Run

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
├── Dockerfile                   # Uses ${PORT:-8080} for Cloud Run compatibility
├── .gcloudignore
└── .env.example
```

## Credentials & Config (non-secret)
- **Google Cloud project**: `va-dental-demo`
- **Service account**: `sa-va-dental-demo@va-dental-demo.iam.gserviceaccount.com`
- **Google Calendar ID**: `harsha.eeb@gmail.com`
- **Clinic timezone**: `America/Chicago`
- **Clinic name**: `Bright Smile Dental`
- **Vapi API key**: stored in `.env` as `VAPI_API_KEY` (gitignored)
- **Google credentials**: `google-credentials.json` (gitignored, also stored in GCP Secret Manager as `google-credentials`)

## Deployment Target: Google Cloud Run
Region: `us-central1`
Service name: `dental-voice-agent`
Image: `us-central1-docker.pkg.dev/va-dental-demo/dental-voice-agent/app:latest`

### Environment variables set on Cloud Run
```
VAPI_API_KEY=<from .env>
GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com
GOOGLE_CREDENTIALS_PATH=/app/google-credentials.json
CLINIC_TIMEZONE=America/Chicago
CLINIC_NAME=Bright Smile Dental
```
Secret mount: `google-credentials` (Secret Manager) → `/app/google-credentials.json`

## Deployment Steps (summary)
```bash
# From inside dental-voice-agent/ folder
gcloud config set project va-dental-demo
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories create dental-voice-agent --repository-format=docker --location=us-central1
gcloud secrets create google-credentials --data-file=google-credentials.json
PROJECT_NUMBER=$(gcloud projects describe va-dental-demo --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding google-credentials \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud builds submit --tag us-central1-docker.pkg.dev/va-dental-demo/dental-voice-agent/app:latest
gcloud run deploy dental-voice-agent \
  --image us-central1-docker.pkg.dev/va-dental-demo/dental-voice-agent/app:latest \
  --platform managed --region us-central1 --allow-unauthenticated \
  --port 8080 --min-instances 1 --max-instances 10 \
  --set-secrets="/app/google-credentials.json=google-credentials:latest" \
  --set-env-vars="VAPI_API_KEY=<key>,GOOGLE_CALENDAR_ID=harsha.eeb@gmail.com,GOOGLE_CREDENTIALS_PATH=/app/google-credentials.json,CLINIC_TIMEZONE=America/Chicago,CLINIC_NAME=Bright Smile Dental"
gcloud run services describe dental-voice-agent --region us-central1 --format='value(status.url)'
```

## Post-Deploy: Register Aria in Vapi
1. Update `SERVER_URL` in `vapi_setup/create_assistant.py` with the Cloud Run URL
2. Run: `python vapi_setup/create_assistant.py`
3. Copy the printed `Assistant ID`
4. Go to Vapi dashboard → Phone Numbers → assign `Bright Smile Dental Receptionist`

## Current Status
- [x] All code written and validated
- [x] Pushed to GitHub branch `claude/quirky-curie-p7FZ2`
- [x] Dockerfile updated for Cloud Run (`${PORT:-8080}`)
- [x] `.gcloudignore` added
- [x] Google credentials JSON obtained (project: va-dental-demo)
- [x] Vapi API key obtained
- [ ] Cloud Run deployed (awaiting user to run gcloud commands)
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
- `strftime("%-I:%M %p")` uses Linux-only `%-I` format — works on Cloud Run (Linux), not Windows
- Sandbox SSL proxy blocks outbound Google API calls in this dev environment — works fine on Cloud Run
