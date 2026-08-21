"""
debug/test_upload_step1.py — non-destructive dry run of the YouTube upload
flow, stopping at the 'Details' screen (video picked, title/desc typed,
NO Next/Publish clicks). Screenshots every step to debug/shots/ so the run
can be reviewed without needing to watch it live over RDP.

Run from the repo root on the VM (needs the real DISPLAY/DBUS env of the
live desktop session, same as any other GUI automation here):
    python3 debug/test_upload_step1.py
"""
import sys
import json
import cv2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import engine
import config
import vision

SHOT_DIR = Path(__file__).parent / "shots"
SHOT_DIR.mkdir(exist_ok=True)


def shot(label):
    frame = vision._screenshot()
    path = SHOT_DIR / f"{label}.png"
    cv2.imwrite(str(path), frame)
    print(f"[shot] saved {path}")


def find_test_video():
    """Reuses the same outbox/<id>/{lang}.mp4 + meta.json layout main.py expects."""
    if not config.OUTBOX_DIR.exists():
        raise SystemExit(f"OUTBOX_DIR does not exist: {config.OUTBOX_DIR}")
    for video_dir in sorted(config.OUTBOX_DIR.iterdir()):
        if not video_dir.is_dir():
            continue
        meta_path = video_dir / "meta.json"
        candidate = video_dir / "en.mp4"
        if candidate.exists():
            meta = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
            return candidate, meta
    raise SystemExit(f"No <id>/en.mp4 found anywhere under {config.OUTBOX_DIR}. "
                      f"Put a real test video there first (e.g. outbox/test1/en.mp4 "
                      f"+ outbox/test1/meta.json).")


def main():
    video_path, meta = find_test_video()
    print(f"[info] Using test video: {video_path}")

    title = meta.get("title", {}).get("en", "Autoposter test upload - DO NOT PUBLISH")
    caption = meta.get("caption", {}).get("en", "Test upload, will not be published.")

    proc = engine.open_account("youtube", "en")
    shot("01_studio_loaded")

    try:
        engine.click_text("Create", region=engine.top_nav_region())
        shot("02_after_create_click")

        engine.click_text("Upload videos")
        shot("03_after_upload_videos_click")

        engine.open_file_via_dialog(video_path)
        shot("04_after_file_dialog")

        engine.wait_for_text("Details", timeout=90)
        shot("05_details_screen_reached")

        engine.select_all_and_type(title)
        shot("06_title_typed")

        print("[SUCCESS] Reached Details screen with title set. Stopping here on purpose.")
        print("[SUCCESS] No Next/Publish was clicked. Studio autosaves this as an unlisted draft.")

    except Exception as e:
        shot("ERROR_final_state")
        print(f"[FAIL] {type(e).__name__}: {e}")
        raise
    finally:
        engine.close_account(proc)


if __name__ == "__main__":
    main()
