# Operational Card — Voice Agent Workflow

## Purpose
Demonstrate a complete voice agent loop for a restaurant reservation request, including intent detection, tool decision, spoken response, interruption handling, and human handoff.

## Trust Boundaries
- **Input**: Simulated spoken text (hard-coded demo utterances).
- **Processing**: Client-side JavaScript only. No LLM API, no external tool, no network call.
- **Output**: Text log + metrics displayed in the browser.
- **Data**: Nothing leaves the page. No storage, no cookies, no analytics.

## Current Enforcement
- Three fixed paths only:
  1. Normal booking (“table for two tomorrow”) → tool decision + confirmation
  2. Interruption during response → stop previous turn, process new input
  3. Handoff triggers (complaint, large party, human request) → handoff message, no tool call
- Metrics recorded locally: response time (ms), task completion (Yes/No), handoff status.

## Explicit Non-Goals
- Real speech-to-text or text-to-speech
- Live LLM or function calling
- Connection to any reservation, calendar, or CRM system
- Production telephony or multi-user support
- Persistent memory or user accounts

## Verification Points
| Test | Input | Expected Result |
|------|--------|-----------------|
| Normal booking | “I’d like to book a table for two tomorrow.” | Tool path taken, task completed = Yes, handoff = No |
| Interruption | Customer speaks while agent is responding | Previous TTS stopped, new utterance processed, interrupt handled |
| Handoff | “I have a complaint…” or “party of 10” | Handoff = Yes, no reservation tool called, task completed = Yes |

All tests are executable by opening `index.html` and clicking the corresponding button.

## Next Secure Step
If a real backend or live LLM is added later:
- Move tool execution behind an explicit policy gate (admit / review / deny).
- Log every tool decision.
- Keep raw audio out of long-term storage.
- Require human approval for irreversible actions.

---
*Documentation defines the intended trust boundaries. Code is the implementation.*
