#!/usr/bin/env python3
"""
Kilo HTTP Bridge
- Tiny, zero-dependency HTTP server that forwards commands to the Kilo daemon
  over the UNIX socket /opt/kilo/personality/kilo.sock
- Endpoints:
    GET /health        -> {"ok":true}
    GET /do?cmd=<cmd>  -> forwards: status|demo|sleep|wake|joke|scan|greeting
- For local use on 127.0.0.1 only (default).
"""
import http.server, socketserver, urllib.parse, json, socket, os

SOCK = "/opt/kilo/personality/kilo.sock"
HOST = "127.0.0.1"
PORT = 7861

def send_cmd(cmd: str):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect(SOCK)
        s.sendall((cmd.strip()+"\n").encode())
        data = s.recv(8192)
        try:
            return True, json.loads(data.decode())
        except Exception:
            return True, {"ok": True, "msg": data.decode(errors="ignore")}
    except Exception as e:
        return False, {"ok": False, "error": str(e)}
    finally:
        try: s.close()
        except Exception: pass

class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/health":
                return self._send(200, {"ok": True, "service": "kilo-bridge"})
            if parsed.path == "/do":
                q = urllib.parse.parse_qs(parsed.query or "")
                cmd = (q.get("cmd", [""])[0] or "").strip().lower()
                if not cmd:
                    return self._send(400, {"ok": False, "error": "missing cmd"})
                ok, resp = send_cmd(cmd)
                return self._send(200 if ok else 502, resp)
            return self._send(404, {"ok": False, "error": "not found"})
        except Exception as e:
            return self._send(500, {"ok": False, "error": str(e)})

def main():
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"[kilo-bridge] listening on http://{HOST}:{PORT}", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("[kilo-bridge] stopped.", flush=True)

if __name__ == "__main__":
    main()
