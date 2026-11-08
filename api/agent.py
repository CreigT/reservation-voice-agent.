# Voice Agent — 6-stage flow
# WAKE → LISTEN → UNDERSTAND → ACT → SPEAK → LOG
# Free path: browser STT/TTS + rule NLU. Paid STT/TTS/LLM optional via env.

from http.server import BaseHTTPRequestHandler
import json, os, re, time, uuid, urllib.request, csv, io
from datetime import datetime

RESERVATIONS_URL = os.environ.get("RESERVATIONS_URL", "").strip()
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))

_cache = {"rows": None, "expires": 0}
_users = {}
_sessions = {}
_agent_sessions = {}
_bookings = []
_audio_records = []
_handoff_tickets = []
_call_logs = []

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

def load_tables():
    now = time.time()
    if _cache["rows"] is not None and now < _cache["expires"]:
        return _cache["rows"]
    rows = _fetch_remote() or _load_bundled()
    _cache["rows"] = rows
    _cache["expires"] = now + CACHE_TTL
    return rows

def extract_party(lower):
    word_map = {"one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10","party of ten":"10","party of 10":"10"}
    for w, n in word_map.items():
        if w in lower:
            return n
    m = re.search(r"\b([1-9]|10)\b", lower)
    return m.group(1) if m else "2"

def extract_time(lower):
    m = re.search(r"\b([1-9]|1[0-2])(?::([0-5][0-9]))?\s*(am|pm)?\b", lower)
    return m.group(0) if m else None

def check_availability(date, party, time_pref=None):
    rows = load_tables()
    party = str(party)
    matches = [r for r in rows if str(r.get("party_size"))==party and str(r.get("date","")).lower()==date.lower() and r.get("status")=="available"]
    if time_pref:
        for r in matches:
            if time_pref.replace(" ","") in str(r.get("time","")).replace(":",""):
                return {"available": True, "time": r.get("time"), "row": r, "suggestions": []}
    if matches:
        return {"available": True, "time": matches[0].get("time"), "row": matches[0], "suggestions": [m.get("time") for m in matches[1:3]]}
    alts = [r.get("time") for r in rows if str(r.get("date","")).lower()==date.lower() and r.get("status")=="available"][:2]
    return {"available": False, "suggestions": alts}

def get_user(token):
    if not token:
        return None
    uid = _sessions.get(token)
    if not uid:
        return None
    for u in _users.values():
        if u["id"] == uid:
            return u
    return None

def understand(lower, is_interrupt):
    if is_interrupt:
        return "interruption"
    if any(w in lower for w in ["complaint","manager","human","party of 10","party of ten"]):
        return "handoff"
    if any(w in lower for w in ["hello","hi","hey","how are you","thanks","thank you"]):
        return "smalltalk"
    if any(w in lower for w in ["table","book","reservation","confirm","yes","book it"]):
        return "booking"
    return "clarification"

def act(intent, transcript, user, session_id):
    lower = transcript.lower().strip()
    tool_result = None
    booking = None
    ticket = None
    reply = ""
    if intent == "interruption":
        reply = "Stopping. What would you like instead?"
    elif intent == "handoff":
        ticket = {"id": str(uuid.uuid4())[:8], "session_id": session_id, "user_id": user["id"] if user else None, "reason": transcript, "status": "open", "created": datetime.utcnow().isoformat()+"Z"}
        _handoff_tickets.append(ticket)
        reply = "Connecting you now."
    elif intent == "smalltalk":
        reply = "Happy to help. How many people and what day?"
    elif intent == "booking":
        party = extract_party(lower)
        date = "tomorrow" if "tomorrow" in lower else "saturday" if "saturday" in lower else "friday" if "friday" in lower else "tomorrow"
        time_pref = extract_time(lower)
        tool_result = check_availability(date, party, time_pref)
        if tool_result["available"]:
            if user and any(w in lower for w in ["confirm","yes","book it"]):
                booking = {"id": str(uuid.uuid4())[:8], "session_id": session_id, "user_id": user["id"], "user_email": user["email"], "party_size": party, "date": date, "time": tool_result["time"], "status": "confirmed", "created": datetime.utcnow().isoformat()+"Z"}
                _bookings.append(booking)
                reply = f"Booked. Confirmation {booking['id']} for {party} on {date} at {tool_result['time']}."
            else:
                reply = f"Table for {party} is available {date} at {tool_result['time']}. Say confirm to book."
        else:
            sugg = tool_result.get("suggestions") or []
            reply = f"No table for {party} on {date}." + (f" Next slots: {', '.join(sugg)}." if sugg else " Want another day?")
    else:
        reply = "I can check tables. How many people and what day?"
    return reply, tool_result, booking, ticket

def log_call(session_id, transcript, latency_ms, task_completed, handoff, intent):
    rec = {"id": str(uuid.uuid4())[:8], "session_id": session_id, "transcript": transcript, "latency_ms": latency_ms, "task_completed": task_completed, "handoff": handoff, "intent": intent, "ts": datetime.utcnow().isoformat()+"Z"}
    _call_logs.append(rec)
    return rec

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
            name = (body.get("name") or "").strip() or (email.split("@")[0] if email else "guest")
            if not email or "@" not in email:
                return self._json(400, {"error": "valid email required"})
            if email in _users:
                return self._json(409, {"error": "email already registered"})
            uid = str(uuid.uuid4())
            _users[email] = {"id": uid, "email": email, "name": name, "created": datetime.utcnow().isoformat()+"Z"}
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

        if path == "/api/wake":
            token = body.get("token") or self.headers.get("Authorization","").replace("Bearer ","")
            user = get_user(token)
            session_id = str(uuid.uuid4())[:8]
            tables = load_tables()
            _agent_sessions[session_id] = {"user_id": user["id"] if user else None, "started": datetime.utcnow().isoformat()+"Z", "context": {"tables_loaded": len(tables)}}
            return self._json(200, {"session_id": session_id, "tables_loaded": len(tables)})

        if path == "/api/audio":
            token = body.get("token") or self.headers.get("Authorization","").replace("Bearer ","")
            user = get_user(token)
            if not user:
                return self._json(401, {"error": "auth required"})
            rec = {"id": str(uuid.uuid4())[:8], "user_id": user["id"], "session_id": body.get("session_id"), "transcript": body.get("transcript",""), "audio_ref": body.get("audio_ref"), "ts": datetime.utcnow().isoformat()+"Z"}
            _audio_records.append(rec)
            return self._json(200, {"stored": True, "record": rec})

        token = body.get("token") or self.headers.get("Authorization","").replace("Bearer ","")
        user = get_user(token)
        session_id = body.get("session_id") or "none"
        transcript = body.get("transcript","")
        is_interrupt = bool(body.get("interrupt", False))

        start = time.perf_counter()
        intent = understand(transcript.lower(), is_interrupt)
        reply, tool_result, booking, ticket = act(intent, transcript, user, session_id)
        latency = round((time.perf_counter() - start) * 1000, 1)
        task_completed = intent in ("booking","handoff","smalltalk")
        log_call(session_id, transcript, latency, task_completed, intent=="handoff", intent)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        payload = {"delta": reply, "intent": intent, "state": intent.upper() if intent != "booking" else "BOOKING", "tool_result": tool_result, "booking": booking, "ticket": ticket, "metrics": {"response_time_ms": latency, "task_completed": task_completed, "handoff": intent == "handoff", "records_loaded": len(load_tables())}}
        self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
        self.wfile.flush()

    def do_GET(self):
        path = self.path.split("?")[0]
        token = self.headers.get("Authorization","").replace("Bearer ","")
        user = get_user(token)
        if path == "/api/bookings":
            if not user:
                return self._json(401, {"error": "auth required"})
            return self._json(200, {"bookings": [b for b in _bookings if b["user_id"]==user["id"]]})
        if path == "/api/audio":
            if not user:
                return self._json(401, {"error": "auth required"})
            return self._json(200, {"audio": [a for a in _audio_records if a["user_id"]==user["id"]]})
        if path == "/api/handoffs":
            return self._json(200, {"tickets": _handoff_tickets})
        if path == "/dashboard/calls" or path == "/api/calls":
            return self._json(200, {"calls": _call_logs[-50:]})
        rows = load_tables()
        self._json(200, {"status": "ready", "tables": len(rows), "users": len(_users), "sessions": len(_agent_sessions), "bookings": len(_bookings), "audio_records": len(_audio_records), "handoffs": len(_handoff_tickets), "calls_logged": len(_call_logs)})
