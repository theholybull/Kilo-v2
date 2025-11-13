#!/usr/bin/env python3
"""
kilo_chat_http.py — local chat endpoint
- GET /health         -> {"ok": true}
- GET /ask?text=...   -> runs through kilo_brain, speaks via kilosay, returns JSON
- Updates eyes state to 'speak' before talking (no extra daemon speech)
"""
import http.server, socketserver, urllib.parse, json, subprocess, os, time

BASE = "/opt/kilo/personality"
STATE = os.path.join(BASE, "state.json")
KILOSAY = "/usr/local/bin/kilosay"
HOST, PORT = "127.0.0.1", 7863

def set_eyes(eyes="speak", sound=None):
    """Lightweight, safe state update (no extra speech)."""
    try:
        state = {}
        if os.path.exists(STATE):
            with open(STATE, "r", encoding="utf-8") as f:
                state = json.load(f)
        state["eyes_state"] = eyes
        if sound is not None:
            state["sound_cue"] = sound
        state["updated_ts"] = int(time.time())
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, STATE)
    except Exception as e:
        # Non-fatal
        pass

def brain_reply(text: str) -> str:
    try:
        out = subprocess.check_output(
            ["/usr/bin/env", "python3", os.path.join(BASE, "kilo_brain.py"), text],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore").strip()
        return out or "Say that again."
    except Exception:
        return "Say that again."

def speak(line: str):
    try:
        subprocess.Popen([KILOSAY, line], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b=json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        try:
            p = urllib.parse.urlparse(self.path)
            if p.path == "/health":
                return self._send(200, {"ok": True, "service": "kilo-chat"})
            if p.path == "/ask":
                q = urllib.parse.parse_qs(p.query or "")
                text = (q.get("text", [""])[0]).strip()
                if not text:
                    return self._send(400, {"ok": False, "error": "missing text"})
                # persona -> reply
                reply = brain_reply(text)
                # show eyes as speaking, then voice it
                set_eyes("speak", None)
                speak(reply)
                return self._send(200, {"ok": True, "reply": reply})
            return self._send(404, {"ok": False, "error": "not found"})
        except Exception as e:
            return self._send(500, {"ok": False, "error": str(e)})

if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), H) as httpd:
        httpd.allow_reuse_address = True
        print(f"[kilo-chat] listening on http://{HOST}:{PORT}", flush=True)
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
        print("[kilo-chat] stopped.", flush=True)
