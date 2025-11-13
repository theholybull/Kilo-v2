#!/usr/bin/env python3
"""
Kilo Personality Daemon (socket + state file + AutoSpeech)
- UNIX socket: /opt/kilo/personality/kilo.sock
- State file:  /opt/kilo/personality/state.json
- Commands: status, demo, sleep, wake, joke, scan, greeting
- AutoSpeech: speaks lines via /usr/local/bin/kilosay when enabled.
  Toggle with env KILO_AUTOSPEAK=1|0 (default 1).
"""
import os, sys, time, signal, argparse, json, socket, select, errno, subprocess, threading

RUN = True
SOCK_PATH = "/opt/kilo/personality/kilo.sock"
STATE_PATH = "/opt/kilo/personality/state.json"
HEARTBEAT_SEC = 10
AUTOSPEAK = (os.environ.get("KILO_AUTOSPEAK","1").lower() in ("1","true","yes","on"))
KILOSAY = "/usr/local/bin/kilosay"

STATE = {
    "mode": "idle",
    "last_cmd": None,
    "last_status": "Starting",
    "eyes_state": "idle",
    "sound_cue": None,
    "base": None,
    "updated_ts": None
}

def _speak_async(text: str):
    """Fire-and-forget speaking in a thread so we never block the main loop."""
    if not AUTOSPEAK or not text:
        return
    if not os.path.isfile(KILOSAY) or not os.access(KILOSAY, os.X_OK):
        print("[kilo] warn: kilosay not found/executable; skipping speech", flush=True)
        return
    def runner(line: str):
        try:
            # Use a short timeout guard by running non-blocking; let audio system handle playback.
            subprocess.Popen([KILOSAY, line], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[kilo] warn: kilosay failed: {e}", flush=True)
    t = threading.Thread(target=runner, args=(text,), daemon=True)
    t.start()

def write_state():
    try:
        STATE["updated_ts"] = int(time.time())
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(STATE, f, indent=2)
        os.replace(tmp, STATE_PATH)
    except Exception as e:
        print(f"[kilo] warn: cannot write state.json: {e}", flush=True)

def _sig_handler(signum, frame):
    global RUN
    print(f"[kilo] Caught signal {signum}; shutting down...", flush=True)
    RUN = False

def safe_read(path, kind="text"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            if kind == "json":
                json.load(f)
            else:
                f.read(512)
        print(f"[kilo] ok: {path}", flush=True)
        return True
    except Exception as e:
        print(f"[kilo] warn: cannot read {path}: {e}", flush=True)
        return False

def _ok(msg): return {"ok": True, "msg": msg}
def _err(msg): return {"ok": False, "error": msg}

def set_ui(eyes=None, sound=None):
    if eyes:  STATE["eyes_state"] = eyes
    if sound: STATE["sound_cue"]  = sound
    write_state()

# ---- Command handlers ----
def do_status():
    msg = f"mode={STATE['mode']}, last_cmd={STATE['last_cmd']}, status={STATE['last_status']}"
    print(f"[kilo] STATUS: {msg}", flush=True)
    set_ui(eyes="speak", sound=None)
    # No autospeak for status (too chatty)
    return _ok(msg)

def do_greeting():
    line = "Kilo Truck—fully loaded with charm and sarcasm."
    print(f"[kilo] SAY: {line}", flush=True)
    set_ui(eyes="happy", sound="rev_happy")
    _speak_async(line)
    return _ok(line)

def do_joke():
    line = "Why don’t Dodges tell jokes? They can’t handle the punchline."
    print(f"[kilo] JOKE: {line}", flush=True)
    set_ui(eyes="speak", sound=None)
    _speak_async(line)
    return _ok(line)

def do_scan():
    line = "Scanning. Holler if you see a Vespa before I do."
    print(f"[kilo] SCAN: {line}", flush=True)
    set_ui(eyes="focus", sound=None)
    # No autospeak; keep background actions quiet
    return _ok(line)

def do_sleep():
    STATE["mode"] = "sleep"
    line = "Fine, but I’m dreaming of Vespas again."
    print(f"[kilo] SLEEP: {line}", flush=True)
    set_ui(eyes="sleep", sound="idle_low")
    _speak_async(line)
    return _ok(line)

def do_wake():
    STATE["mode"] = "idle"
    line = "Up and running. Didn’t even cross my fingers this time."
    print(f"[kilo] WAKE: {line}", flush=True)
    set_ui(eyes="happy", sound="rev_startup")
    _speak_async(line)
    return _ok(line)

def do_demo():
    STATE["mode"] = "demo"
    seq = [
        ("boot",    "Kilo online. Batteries charged, patience limited.", "happy", "rev_startup"),
        ("scan",    "Scanning my surroundings… no Dodges detected. Life’s good.", "focus", None),
        ("quip",    "All squared away. Don’t mess it up.", "speak", None),
        ("dreams",  "If you see a Vespa, wake me gently.", "sleep", "idle_low"),
        ("wake",    "Demo over. I’m still cooler than Barney.", "happy", "rev_startup"),
    ]
    for step, line, eyes, sound in seq:
        print(f"[kilo] DEMO [{step}]: {line}", flush=True)
        set_ui(eyes=eyes, sound=sound)
        if step in ("boot","wake","quip"):  # tasteful speaking, not every step
            _speak_async(line)
        time.sleep(0.2)
    STATE["mode"] = "idle"
    return _ok("demo complete")

COMMANDS = {
    "status":   do_status,
    "greeting": do_greeting,
    "joke":     do_joke,
    "scan":     do_scan,
    "sleep":    do_sleep,
    "wake":     do_wake,
    "demo":     do_demo,
}

def handle_cmd(raw: str):
    raw = (raw or "").strip()
    STATE["last_cmd"] = raw
    if not raw: return _err("empty command")
    # accept either plain word or tiny JSON {"cmd":"status"}
    try:
        obj = json.loads(raw)
        cmd = str(obj.get("cmd","")).strip().lower()
    except Exception:
        cmd = raw.split()[0].lower()
    fn = COMMANDS.get(cmd)
    if not fn: return _err(f"unknown command: {cmd}")
    try:
        resp = fn()
        STATE["last_status"] = f"{cmd} ok"
        write_state()
        return resp
    except Exception as e:
        STATE["last_status"] = f"{cmd} error: {e}"
        write_state()
        return _err(str(e))

def open_socket():
    try: os.unlink(SOCK_PATH)
    except FileNotFoundError: pass
    except Exception as e: print(f"[kilo] warn: unlink old socket failed: {e}", flush=True)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o666)
    s.listen(4)
    s.setblocking(False)
    print(f"[kilo] socket listening at {SOCK_PATH}", flush=True)
    return s

def main():
    parser = argparse.ArgumentParser(description="Kilo Personality (socket + state + autospeech)")
    parser.add_argument("--daemon", action="store_true", help="run in daemon mode")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    base = os.environ.get("KILO_PERSONALITY_DIR", "/opt/kilo/personality")
    STATE["base"] = base
    print(f"[kilo] Starting. base={base} daemon={args.daemon} autospeak={AUTOSPEAK}", flush=True)

    # Probe content (non-fatal)
    safe_read(os.path.join(base, "persona.json"), "json")
    safe_read(os.path.join(base, "people.json"), "json")
    safe_read(os.path.join(base, "quips.yaml"), "text")
    safe_read(os.path.join(base, "persona_full.yaml"), "text")

    # Initialize state file
    write_state()

    server = open_socket()
    clients = []
    last_beat = 0

    try:
        while RUN:
            now = time.time()
            if now - last_beat >= HEARTBEAT_SEC:
                print(f"[kilo] heartbeat mode={STATE['mode']} eyes={STATE['eyes_state']} sound={STATE['sound_cue']}", flush=True)
                last_beat = now
                write_state()

            rlist = [server] + clients
            readable, _, _ = select.select(rlist, [], [], 1.0)

            for s in readable:
                if s is server:
                    try:
                        conn, _ = server.accept()
                        conn.setblocking(False)
                        clients.append(conn)
                    except OSError as e:
                        if getattr(e, "errno", None) != errno.EAGAIN:
                            print(f"[kilo] accept error: {e}", flush=True)
                    continue

                try:
                    data = s.recv(4096)
                except OSError as e:
                    print(f"[kilo] recv error: {e}", flush=True)
                    data = b""

                if not data:
                    try: s.close()
                    except Exception: pass
                    try: clients.remove(s)
                    except ValueError: pass
                    continue

                req = data.decode(errors="ignore").strip()
                resp = handle_cmd(req)
                payload = (json.dumps(resp) + "\n").encode()
                try: s.sendall(payload)
                except Exception as e: print(f"[kilo] send error: {e}", flush=True)
                for act in (lambda: s.shutdown(socket.SHUT_RDWR), s.close, lambda: clients.remove(s) if s in clients else None):
                    try: act()
                    except Exception: pass
    finally:
        try: server.close()
        except Exception: pass
        try: os.unlink(SOCK_PATH)
        except Exception: pass
        print("[kilo] stopped. goodbye.", flush=True)

if __name__ == "__main__":
    sys.exit(main())
