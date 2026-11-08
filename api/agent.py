# Voice Agent Backend
# - Data URL loaded from env var RESERVATIONS_URL (falls back to bundled JSON)
# - In-memory cache populated on first request (cold start)
# - SSE stream + state machine: BOOKING | INTERRUPTED | HANDOFF

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import time
import urllib.request
import csv
import io

RESERVATIONS_URL = os.environ.get("RESERVATIONS_URL", "").strip()
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))

_cache = {"rows": None, "expires": 0}

def _load_bundled():
    try:
        path = os.path.join(os.path.dirname(__file__), "reservations.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _fetch_remote():
    if not RESERVATIONS_URL:
        return None
    try:
        with urllib.request.urlopen(RESERVATIONS_URL, timeout=5) as resp:
            text = resp.read().decode("utf-8")
        if RESERVATIONS_URL.endswith(".json"):
            return json.loads(text)
        return list(csv.DictReader(io.StringIO(text)))
    except Exception:
        return None

def load_reservations():
    now = time.time()
    if _cache["rows"] is not None and now < _cache["expires"]:
        return _cache["rows"]

    rows = _fetch_remote()
    if rows is None:
        rows = _load_bundled()

    _cache["rows"] = rows
    _cache["expires"] = now + CACHE_TTL
    return rows

def extract_party(lower: str) -> str:
    word_map = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        "party of ten": "10", "party of 10": "10"
    }
    for word, num in word_map.items():
        if word in lower:
            return num
    m = re.search(r"\b([1-9]|10)\b", lower)
    if m:
        return m.group(1)
    return "2"

def check_availability(date, party):
    rows = load_reservations()
    party = str(party)
    for r in rows:
        if (str(r.get("party_size")) == party and
            str(r.get("date", "")).lower() == date.lower() and
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
    elif any(w in lower for w in ["table", "book", "reservation"]):
        intent = "make_reservation"
        party = extract_party(lower)
        date = "tomorrow" if "tomorrow" in lower else "saturday" if "saturday" in lower else "tomorrow"
        tool_result = check_availability(date, party)
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
            "records_loaded": len(load_reservations()),
            "data_source": "remote" if RESERVATIONS_URL else "bundled"
        }
    }

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        transcript = body.get("transcript", "")
        is_interrupt = bool(body.get("interrupt", False))

        result = process(transcript, is_interrupt)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
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
        rows = load_reservations()
        self.wfile.write(json.dumps({
            "status": "ready",
            "records": len(rows),
            "data_source": "remote" if RESERVATIONS_URL else "bundled",
            "cache_ttl": CACHE_TTL
        }).encode())
