# Operational Card — Voice Agent Workflow

Sponsored by Creignificent LLC.

## Purpose
Working voice agent that accepts spoken reservation requests, checks availability, confirms bookings for signed-in users, stores spoken transcripts, and handles interruption and human handoff.

## Trust Boundaries
- **Input**: Spoken text from the browser Web Speech API. Transcript and session token are sent to the backend.
- **Processing**: Python serverless handler (`api/agent.py`) with explicit state machine.
- **Output**: SSE stream (`delta`, `metrics`, `intent`, `state`, `booking`) + browser TTS.
- **Data**:
  - Availability from `RESERVATIONS_URL` or bundled `api/reservations.json` (cached).
  - Users, bookings, and audio transcripts held in memory only.
- No raw audio blobs are stored. No durable persistence yet.

## Current Enforcement
- State machine: `BOOKING` | `INTERRUPTED` | `HANDOFF`.
- Booking write requires a valid session token and an explicit confirm utterance.
- Party size extracted from words (one–ten) or digits (1–10).
- In-memory cache with configurable TTL (`CACHE_TTL_SECONDS`, default 60).
- Metrics returned: response time, task completion, handoff flag, records loaded, data source.

## Explicit Non-Goals
- Not connected to an external restaurant system or telephony provider.
- Not using a remote LLM API (intent is rule-based).
- Not durable across cold starts.
- Not storing raw audio files.
- Not intended for production customer traffic without a persistent store and further hardening.

## Verification Points
| Test | Input | Expected Result |
|------|--------|-----------------|
| Register | Email + name | Session token returned, UI unlocks |
| Availability | “I’d like a table for two tomorrow.” | State = BOOKING, availability offered |
| Confirm booking | “confirm” (while signed in) | Booking record created and spoken |
| My bookings | Click button | User’s bookings listed |
| Party size | “Book a table for six on Saturday.” | Party correctly parsed as 6 |
| Interruption | Speak while agent is talking | TTS stops, state = INTERRUPTED |
| Handoff | “I have a complaint…” | State = HANDOFF |
| Audio record | Any spoken turn | Transcript stored for the user |

All tests are executable after deploying to Vercel and opening the live URL in Chrome.

## Next Secure Step
- Move users, bookings, and audio records to a durable store (KV / Postgres).
- Add an explicit policy gate before booking writes (admit / review / deny).
- Log tool decisions.
- Define retention and deletion rules for stored transcripts.
- Require stronger auth if this leaves the free-tier demo path.

---
*Documentation defines the intended trust boundaries. Code is the implementation.*
