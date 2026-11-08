# Voice Agent Workflow

Minimal, browser-based demonstration of a 5-step voice agent pipeline for restaurant reservations.

Customer speaks → Speech-to-Text → LLM intent detection → Tool decision → Text-to-Speech, with explicit interruption (barge-in) and handoff handling.

## Quick Start

1. Open `index.html` in any browser, or  
2. Deploy the single file to Vercel (drag-and-drop).

Click the buttons to run:
- Normal booking
- Interruption (barge-in) test
- Handoff test

Metrics (response time, task completion, handoff) update after each run.

## SECURE

This is a client-side simulation only.

**Trust boundaries**
- All logic runs in the browser.
- No network requests are made.
- No real tools, APIs, or external systems are called.
- No user data is stored or transmitted.

**Current enforcement**
- Deterministic rule-based decisions for the three demo paths (booking, interrupt, handoff).
- No dynamic code execution or external dependencies.

**Explicit non-goals**
- Not a production voice agent.
- Not connected to any reservation system, telephony provider, or LLM API.
- Not intended for real customer traffic.

## VERIFY

Verification is manual and immediate:

1. Open `index.html`.
2. Run **Normal booking** — confirm tool path and task completion = Yes.
3. Run **Test interruption** — confirm previous response is stopped and new turn is processed.
4. Run **Test handoff** — confirm handoff is triggered and no reservation tool is called.

All three cases and expected outcomes are listed in `docs/OPERATIONAL_CARD.md`.

## DOCUMENT

Full operational details, trust boundaries, verification points, and next secure step:

→ [docs/OPERATIONAL_CARD.md](docs/OPERATIONAL_CARD.md)

## Stack

- Single HTML file
- No build step
- No backend required
- Deployable on Vercel or any static host

## License

MIT
