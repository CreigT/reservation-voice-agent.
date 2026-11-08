# Voice Agent Workflow

Working voice agent for restaurant reservation availability.

Sponsored by Creignificent LLC.

Speak into the microphone → speech-to-text → intent detection → availability check against reservation data → spoken reply, with interruption and handoff handling.

## Quick Start

1. Deploy the repo to Vercel (import `CreigT/reservation-voice-agent.`).
2. Open the live URL in Chrome.
3. Hold the **Hold to speak** button and say a request, for example:
   - “I’d like a table for two tomorrow.”
   - “I have a complaint.” (triggers handoff)
4. Speak again while the agent is talking to interrupt.

Metrics (response time, task completion, state) update after each turn.

## Data Source

The backend loads reservation data in this order:

1. Environment variable `RESERVATIONS_URL` (public CSV or JSON URL).
2. Bundled fallback `api/reservations.json` if no URL is set or the fetch fails.

Results are cached in memory for `CACHE_TTL_SECONDS` (default 60).

**Vercel environment variables (optional)**
- `RESERVATIONS_URL` — public CSV or JSON link
- `CACHE_TTL_SECONDS` — cache duration (default 60)

## SECURE

**Trust boundaries**
- Microphone and speech synthesis run in the browser (Web Speech API).
- Backend receives only the transcript text.
- Data source is either the URL you set in `RESERVATIONS_URL` or the bundled JSON.
- No user audio or personal data is stored.

**Current enforcement**
- Explicit state machine: `BOOKING` | `INTERRUPTED` | `HANDOFF`.
- Availability tool reads only from the cached reservation data.
- In-memory cache with TTL; no persistent external store required.

**Explicit non-goals**
- Not connected to a live restaurant reservation system or telephony provider.
- Not using a remote LLM API (intent is rule-based).
- Not intended for production customer traffic without further hardening.

## VERIFY

1. Deploy and open the live URL in Chrome.
2. Hold the button and say “I’d like a table for two tomorrow.”  
   Confirm the reply uses data from the reservation source and state = `BOOKING`.
3. While the agent is speaking, hold the button again.  
   Confirm TTS stops and state = `INTERRUPTED`.
4. Say “I have a complaint.”  
   Confirm state = `HANDOFF` and no availability is confirmed.

Full verification points are in `docs/OPERATIONAL_CARD.md`.

## DOCUMENT

Operational details, trust boundaries, verification points, and next secure step:

→ [docs/OPERATIONAL_CARD.md](docs/OPERATIONAL_CARD.md)

## Stack

- HTML frontend with Web Speech API (microphone + TTS)
- Python serverless backend (`api/agent.py`) with SSE streaming
- In-memory cache + bundled JSON fallback
- Optional remote data via `RESERVATIONS_URL`
- Deployable on Vercel

## License

MIT
