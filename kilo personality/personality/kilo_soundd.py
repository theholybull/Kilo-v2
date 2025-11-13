#!/usr/bin/env python3
"""
kilo_soundd.py — watches /opt/kilo/personality/state.json and plays sound cues.
- No external Python deps.
- Uses aplay if available, otherwise ffplay (ffmpeg).
- Avoids overlapping playback: stops the last sound before starting a new one.
"""
import json, os, time, subprocess, shutil, signal, sys

STATE = "/opt/kilo/personality/state.json"
SOUNDS = "/opt/kilo/personality/sounds/engine"

# Map logical cues -> filenames (adjust as needed)
CUES = {
    "rev_startup":  "rev_startup.wav",
    "rev_shutdown": "rev_shutdown.wav",
    "rev_happy":    "rev_happy_double.wav",
    "rev_warning":  "rev_single_low.wav",
    "rev_showoff":  "rev_triple_rise.wav",
    "idle_low":     "idle_low.wav",
}

PLAYER = shutil.which("aplay") or shutil.which("ffplay")
PLAYER_TYPE = "aplay" if shutil.which("aplay") else ("ffplay" if shutil.which("ffplay") else None)

def play(path):
    if not PLAYER_TYPE:
        print("[kilo-sound] No aplay/ffplay found; cannot play:", path, flush=True)
        return None
    if PLAYER_TYPE == "aplay":
        # aplay blocks; run in Popen so we can stop it
        return subprocess.Popen([PLAYER, "-q", path])
    else:
        # ffplay (ffmpeg) — quiet, no window, auto-exit
        return subprocess.Popen([PLAYER, "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def stop(proc):
    if not proc: return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except Exception:
            proc.kill()
    except Exception:
        pass

def load_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    last = None
    proc = None
    print("[kilo-sound] starting; player:", PLAYER or "none", flush=True)
    try:
        while True:
            s = load_state()
            cue = s.get("sound_cue")
            if cue != last and cue:
                fname = CUES.get(cue)
                if fname:
                    path = os.path.join(SOUNDS, fname)
                    if os.path.exists(path):
                        print(f"[kilo-sound] play {cue} -> {fname}", flush=True)
                        stop(proc)
                        proc = play(path)
                    else:
                        print(f"[kilo-sound] missing file for {cue}: {path}", flush=True)
                else:
                    # Unknown cue; ignore quietly
                    pass
                last = cue
            # If cue cleared (None), stop any current playback
            if cue in (None, "", "none"):
                stop(proc); proc = None
                last = cue
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        stop(proc)
        print("[kilo-sound] stopped", flush=True)

if __name__ == "__main__":
    sys.exit(main())
