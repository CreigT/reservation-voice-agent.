# Voice Agent Workflow

Minimal, browser-based demonstration of a 5-step voice agent pipeline for restaurant reservations.

Sponsored by Creignificent LLC.

Customer speaks → Speech-to-Text → LLM intent detection → Tool decision → Text-to-Speech, with explicit interruption (barge-in) and handoff handling.

## Quick Start

1. Open `index.html` in any browser, or  
2. Deploy to Vercel (import the repo).

Click the buttons to run:
- Normal booking
- Interruption (barge-in) test
- Handoff test

Metrics (response time, task completion, handoff) update after each run.

## SECURE

This is a client-side simulation with an optional backend that reads a public CSV.

**Trust boundaries**
- Frontend logic runs in the browser.
- Backend fetches only the public reservations.csv.
- No real external reservation system or LLM API is called.
- No user data is stored.

**Current enforcement**
- Deterministic rule-based decisions for the three demo paths (booking, interrupt, handoff).
- Data source is the public CSV in this repo.

**Explicit non-goals**
- Not a production voice agent.
- Not connected to any live reservation system, telephony provider, or LLM API.
- Not intended for real customer traffic.

## VERIFY

Verification is manual and immediate:

1. Open the deployed URL (or `index.html`).
2. Run **Normal booking** — confirm tool path, task completion = Yes, and reply uses CSV data.
3. Run **Test interruption** — confirm previous response is stopped and new turn is processed.
4. Run **Test handoff** — confirm handoff is triggered and no reservation tool is called.

All three cases and expected outcomes are listed in `docs/OPERATIONAL_CARD.md`.

## DOCUMENT

Full operational details, trust boundaries, verification points, and next secure step:

→ [docs/OPERATIONAL_CARD.md](docs/OPERATIONAL_CARD.md)

## Stack

- HTML frontend
- Python serverless backend (`api/agent.py`)
- Public CSV data source
- Deployable on Vercel

## License

MIT
