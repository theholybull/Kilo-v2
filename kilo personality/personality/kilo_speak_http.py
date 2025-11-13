#!/usr/bin/env python3
import http.server, socketserver, urllib.parse, json, subprocess, shlex

HOST="127.0.0.1"; PORT=7862
def speak(text):
    return subprocess.call(["/usr/local/bin/kilosay", text])

class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b=json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        try:
            p=urllib.parse.urlparse(self.path)
            if p.path=="/health": return self._send(200, {"ok":True,"service":"kilo-speak"})
            if p.path=="/speak":
                q=urllib.parse.parse_qs(p.query or "")
                text=(q.get("text",[""])[0]).strip()
                if not text: return self._send(400, {"ok":False,"error":"missing text"})
                rc=speak(text)
                return self._send(200, {"ok": rc==0})
            return self._send(404, {"ok":False,"error":"not found"})
        except Exception as e:
            return self._send(500, {"ok":False,"error":str(e)})

if __name__=="__main__":
    with socketserver.TCPServer((HOST,PORT), H) as httpd:
        httpd.allow_reuse_address=True
        print(f"[kilo-speak] listening on http://{HOST}:{PORT}", flush=True)
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
        print("[kilo-speak] stopped.", flush=True)
