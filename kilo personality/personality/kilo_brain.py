#!/usr/bin/env python3
"""
kilo_brain.py — tiny persona adapter:
- Reads persona.json / quips.yaml when available
- Returns a short, Kilo-toned reply to a user utterance
- No external calls; uses simple rules & quips
"""
import os, json, re, random
from typing import Dict, Any

BASE = "/opt/kilo/personality"
PERSONA_JSON = os.path.join(BASE, "persona.json")
QUIPS_YAML   = os.path.join(BASE, "quips.yaml")

def _load_persona() -> Dict[str, Any]:
    try:
        with open(PERSONA_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _load_quips() -> Dict[str, Any]:
    try:
        import yaml  # PyYAML assumed present earlier
        with open(QUIPS_YAML, "r", encoding="utf-8") as f:
            q = yaml.safe_load(f) or {}
            return q if isinstance(q, dict) else {}
    except Exception:
        return {}

def _pick(lst, default=""):
    if isinstance(lst, (list, tuple)) and lst:
        return random.choice(lst)
    return default

def _snarkify(line: str) -> str:
    """Apply Kilo seasoning (Red Forman / Tim Allen / Fred Sanford, Dodge/Barney/Vespa rules)."""
    low = line.lower()
    out = line.strip()

    # Add light add-ons based on keywords
    if "vespa" in low:
        out += " Classy."
    if "dodge" in low:
        out += " Figures."
    if "barney" in low:
        out += " Spare me."
    # Shorten overly long responses
    if len(out) > 220:
        out = (out[:220] + "…").rsplit(" ",1)[0]
    return out

def reply(user_text: str) -> str:
    persona = _load_persona()
    quips = _load_quips()

    text = (user_text or "").strip()
    low = text.lower()

    # Fast rule intents
    if not text:
        return "Say that again, but with confidence."
    if any(w in low for w in ["hello", "hi", "hey"]):
        return _snarkify(_pick(quips.get("greetings"), "What’s up. Try not to bore me."))
    if "name" in low:
        return _snarkify("Kilo Truck. Chrome personality, steel backbone.")
    if any(w in low for w in ["vespa", "scooter"]):
        return _snarkify("Vespas? Now that’s taste. Classy.")
    if "dodge" in low:
        return _snarkify("A Dodge? Figures.")
    if "barney" in low:
        return _snarkify("Purple menace. Spare me.")
    if any(w in low for w in ["joke", "laugh"]):
        return _snarkify(_pick(quips.get("jokes"), "Why don’t Dodges tell jokes? They can’t handle the punchline."))
    if any(w in low for w in ["help", "what can you do", "commands"]):
        return _snarkify("Ask me for a demo, a scan, or directions. I do charm, too.")

    # If quips has small talk or fallback buckets, use them
    for key in ("small_talk","one_liners","sarcasm"):
        if key in quips:
            return _snarkify(_pick(quips[key], "Got it. Put me to work."))

    # Plain fallback
    return _snarkify("Copy that. What’s next?")
    
if __name__ == "__main__":
    import sys
    print(reply(" ".join(sys.argv[1:])))
