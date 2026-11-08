# Voice Agent Backend
# - Auth (register/login) with session tokens
# - Real booking writes (in-memory store, survives warm instance)
# - Audio record storage (transcript + optional audio ref)
# - Data URL from env, bundled JSON fallback, in-memory cache

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import time
import uuid
import urllib.request
import csv
import io
from datetime import datetime

RESERVATIONS_URL = os.environ.get("RESERVATIONS_URL", "").strip()
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))

_cache = {"rows": None, "expires": 0}
_users = {}
_sessions = {}
_bookings = []
_audio_records = []

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

def get_user_from_token(token):
    if not token:
        return None
    uid = _sessions.get(token)
    if not uid:
        return None
    for u in _users.values():
        if u["id"] == uid:
            return u
    return None

def process(transcript: str, is_interrupt: bool = False, user=None):
    start = time.perf_counter()
    lower = transcript.lower().strip()
    state = "BOOKING"
    intent = "unknown"
    tool_result = None
    reply = ""
    booking = None

    if is_interrupt:
        state = "INTERRUPTED"
        intent = "interrupt"
        reply = "Stopping. What would you like instead?"
    elif any(w in lower for w in ["complaint", "manager", "human", "party of 10", "party of ten"]):
        state = "HANDOFF"
        intent = "handoff"
        reply = "Transferring you to a person now."
    elif any(w in lower for w in ["table", "book", "reservation", "confirm"]):
        intent = "make_reservation"
        party = extract_party(lower)
        date = "tomorrow" if "tomorrow" in lower else "saturday" if "saturday" in lower else "tomorrow"
        tool_result = check_availability(date, party)
        if tool_result["available"]:
            if user and ("confirm" in lower or "yes" in lower or "book it" in lower):
                booking = {
                    "id": str(uuid.uuid4())[:8],
                    "user_id": user["id"],
                    "user_email": user["email"],
                    "party_size": party,
                    "date": date,
                    "time": tool_result["time"],
                    "status": "confirmed",
                    "created": datetime.utcnow().isoformat() + "Z"
                }
                _bookings.append(booking)
                reply = f"Booked. Confirmation {booking['id']} for {party} on {date} at {tool_result['time']}."
            else:
                reply = f"Yes, a table for {party} is available {date} at {tool_result['time']}. Say confirm to book it."
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
        "booking": booking,
        "metrics": {
            "response_time_ms": elapsed,
            "task_completed": state in ("BOOKING", "HANDOFF") and intent != "unknown",
            "handoff": state == "HANDOFF",
            "records_loaded": len(load_reservations()),
            "data_source": "remote" if RESERVATIONS_URL else "bundled"
        }
    }

class handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path.split("?")[0]

        if path == "/api/auth/register":
            email = (body.get("email") or "").strip().lower()
            name = (body.get("name") or "").strip() or email.split("@")[0]
            if not email or "@" not in email:
                return self._json(400, {"error": "valid email required"})
            if email in _users:
                return self._json(409, {"error": "email already registered"})
            uid = str(uuid.uuid4())
            _users[email] = {"id": uid, "email": email, "name": name, "created": datetime.utcnow().isoformat() + "Z"}
            token = str(uuid.uuid4())
            _sessions[token] = uid
            return self._json(200, {"token": token, "user": _users[email]})

        if path == "/api/auth/login":
            email = (body.get("email") or "").strip().lower()
            user = _users.get(email)
            if not user:
                return self._json(401, {"error": "unknown email"})
            token = str(uuid.uuid4())
            _sessions[token] = user["id"]
            return self._json(200, {"token": token, "user": user})

        if path == "/api/audio":
            token = body.get("token") or self.headers.get("Authorization", "").replace("Bearer ", "")
            user = get_user_from_token(token)
            if not user:
                return self._json(401, {"error": "auth required"})
            rec = {
                "id": str(uuid.uuid4())[:8],
                "user_id": user["id"],
                "transcript": body.get("transcript", ""),
                "audio_ref": body.get("audio_ref"),
                "ts": datetime.utcnow().isoformat() + "Z"
            }
            _audio_records.append(rec)
            return self._json(200, {"stored": True, "record": rec})

        token = body.get("token") or self.headers.get("Authorization", "").replace("Bearer ", "")
        user = get_user_from_token(token)
        transcript = body.get("transcript", "")
        is_interrupt = bool(body.get("interrupt", False))
        result = process(transcript, is_interrupt, user)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        payload = {
            "delta": result["reply"],
            "metrics": result["metrics"],
            "intent": result["intent"],
            "state": result["state"],
            "tool_result": result["tool_result"],
            "booking": result["booking"]
        }
        self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
        self.wfile.flush()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/bookings":
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            user = get_user_from_token(token)
            if not user:
                return self._json(401, {"error": "auth required"})
            mine = [b for b in _bookings if b["user_id"] == user["id"]]
            return self._json(200, {"bookings": mine})
        if path == "/api/audio":
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            user = get_user_from_token(token)
            if not user:
                return self._json(401, {"error": "auth required"})
            mine = [a for a in _audio_records if a["user_id"] == user["id"]]
            return self._json(200, {"audio": mine})
        rows = load_reservations()
        self._json(200, {
            "status": "ready",
            "records": len(rows),
            "users": len(_users),
            "bookings": len(_bookings),
            "audio_records": len(_audio_records),
            "data_source": "remote" if RESERVATIONS_URL else "bundled",
            "cache_ttl": CACHE_TTL
        })
