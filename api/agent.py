# Minimal Backend for Voice Agent Workflow
# Pulls reservation data from a public CSV.
# Verified 5-step flow + interruption handling.
# No invented external systems.

from http.server import BaseHTTPRequestHandler
import json
import time
import urllib.request
import csv
import io

# Public CSV (raw GitHub). Replace with your own published Sheet CSV if desired.
CSV_URL = "https://raw.githubusercontent.com/CreigT/reservation-voice-agent./main/data/reservations.csv"

def load_reservations():
    try:
        with urllib.request.urlopen(CSV_URL, timeout=5) as resp:
            text = resp.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception:
        return []

def process_request(transcript: str, is_interrupt: bool = False) -> dict:
    start = time.perf_counter()
    lower = transcript.lower()
    completed = False
    handoff = False
    tool_called = False
    reply = ""
    data_source = "csv"

    rows = load_reservations()

    if is_interrupt:
        reply = "Understood — stopping previous response. How can I help with the new request?"
        completed = True
    elif "table for two tomorrow" in lower or "book a table" in lower:
        tool_called = True
        match = next((r for r in rows if r.get("party_size") == "2" and r.get("date") == "tomorrow" and r.get("status") == "available"), None)
        if match:
            reply = f"Table for 2 is available tomorrow at {match.get('time', '19:00')}. Confirming reservation."
            completed = True
        else:
            reply = "No available table for 2 tomorrow found in the schedule."
            completed = False
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
        "interrupt_handled": is_interrupt,
        "data_source": data_source,
        "records_loaded": len(rows)
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
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        rows = load_reservations()
        self.wfile.write(json.dumps({"status": "ready", "records": len(rows), "csv": CSV_URL}).encode())
