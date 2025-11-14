#!/usr/bin/env python3
"""
Kilo Head Backend - minimal HTTP API for the head app

Listens on 0.0.0.0:8080 by default and exposes:
  GET  /health        -> {"ok": true, "service": "kilo-head-backend"}
  GET  /state         -> {"ok": true, "mode": "...", "emotion": "...", "last_update": "..."}
  POST /setEmotion    -> {"ok": true}
  POST /setMode       -> {"ok": true}

Later this can call into your Kilo personality engine and Viam,
but for now it just keeps state in memory so we can wire the app cleanly.
"""
import http.server
import json
import socketserver
import datetime

HOST = "0.0.0.0"
PORT = 8080  # can change if this conflicts with something else

STATE = {
    "mode": "idle",
    "emotion": "neutral",
    "last_update": None,
}

def _now_iso():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

class Handler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Keep logs less noisy; you can change this if you want.
        print("[kilo-head-backend]", fmt % args)

    def do_OPTIONS(self):
        # Simple CORS preflight handler
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._send_json(200, {"ok": True, "service": "kilo-head-backend"})

        if self.path.startswith("/state"):
            state = dict(STATE)
            state["ok"] = True
            if state["last_update"] is None:
                state["last_update"] = _now_iso()
            return self._send_json(200, state)

        # Default: simple landing JSON instead of HTML
        return self._send_json(200, {
            "ok": True,
            "service": "kilo-head-backend",
            "endpoints": ["/health", "/state", "/setEmotion", "/setMode"],
        })

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            return self._send_json(400, {"ok": False, "error": f"invalid json: {e}"})

        if self.path.startswith("/setEmotion"):
            emo = (data.get("emotion") or "").strip().lower()
            if not emo:
                return self._send_json(400, {"ok": False, "error": "missing 'emotion'"})
            STATE["emotion"] = emo
            STATE["last_update"] = _now_iso()
            # TODO: hook into actual personality engine here
            return self._send_json(200, {"ok": True, "emotion": emo})

        if self.path.startswith("/setMode"):
            mode = (data.get("mode") or "").strip().lower()
            if not mode:
                return self._send_json(400, {"ok": False, "error": "missing 'mode'"})
            STATE["mode"] = mode
            STATE["last_update"] = _now_iso()
            # TODO: hook into actual robot/autonomy here
            return self._send_json(200, {"ok": True, "mode": mode})

        return self._send_json(404, {"ok": False, "error": "not found"})

if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"[kilo-head-backend] listening on http://{HOST}:{PORT}", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("[kilo-head-backend] stopped.", flush=True)
