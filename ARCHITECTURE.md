# Architecture — Waterfront Family Dentistry Voice Agent

## System Overview

Aria is a voice AI receptionist that answers inbound phone calls for a dental clinic. It uses Vapi.ai as the voice orchestration layer, a Python/FastAPI backend hosted on Railway as the tool execution server, and Google Calendar for appointment management.

---

## High-Level Block Diagram

```mermaid
flowchart TD
    Caller(["📞 Patient\n(phone call)"])

    subgraph VAPI["VAPI.AI — Voice Orchestration"]
        PhoneNum["Phone Number\n(inbound call routing)"]
        STT["Speech-to-Text\nDeepgram Nova-2"]
        LLM["LLM\nOpenAI gpt-4o-mini\n+ System Prompt"]
        TTS["Text-to-Speech\nVapi Default"]
    end

    subgraph RAILWAY["RAILWAY — FastAPI Backend"]
        Webhook["POST /vapi/tool-call\nWebhook Handler"]
        Router["Tool Router\nmain.py"]
        CalSvc["CalendarService\ncalendar_service.py"]
        PromptBuilder["System Prompt Builder\nconfig.py"]
        KB[("Clinic Knowledge Base\nwaterfront_faqs.json")]
    end

    subgraph GCAL["GOOGLE CALENDAR API"]
        Calendar[("Google Calendar\nharsha.eeb@gmail.com")]
        ServiceAcct["Service Account\nsa-va-dental-demo@\nva-dental-demo.iam.\ngserviceaccount.com"]
    end

    Caller -->|"inbound call"| PhoneNum
    PhoneNum --> STT
    STT -->|"transcript"| LLM
    LLM -->|"spoken response"| TTS
    TTS -->|"audio"| Caller

    LLM -->|"HTTP POST\ntool call"| Webhook
    Webhook --> Router
    Router --> CalSvc
    CalSvc --> ServiceAcct
    ServiceAcct --> Calendar
    Calendar -->|"events / confirmation"| CalSvc
    CalSvc -->|"result JSON"| Router
    Router -->|"tool result"| Webhook
    Webhook -->|"HTTP response"| LLM

    LLM -->|"transferCall\n(native Vapi)"| Supervisor["☎ Supervisor\n+14699825114"]

    KB -->|"read at startup"| PromptBuilder
    PromptBuilder -->|"system prompt\n(injected per call)"| LLM
```

---

## Call Flow — Sequence Diagram

```mermaid
sequenceDiagram
    participant P as Patient (Phone)
    participant V as Vapi.ai
    participant F as FastAPI (Railway)
    participant G as Google Calendar

    P->>V: Inbound call
    V->>P: "Thank you for calling Waterfront Family Dentistry! This is Aria."

    P->>V: "I'd like to book a cleaning for next Monday"
    V->>V: STT → transcript
    V->>V: LLM decides to call check_availability

    V->>F: POST /vapi/tool-call {date, duration_minutes}
    F->>G: events.list(timeMin, timeMax)
    G-->>F: existing events
    F-->>V: "Available slots: 9:00 AM, 10:00 AM, 2:00 PM"

    V->>P: "I have openings at 9, 10 AM and 2 PM — which works best?"
    P->>V: "10 AM works"
    V->>P: "Great! Can I get your name and best callback number?"
    P->>V: "Jane Smith, 214-555-0101"

    V->>F: POST /vapi/tool-call {patient_name, phone, service, date, time}
    F->>G: events.insert(event)
    G-->>F: event_id
    F-->>V: "Confirmed! Jane Smith booked for Routine Cleaning on Monday at 10 AM. Booking ID: abc123"

    V->>P: "You're all set! Jane is booked for a Routine Cleaning on Monday at 10 AM."
    V->>P: "Thank you for calling Waterfront Family Dentistry. Have a wonderful day!"
    V->>P: Call ends
```

### Transfer Flow — Caller Requests a Human

```mermaid
sequenceDiagram
    participant P as Patient (Phone)
    participant V as Vapi.ai
    participant S as Supervisor (+14699825114)

    P->>V: "Can I speak to someone?"
    V->>V: LLM triggers transfer_to_supervisor
    V->>P: "Of course — let me connect you with a team member right now."
    V->>S: PSTN transfer (Vapi-native, no FastAPI call)
    S->>P: Supervisor picks up
```

---

## Component Breakdown

### 1. Vapi.ai (Voice Orchestration)
| Sub-component | Technology | Role |
|--------------|-----------|------|
| Phone Number | Vapi PSTN | Routes inbound calls |
| Speech-to-Text | Deepgram Nova-2 (en-US) | Converts patient speech to text |
| LLM | OpenAI gpt-4o-mini, temp 0.4 | Drives conversation, decides when to call tools |
| Text-to-Speech | Vapi Default | Converts Aria's responses to audio |
| Tool definitions | Inline in `model.tools` | Tells LLM when/how to call backend tools |
| Call Transfer | Vapi `transferCall` (native) | PSTN transfer to supervisor — no FastAPI involved |

**Key design choice:** Tools are defined *inline* in the assistant config (not as pre-created Vapi tool objects). This ensures tool results are properly routed back to the LLM.

### 2. FastAPI Backend (Railway)
| File | Responsibility |
|------|--------------|
| `main.py` | Webhook handler, tool dispatcher |
| `calendar_service.py` | Google Calendar API wrapper |
| `config.py` | Builds system prompt from JSON data |
| `data/waterfront_faqs.json` | Clinic knowledge base (hours, services, FAQs, insurance, loyalty program) |

**Endpoint:** `POST /vapi/tool-call`  
**Health check:** `GET /health`

### 3. Google Calendar API
- Auth via service account (`google-credentials.json` / `GOOGLE_CREDENTIALS_JSON` env var)
- Reads events to find free slots (8 AM–5 PM window, 30-min increments, 15-min buffers)
- Creates events with patient name, phone, service, and reminders
- Deletes events for cancellations/rescheduling

### 4. Clinic Knowledge Base (`waterfront_faqs.json`)
Loaded at startup and rendered into the system prompt. Contains:
- Clinic name, address, phone, email, hours
- 24 bookable services with durations (20–90 min)
- Insurance plans accepted
- Loyalty Program details (for uninsured patients)
- Provider profiles (Dr. Lavi, 20+ years)
- Technology (digital X-rays, laser dentistry)
- 33 FAQs covering common caller questions

---

## The 5 Tools

```mermaid
flowchart LR
    LLM["LLM\n(gpt-4o-mini)"] -->|"date, duration"| T1
    LLM -->|"name, phone,\nservice, date, time"| T2
    LLM -->|"event_id"| T3
    LLM -->|"name, phone,\nmessage"| T4
    LLM -->|"caller requests human\nor booking fails"| T5

    T1["check_availability\n→ list of open slots"]
    T2["book_appointment\n→ calendar event + Booking ID"]
    T3["cancel_appointment\n→ deletes event (for reschedule)"]
    T4["take_message\n→ logs to Railway stdout"]
    T5["transfer_to_supervisor\n→ PSTN transfer (Vapi-native)"]

    T1 & T2 & T3 -->|"Calendar API"| GCal[("Google\nCalendar")]
    T4 -->|"stdout log"| Log["Railway\nLogs"]
    T5 -->|"no FastAPI call\nVapi transfers directly"| Sup["☎ Supervisor\n+14699825114"]
```

### Tool Transfer Triggers

`transfer_to_supervisor` fires when either condition is met:
1. Caller asks to speak to a person, representative, supervisor, or the doctor
2. Aria cannot book or confirm an appointment due to a calendar or system error

On transfer failure, Aria falls back to `take_message` to collect the caller's details for a callback.

---

## Deployment Architecture

```mermaid
flowchart LR
    Dev["Developer\n(local)"] -->|"git push"| GH["GitHub\nharshaeeb/va_dental\nbranch: claude/quirky-curie-p7FZ2"]
    GH -->|"auto-deploy\non push"| Railway["Railway\nDocker container\nport 8080"]
    Railway -->|"HTTPS"| Vapi["Vapi.ai\n(tool webhook)"]
    Vapi -->|"PSTN"| Phone["Patient\nPhone"]

    Railway -->|"OAuth2\nservice account"| GCal["Google Calendar API"]
    Railway -->|"reads at startup"| KB["waterfront_faqs.json\n(in repo)"]
```

**Environment variables on Railway:**
```
GOOGLE_CREDENTIALS_JSON   # Full service account JSON (secret)
GOOGLE_CALENDAR_ID        # harsha.eeb@gmail.com
CLINIC_TIMEZONE           # America/Chicago
CLINIC_NAME               # Waterfront Family Dentistry
VAPI_API_KEY              # Vapi secret key
SUPERVISOR_PHONE          # +14699825114 — destination for call transfers
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Inline Vapi tools (not pre-created toolIds) | Pre-created tools route results incorrectly; LLM never sees tool responses |
| No `request-complete` messages in tools | Caused agent silence — LLM generated empty response after filler audio |
| `{{currentDateTime}}` in system prompt | LLM defaults to training data year (2024); Vapi injects real date at call time |
| `cancel_appointment` before rebook | Without explicit cancel, a reschedule creates a duplicate calendar event |
| `replace(tzinfo=None)` on Calendar datetimes | Google returns timezone-aware datetimes; slot times are naive — stripping tzinfo prevents crash |
| Lazy-load `CalendarService` | Server boots cleanly without credentials; fails gracefully only when a calendar tool is called |
| `GOOGLE_CREDENTIALS_JSON` env var | Railway has no filesystem persistence; inlining credentials as an env var avoids file management |
| gpt-4o-mini over Anthropic models | Vapi requires a separate Anthropic API key; OpenAI models work with Vapi's built-in key |
| `transferCall` tool type (not a function tool) | Vapi handles PSTN transfer natively — no HTTP round-trip to FastAPI, lower latency, no server-side code needed |
| Fallback to `take_message` on transfer failure | If the supervisor line is unreachable, caller details are still captured rather than losing the caller entirely |

---

## Data Flow Summary

```
Patient speech
  → Deepgram STT (transcript)
  → gpt-4o-mini + system prompt (decides action)
  → [if calendar tool needed] HTTP POST to FastAPI /vapi/tool-call
      → Google Calendar API (read/write)
      → result JSON back to Vapi
  → [if transfer triggered] Vapi transferCall (PSTN, no FastAPI involved)
      → call bridged to supervisor at +14699825114
  → gpt-4o-mini (formulates spoken reply)
  → Vapi TTS (audio)
  → Patient hears response
```

---

## Security Notes

- `google-credentials.json` is **gitignored** — never committed to the repo
- Google credentials are passed to Railway via the `GOOGLE_CREDENTIALS_JSON` environment variable
- Vapi API key is stored in local `.env` (gitignored) and Railway environment variables only
- Service account has calendar access only — no broader GCP permissions
