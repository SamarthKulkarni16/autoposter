"""
debug/test_upload_step1.py — non-destructive dry run of the YouTube upload
flow, stopping at the 'Details' screen (video picked, title typed, NO
Next/Publish clicks). Screenshots every step to debug/shots/ so the run can
be reviewed without needing to watch it live over RDP.

Run from the repo root on the VM:
    python3 debug/test_upload_step1.py
    python3 debug/test_upload_step1.py --fast   # shorter timeouts for iterating
"""
import sys
import json
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import engine
import config

SHOT_DIR = Path(__file__).parent / "shots"
SHOT_DIR.mkdir(exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Non-destructive YouTube upload test")
    parser.add_argument("--fast", action="store_true", help="Enable fast/debug mode with shorter timeouts")
    parser.add_argument("--lang", default=config.LANGS[0],
                         help=f"Which configured account/video language to test (default: {config.LANGS[0]!r})")
    return parser.parse_args()


def shot(page, label):
    path = SHOT_DIR / f"{label}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[shot] saved {path}")


def find_test_video(lang):
    """Reuses the same outbox/<id>/{lang}.mp4 + meta.json layout main.py expects."""
    if not config.OUTBOX_DIR.exists():
        raise SystemExit(f"OUTBOX_DIR does not exist: {config.OUTBOX_DIR}")
    for video_dir in sorted(config.OUTBOX_DIR.iterdir()):
        if not video_dir.is_dir():
            continue
        meta_path = video_dir / "meta.json"
        candidate = video_dir / f"{lang}.mp4"
        if candidate.exists():
            meta = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
            return candidate, meta
    raise SystemExit(f"No <id>/{lang}.mp4 found anywhere under {config.OUTBOX_DIR}. "
                      f"Put a real test video there first (e.g. outbox/test1/{lang}.mp4 "
                      f"+ outbox/test1/meta.json).")


def main():
    args = parse_args()
    if args.fast:
        print("[info] Fast/debug mode enabled")
        os.environ["DEBUG_FAST"] = "1"

    lang = args.lang
    if lang not in config.ACCOUNTS.get("youtube", {}):
        raise SystemExit(f"No youtube account configured for lang={lang!r}. "
                          f"Configured: {list(config.ACCOUNTS.get('youtube', {}).keys())}")

    video_path, meta = find_test_video(lang)
    print(f"[info] Using test video: {video_path}")

    title = meta.get("title", {}).get(lang, "Autoposter test upload - DO NOT PUBLISH")

    page = engine.open_account("youtube", lang)
    shot(page, "01_studio_loaded")

    try:
        # No more "is the real page ready or is this the browser tab title"
        # ambiguity — get_by_role only ever looks inside the page DOM, so
        # waiting for the button itself to be visible IS the readiness check.
        create_btn = engine.locate(page, role="button", name="Create", timeout=90000)
        shot(page, "01b_page_actually_ready")

        box = create_btn.bounding_box()
        print(f"[diag] 'Create' button bounding box: {box}")

        engine.click_role(page, "button", "Create", timeout=90000)
        shot(page, "02_after_create_click")

        import human_actions as human
        human.wait(0.5, 1)
        engine.click_text(page, "Upload videos")
        shot(page, "03_upload_dialog_opened")

        select_files_trigger = engine.locate(page, text="SELECT FILES", timeout=15000)
        engine.upload_file(page, select_files_trigger, video_path)
        shot(page, "04_after_file_upload")

        engine.wait_for_text(page, "Details", timeout=90000)
        shot(page, "05_details_screen_reached")

        # Let YouTube's own filename-based title autofill settle before we
        # clear+type over it (see engine.select_all_and_type / platforms/youtube.py
        # for why this matters with "<lang>.mp4" filenames).
        human.wait(1.5, 2.5)

        title_field = engine.locate(page, role="textbox", name="Add a title", timeout=8000)
        engine.select_all_and_type(page, title_field, title)
        shot(page, "06_title_typed")

        print("[SUCCESS] Reached Details screen with title set. Stopping here on purpose.")
        print("[SUCCESS] No Next/Publish was clicked. Studio autosaves this as an unlisted draft.")

    except Exception as e:
        shot(page, "ERROR_final_state")
        print(f"[FAIL] {type(e).__name__}: {e}")
        raise
    finally:
        engine.close_account(page)


if __name__ == "__main__":
    main()
