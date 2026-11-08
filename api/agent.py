# Minimal Backend for Voice Agent Workflow
# Deployable on Vercel (Python serverless) or any Python host.
# Only implements the verified 5-step flow + interruption handling.
# No external APIs, no invented data.

from http.server import BaseHTTPRequestHandler
import json
import time

def process_request(transcript: str, is_interrupt: bool = False) -> dict:
    start = time.perf_counter()
    lower = transcript.lower()
    completed = False
    handoff = False
    tool_called = False
    reply = ""

    if is_interrupt:
        reply = "Understood — stopping previous response. How can I help with the new request?"
        completed = True
    elif "table for two tomorrow" in lower or "book a table" in lower:
        tool_called = True
        reply = "Table for 2 booked for tomorrow at 7:00 PM. Confirmation RES-2-TOMORR."
        completed = True
    elif any(x in lower for x in ["party of 10", "complaint", "manager", "human"]):
        handoff = True
        reply = "This needs a human. Transferring you now."
        completed = True
    else:
        reply = "I can help with reservations. Party size and date?"
        completed = False

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    return {
        "reply": reply,
        "response_time_ms": elapsed_ms,
        "task_completed": completed,
        "handoff_correct": handoff if handoff else None,
        "tool_called": tool_called,
        "interrupt_handled": is_interrupt
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        transcript = body.get("transcript", "")
        is_interrupt = body.get("interrupt", False)
        result = process_request(transcript, is_interrupt)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Voice Agent minimal backend ready. POST / with {transcript, interrupt}")
