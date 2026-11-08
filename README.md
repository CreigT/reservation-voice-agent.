# Voice Agent Workflow

Working voice agent for restaurant reservation availability and booking.

Sponsored by Creignificent LLC.

Speak into the microphone → speech-to-text → intent detection → availability check → spoken reply, with interruption, handoff, user accounts, booking confirmation, and stored transcripts.

## Quick Start

1. Deploy the repo to Vercel (import `CreigT/reservation-voice-agent.`).
2. Open the live URL in Chrome.
3. Register or log in with an email.
4. Hold the **Hold to speak** button and say a request, for example:
   - “I’d like a table for two tomorrow.”
   - Then say “confirm” to book it (while signed in).
   - “I have a complaint.” (triggers handoff)
5. Speak again while the agent is talking to interrupt.
6. Click **My bookings** to see confirmed reservations for your account.

Metrics (response time, task completion, state) update after each turn.

## Accounts, Bookings, and Audio

- **Register / Login** — email-based session token stored in the browser.
- **Booking** — after availability is confirmed, say “confirm”, “yes”, or “book it” to write a booking tied to the signed-in user.
- **Audio records** — each spoken transcript is stored for the user (transcript + timestamp).

These records live in memory on the serverless instance (survive a warm instance, lost on cold start). A durable store can replace the in-memory lists later without changing the API.

## Data Source

Reservation availability is loaded in this order:

1. Environment variable `RESERVATIONS_URL` (public CSV or JSON URL).
2. Bundled fallback `api/reservations.json` if no URL is set or the fetch fails.

Results are cached in memory for `CACHE_TTL_SECONDS` (default 60).

**Vercel environment variables (optional)**
- `RESERVATIONS_URL` — public CSV or JSON link
- `CACHE_TTL_SECONDS` — cache duration (default 60)

## SECURE

**Trust boundaries**
- Microphone and speech synthesis run in the browser (Web Speech API).
- Backend receives the transcript and session token.
- Availability data comes from `RESERVATIONS_URL` or the bundled JSON.
- User accounts, bookings, and audio transcripts are held in memory only (no durable store yet).
- No raw audio blobs are stored; only the transcript text.

**Current enforcement**
- Explicit state machine: `BOOKING` | `INTERRUPTED` | `HANDOFF`.
- Booking write requires a valid session token.
- Availability tool reads only from the cached reservation data.
- In-memory cache with TTL.

**Explicit non-goals**
- Not connected to an external restaurant POS or telephony provider.
- Not using a remote LLM API (intent is rule-based).
- Not durable across cold starts (in-memory only).
- Not intended for production customer traffic without further hardening and a persistent store.

## VERIFY

1. Deploy and open the live URL in Chrome.
2. Register with an email.
3. Hold the button and say “I’d like a table for two tomorrow.”  
   Confirm the reply offers availability and state = `BOOKING`.
4. Say “confirm”.  
   Confirm a booking record is created and spoken back.
5. Click **My bookings** and confirm the record appears.
6. While the agent is speaking, hold the button again.  
   Confirm TTS stops and state = `INTERRUPTED`.
7. Say “I have a complaint.”  
   Confirm state = `HANDOFF`.

Full verification points are in `docs/OPERATIONAL_CARD.md`.

## DOCUMENT

Operational details, trust boundaries, verification points, and next secure step:

→ [docs/OPERATIONAL_CARD.md](docs/OPERATIONAL_CARD.md)

## Stack

- HTML frontend with Web Speech API (microphone + TTS) and session login
- Python serverless backend (`api/agent.py`) with SSE streaming
- In-memory users, bookings, and audio records
- In-memory availability cache + bundled JSON fallback
- Optional remote data via `RESERVATIONS_URL`
- Deployable on Vercel

## License

MIT
