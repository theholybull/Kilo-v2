#!/usr/bin/env python3
import os, sys, time, json, queue, urllib.parse, urllib.request
import numpy as np
import sounddevice as sd
import webrtcvad
from vosk import Model, KaldiRecognizer

def getenv(k, default=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else default

CFG = {
    "device": getenv("EARS_INPUT_DEVICE"),
    "wake_phrases": [p.strip() for p in (getenv("EARS_WAKE_PHRASES","hey jarvis, hey kilo, computer")).split(",") if p.strip()],
    "vosk_model": getenv("EARS_VOSK_MODEL","/opt/kilo/models/vosk-small-en-us"),
    "chat_url": getenv("EARS_CHAT_URL","http://127.0.0.1:7863/ask"),
    "max_speech": float(getenv("EARS_MAX_SPEECH_SEC","8")),
    "hang_sil": float(getenv("EARS_SILENCE_HANG_SEC","0.9")),
    "min_conf": float(getenv("EARS_MIN_CONF","0.30")),
}

RATE = 16000
CH = 1
BLOCK = 1600   # 100 ms
VAD_FRAME = 480  # 30 ms @16k

def http_ask(text: str):
    q = urllib.parse.urlencode({"text": text})
    with urllib.request.urlopen(f"{CFG['chat_url']}?{q}", timeout=5) as resp:
        resp.read()

def set_eye(eyes="focus"):
    try:
        state_path = "/opt/kilo/personality/state.json"
        st = {}
        if os.path.exists(state_path):
            with open(state_path,"r",encoding="utf-8") as f: st = json.load(f)
        st["eyes_state"]=eyes; st["updated_ts"]=int(time.time())
        tmp = state_path+".tmp"
        with open(tmp,"w",encoding="utf-8") as f: json.dump(st,f,indent=2)
        os.replace(tmp,state_path)
    except Exception:
        pass

def make_kw_rec(model: Model, phrases):
    import json as _json
    grammar = _json.dumps(phrases)
    rec = KaldiRecognizer(model, RATE)
    rec.SetGrammar(grammar)
    return rec

def make_full_rec(model: Model):
    rec = KaldiRecognizer(model, RATE)
    rec.SetWords(True)
    return rec

def run_stream(dev_choice):
    """Try to run with a specific device (index/name/None). Returns when stopped."""
    model = Model(CFG["vosk_model"])
    rec_kw = make_kw_rec(model, CFG["wake_phrases"])
    rec_full = make_full_rec(model)
    vad = webrtcvad.Vad(2)

    audio_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=50)
    hot = False
    speech_buf = bytearray()
    last_voice_ts = 0.0
    start_ts = 0.0

    def cb(indata, frames, time_info, status):
        if status: print("[ears] audio status:", status, file=sys.stderr)
        data = (indata[:,0] if indata.ndim>1 else indata).astype(np.float32)
        data_i16 = np.clip(data * 32767.0, -32768, 32767).astype(np.int16)
        try: audio_q.put_nowait(data_i16.copy())
        except queue.Full: pass

    sd_kwargs = dict(samplerate=RATE, channels=CH, dtype="float32", blocksize=BLOCK, callback=cb)
    if dev_choice is not None:
        sd_kwargs["device"] = dev_choice

    print(f"[ears] starting; device: {dev_choice if dev_choice is not None else 'default'} wake: {CFG['wake_phrases']}")
    set_eye("idle")
    with sd.InputStream(**sd_kwargs):
        while True:
            try:
                chunk = audio_q.get(timeout=1.0)
            except queue.Empty:
                continue

            byte_chunk = chunk.tobytes()
            # VAD (updates last_voice_ts)
            for i in range(0, len(byte_chunk), VAD_FRAME*2):
                frame = byte_chunk[i:i+VAD_FRAME*2]
                if len(frame) < VAD_FRAME*2: break
                if webrtcvad.Vad(2).is_speech(frame, RATE):
                    last_voice_ts = time.time()

            if not hot:
                if rec_kw.AcceptWaveform(byte_chunk):
                    import json as _json
                    res = _json.loads(rec_kw.Result())
                    utt = (res.get("text") or "").strip()
                    if utt:
                        print(f"[ears] wake: '{utt}'")
                        set_eye("focus")
                        hot = True
                        speech_buf.clear()
                        start_ts = time.time()
                        last_voice_ts = time.time()
            else:
                speech_buf.extend(byte_chunk)
                now = time.time()
                if (now - last_voice_ts) >= CFG["hang_sil"] or (now - start_ts) >= CFG["max_speech"]:
                    import json as _json
                    rec_full.AcceptWaveform(bytes(speech_buf))
                    res = _json.loads(rec_full.Result())
                    text = (res.get("text") or "").strip()
                    conf = float(res.get("confidence", 0.0) or 0.0)
                    if text and conf >= CFG["min_conf"]:
                        print(f"[ears] heard: '{text}' conf~{conf:.2f}")
                        set_eye("speak")
                        try: http_ask(text)
                        except Exception as e:
                            print("[ears] ask error:", e, file=sys.stderr)
                    else:
                        print(f"[ears] no usable speech (len={len(speech_buf)} conf~{conf:.2f})")
                        set_eye("idle")
                    hot = False
                    speech_buf.clear()
                    last_voice_ts = 0.0
                    start_ts = 0.0
                    rec_kw = make_kw_rec(model, CFG["wake_phrases"])

def main():
    # Try configured device; if it fails, try None (default); then 'pulse'
    choices = []
    raw = CFG["device"]
    if raw is not None and raw != "":
        try:
            choices.append(int(raw) if raw.isdigit() else raw)
        except Exception:
            choices.append(raw)
    choices += [None, "pulse"]

    for choice in choices:
        try:
            run_stream(choice)
            return
        except Exception as e:
            print(f"[ears] device '{choice}' failed: {e}", file=sys.stderr)
            time.sleep(0.3)
    print("[ears] ERROR: no usable input device", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    if not os.path.isdir(CFG["vosk_model"]):
        print("[ears] ERROR: Vosk model not found at", CFG["vosk_model"], file=sys.stderr)
        sys.exit(2)
    main()
