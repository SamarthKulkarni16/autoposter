"""
main.py — watches outbox/, builds a job queue of unposted (video, platform,
lang) combos, and works through them at a randomized human-ish pace inside
active hours. Run this with the target browser window already open, logged
in, tabs pinned in the order config.TAB_MAP expects.

    python3 main.py            # run continuously
    python3 main.py --once     # process current queue once and exit
"""

import sys
import json
import random
import time
import logging
import importlib

import config
import state
import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("autoposter.log"), logging.StreamHandler()],
)
log = logging.getLogger("autoposter")

_platform_modules = {}


def _load_platform(name):
    if name not in _platform_modules:
        _platform_modules[name] = importlib.import_module(f"platforms.{name}")
    return _platform_modules[name]


def scan_outbox():
    """Yields (video_id, meta) for every folder in outbox/ with a meta.json."""
    if not config.OUTBOX_DIR.exists():
        return
    for video_dir in sorted(config.OUTBOX_DIR.iterdir()):
        if not video_dir.is_dir():
            continue
        meta_path = video_dir / "meta.json"
        if not meta_path.exists():
            continue
        with open(meta_path) as f:
            meta = json.load(f)
        yield video_dir.name, video_dir, meta


def build_queue():
    jobs = []
    for video_id, video_dir, meta in scan_outbox():
        platforms = [p for p in meta.get("platforms", config.ENABLED_PLATFORMS)
                     if p in config.ENABLED_PLATFORMS]
        for platform in platforms:
            for lang in config.LANGS:
                account = config.ACCOUNTS.get(platform, {}).get(lang)
                if account is None:
                    continue  # no account configured for this platform/lang yet
                video_file = video_dir / f"{lang}.mp4"
                if not video_file.exists():
                    continue
                status = state.get_status(video_id, platform, lang)
                status = status["status"] if isinstance(status, dict) else status
                if status == "posted":
                    continue
                jobs.append({
                    "video_id": video_id,
                    "platform": platform,
                    "lang": lang,
                    "video_path": str(video_file),
                    "title": meta.get("title", {}).get(lang, video_id),
                    "caption": meta.get("caption", {}).get(lang, ""),
                    "tags": meta.get("tags", {}).get(lang, ""),
                    # Only set for platforms like pinterest where several langs
                    # share one logged-in profile and differ by board instead;
                    # None for youtube and anything else without a "board" key.
                    "board": account.get("board"),
                    # Only set for platforms like facebook where several langs
                    # share one logged-in profile but each posts as a
                    # different Page (selected by navigating to that Page's
                    # own "url" above, not by an in-page dropdown) -- this is
                    # just the display name, for logging/sanity-checks.
                    "page": account.get("page"),
                    # Only set for instagram (each lang has its own separate
                    # account/login already, so this isn't needed to select
                    # anything at post time) -- for logging/sanity-checks.
                    "handle": account.get("handle"),
                })
    return jobs


def run_job(job):
    video_id, platform, lang = job["video_id"], job["platform"], job["lang"]
    log.info(f"Posting {video_id} -> {platform}/{lang}")
    state.set_status(video_id, platform, lang, "in_progress")
    page = None
    try:
        page = engine.open_account(platform, lang)
        mod = _load_platform(platform)
        mod.post(job, page)
        state.set_status(video_id, platform, lang, "posted")
        log.info(f"OK {video_id} -> {platform}/{lang}")
        return True
    except Exception as e:
        state.set_status(video_id, platform, lang, "failed", note=str(e))
        log.error(f"FAILED {video_id} -> {platform}/{lang}: {e}")
        return False
    finally:
        if page is not None:
            engine.close_account(page)


def process_queue_once():
    jobs = build_queue()
    log.info(f"{len(jobs)} pending job(s)")
    for job in jobs:
        run_job(job)
        gap = random.uniform(*config.MIN_GAP_BETWEEN_POSTS)
        log.info(f"Sleeping {gap:.0f}s before next post")
        time.sleep(gap)


def main_loop():
    log.info("autoposter started, watching outbox/")
    while True:
        try:
            process_queue_once()
        except Exception as e:
            log.error(f"Loop error: {e}")
        time.sleep(config.POLL_INTERVAL_SEC)


if __name__ == "__main__":
    if "--once" in sys.argv:
        process_queue_once()
    else:
        main_loop()
