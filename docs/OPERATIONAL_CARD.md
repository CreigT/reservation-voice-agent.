# Operational Card — Voice Agent Workflow

Sponsored by Creignificent LLC.

## Purpose
Working voice agent that accepts spoken reservation requests, checks availability against a data source, speaks the reply, and handles interruption and human handoff.

## Trust Boundaries
- **Input**: Spoken text from the browser Web Speech API (user microphone). Only the transcript is sent to the backend.
- **Processing**: Python serverless handler (`api/agent.py`) with explicit state machine.
- **Output**: SSE stream (`delta`, `metrics`, `intent`, `state`) + browser TTS.
- **Data**: Loaded from `RESERVATIONS_URL` (if set) or bundled `api/reservations.json`. Cached in memory with TTL. No user audio or personal data is stored.

## Current Enforcement
- State machine: `BOOKING` | `INTERRUPTED` | `HANDOFF`.
- Availability tool reads only from the cached reservation data.
- Party size extracted from words (one–ten) or digits (1–10).
- In-memory cache with configurable TTL (`CACHE_TTL_SECONDS`, default 60).
- Metrics returned: response time, task completion, handoff flag, records loaded, data source.

## Explicit Non-Goals
- Not connected to a live restaurant reservation system or telephony provider.
- Not using a remote LLM API (intent is rule-based).
- Not storing raw audio or user identity.
- Not intended for production customer traffic without further hardening.

## Verification Points
| Test | Input | Expected Result |
|------|--------|-----------------|
| Normal booking | “I’d like a table for two tomorrow.” | State = BOOKING, availability tool returns data, spoken reply |
| Party size | “Book a table for six on Saturday.” | Party correctly parsed as 6 |
| Interruption | Speak while agent is talking | TTS stops, state = INTERRUPTED |
| Handoff | “I have a complaint…” or “party of 10” | State = HANDOFF, no availability confirmed |

All tests are executable after deploying to Vercel and opening the live URL in Chrome.

## Next Secure Step
- Add an explicit policy gate before any irreversible action (admit / review / deny).
- Log tool decisions.
- Keep raw audio out of storage.
- Require human approval for booking confirmation if a write path is added.

---
*Documentation defines the intended trust boundaries. Code is the implementation.*
