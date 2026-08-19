"""
state.py — tracks which (video_id, platform, language) combos are
pending / posted / failed. Plain JSON file, single source of truth,
so a crash mid-run never causes a duplicate or a silent skip.
"""

import json
import threading
from pathlib import Path
from datetime import datetime

STATE_PATH = Path(__file__).parent / "state.json"
_lock = threading.Lock()


def _load():
    if not STATE_PATH.exists():
        return {}
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def _save(data):
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(STATE_PATH)  # atomic write


def get_status(video_id, platform, lang):
    data = _load()
    return data.get(video_id, {}).get(platform, {}).get(lang, "pending")


def set_status(video_id, platform, lang, status, note=None):
    with _lock:
        data = _load()
        data.setdefault(video_id, {}).setdefault(platform, {})[lang] = {
            "status": status,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "note": note,
        }
        _save(data)


def list_pending(video_id, platforms, langs):
    pending = []
    for p in platforms:
        for l in langs:
            s = get_status(video_id, p, l)
            s = s["status"] if isinstance(s, dict) else s
            if s not in ("posted",):
                pending.append((p, l))
    return pending
