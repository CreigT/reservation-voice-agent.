# Voice Agent Backend — SSE + cache + state machine
# Actual working flow: loads public CSV (cached), runs check_availability,
# streams {delta, metrics, intent}, handles BOOKING | INTERRUPTED | HANDOFF.

from http.server import BaseHTTPRequestHandler
import json
import time
import urllib.request
import csv
import io

CSV_URL = "https://raw.githubusercontent.com/CreigT/reservation-voice-agent./main/data/reservations.csv"
CACHE_TTL = 30  # seconds

_cache = {"rows": [], "expires": 0}

def load_reservations_cached():
    now = time.time()
    if _cache["rows"] and now < _cache["expires"]:
        return _cache["rows"]
    try:
        with urllib.request.urlopen(CSV_URL, timeout=5) as resp:
            text = resp.read().decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
        _cache["rows"] = rows
        _cache["expires"] = now + CACHE_TTL
        return rows
    except Exception:
        return _cache["rows"]

def check_availability(date, time_str, party):
    rows = load_reservations_cached()
    party = str(party)
    for r in rows:
        if (r.get("party_size") == party and
            r.get("date", "").lower() == date.lower() and
            r.get("status") == "available"):
            return {"available": True, "time": r.get("time"), "row": r}
    return {"available": False}

def process(transcript: str, is_interrupt: bool = False):
    start = time.perf_counter()
    lower = transcript.lower().strip()
    state = "BOOKING"
    intent = "unknown"
    tool_result = None
    reply = ""

    if is_interrupt:
        state = "INTERRUPTED"
        intent = "interrupt"
        reply = "Stopping. What would you like instead?"
    elif any(w in lower for w in ["complaint", "manager", "human", "party of 10", "party of ten"]):
        state = "HANDOFF"
        intent = "handoff"
        reply = "Transferring you to a person now."
    elif "table" in lower or "book" in lower or "reservation" in lower:
        intent = "make_reservation"
        party = "2" if "two" in lower or "2" in lower else "4" if "four" in lower or "4" in lower else "2"
        date = "tomorrow" if "tomorrow" in lower else "saturday" if "saturday" in lower else "tomorrow"
        tool_result = check_availability(date, "19:00", party)
        if tool_result["available"]:
            reply = f"Yes, a table for {party} is available {date} at {tool_result['time']}. Shall I book it?"
        else:
            reply = f"No table for {party} available {date}. Want another time?"
    else:
        reply = "I can check availability. How many people and what day?"

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    return {
        "state": state,
        "intent": intent,
        "reply": reply,
        "tool_result": tool_result,
        "metrics": {
            "response_time_ms": elapsed,
            "task_completed": state in ("BOOKING", "HANDOFF") and intent != "unknown",
            "handoff": state == "HANDOFF",
            "records_loaded": len(load_reservations_cached())
        }
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        transcript = body.get("transcript", "")
        is_interrupt = body.get("interrupt", False)

        result = process(transcript, is_interrupt)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        payload = {
            "delta": result["reply"],
            "metrics": result["metrics"],
            "intent": result["intent"],
            "state": result["state"],
            "tool_result": result["tool_result"]
        }
        self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
        self.wfile.flush()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        rows = load_reservations_cached()
        self.wfile.write(json.dumps({"status": "ready", "records": len(rows)}).encode())
