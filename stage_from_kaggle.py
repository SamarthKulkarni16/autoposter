"""
stage_from_kaggle.py — the bridge between the Kaggle editing pipeline and the
autoposter.

PRODUCER (Kaggle, via kaggle-debug/controller.py)
    notebookccca6d2dda produces, per run:
        output/clips/clip_XX_<lang>.mp4               (per clip × language)
        output/upload_manifest.json                    (clip_index, language,
                                                       hook, duration,
                                                       scheduled_date, ...)
    controller.py pulls those into
        latest_output/<kernel_slug>/short_videos/     (or long_videos/)
        latest_output/<kernel_slug>/upload_manifest.json
      (the manifest is now preserved by controller.pull_and_organize_videos)

CONSUMER (autoposter)
    main.py watches outbox/<video_id>/ and posts files it finds there:
        outbox/<video_id>/meta.json
        outbox/<video_id>/<lang>.mp4                  (one per autoposter LANGS)
    meta.json shape (see build_queue in main.py):
        { "platforms": [...],                          # from ENABLED_PLATFORMS
          "title":  {lang: str},  "caption": {lang: str},  "tags": {lang: str} }

THE BRIDGE
    Reads the latest complete Kaggle run's upload_manifest.json, groups its
    entries by clip_index, and materialises each clip into autoposter's outbox
    as outbox/<clip_id>/{hi,ar,pt,es}.mp4 + meta.json — exactly the shape
    main.py expects. Each clip folder = one short video with per-language
    renditions, per the autoposter model.

    - English is intentionally skipped: the autoposter config.LANGS is
      deliberately non-English (hi/ar/pt/es).
    - Only short clips are staged (the autoposter posts reels/shorts).
      Longform videos have no autoposter path yet and are left untouched.
    - Files are COPIED, never moved: latest_output/ stays as the permanent
      Kaggle backup.
    - Idempotent: clips whose (clip_id, platform, lang) combos are already
      'posted' in state.json are skipped; existing folders are reused.

USAGE
    python3 stage_from_kaggle.py [--run-dir DIR] [--dry-run]
        --run-dir   override the Kaggle run dir to read from (default:
                    auto-detect the newest run under latest_output/<kernel>).
        --dry-run   print what would be staged without copying anything.
"""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import config
import state

# Where controller.py keeps pulled Kaggle output. Importable as a constant so
# the bridge can be invoked from anywhere; users of controller.py can also pass
# --run-dir explicitly with a custom path.
DEFAULT_KAGGLE_PROJECT = Path("/home/ubuntu/kaggle-debug")
DEFAULT_OUTPUT_DIR = DEFAULT_KAGGLE_PROJECT / "latest_output"
KERNEL_SLUG = "notebookccca6d2dda"

# Languages the autoposter posts. English is deliberately excluded.
AUTOPOSTER_LANGS = list(config.LANGS)


def find_run_dir(explicit=None):
    """Return the newest run dir that contains an upload_manifest.json."""
    if explicit:
        d = Path(explicit)
        if d.is_file():
            d = d.parent
        return d if (d / "upload_manifest.json").exists() else None

    base = DEFAULT_OUTPUT_DIR / KERNEL_SLUG
    candidates = [base]
    # Also scan sibling kernel dirs under latest_output/, newest mtime first.
    if DEFAULT_OUTPUT_DIR.exists():
        candidates += [
            p for p in sorted(DEFAULT_OUTPUT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
            if p.is_dir() and p != base
        ]
    for d in candidates:
        if (d / "upload_manifest.json").exists():
            return d
    return None


def clip_video_path(run_dir, filename):
    """Locate a clip's mp4 under a run dir: it may live in short_videos/ (the
    controller's flat output) or in clips/ (the notebook's own output dir)."""
    p = run_dir / "short_videos" / filename
    if p.exists():
        return p
    p = run_dir / "clips" / filename
    if p.exists():
        return p
    # Some pulls name clips differently (e.g. de-duplicated _1 suffix). Fall
    # back to a fuzzy search by exact language token in short_videos/clips.
    for folder in ("short_videos", "clips"):
        d = run_dir / folder
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.name.endswith(".mp4") and filename.startswith(f.name.split("_")[0]):
                if f.name == filename:
                    return f
    return None


def derive_meta(clip_id, lang, hook):
    """Build the autoposter meta.json fields for one (clip, lang)."""
    title = hook.strip() if hook else f"Clip {clip_id} ({lang.upper()})"
    return {
        "title": title,
        "caption": hook.strip() if hook else "",
        "tags": "",
    }


def stage_clip(run_dir, clip_id, by_lang, dry_run):
    """Copy one clip's per-language videos into outbox/<clip_id>/ + meta.json."""
    outbox_dir = Path(config.OUTBOX_DIR) / str(clip_id)
    meta = {
        "platforms": list(config.ENABLED_PLATFORMS),
        "title": {},
        "caption": {},
        "tags": {},
    }
    files_copied = []

    for lang in AUTOPOSTER_LANGS:
        if lang not in by_lang:
            continue
        entry = by_lang[lang]
        filename = entry.get("filename") or Path(entry.get("path", "")).name
        src = clip_video_path(run_dir, filename)
        if not src:
            print(f"  ! missing file for clip {clip_id} {lang}: {filename} — skipping lang")
            continue
        dst = outbox_dir / f"{lang}.mp4"
        # Always refresh the copy (idempotent via state.json; harmless if same)
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        files_copied.append(f"{lang}.mp4")
        m = derive_meta(clip_id, lang, entry.get("hook", ""))
        meta["title"][lang] = m["title"]
        meta["caption"][lang] = m["caption"]
        meta["tags"][lang] = m["tags"]

    if not files_copied:
        return False

    if not dry_run:
        dst = outbox_dir / "meta.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    return True


def main():
    ap = argparse.ArgumentParser(description="Bridge Kaggle output -> autoposter outbox")
    ap.add_argument("--run-dir", help="Kaggle run dir containing upload_manifest.json")
    ap.add_argument("--dry-run", action="store_true", help="show what would be staged")
    args = ap.parse_args()

    run_dir = find_run_dir(args.run_dir)
    if not run_dir:
        print("No upload_manifest.json found under", args.run_dir or DEFAULT_OUTPUT_DIR / KERNEL_SLUG)
        print("(The last Kaggle run must have produced clips for there to be anything to stage.)")
        sys.exit(1)

    with open(run_dir / "upload_manifest.json") as f:
        manifest = json.load(f)

    # Group manifest entries by clip_index.
    by_clip = {}
    for e in manifest:
        by_clip.setdefault(e["clip_index"], {})[e["language"]] = e

    staged = 0
    print(f"Run dir: {run_dir}  ({'DRY-RUN' if args.dry_run else 'staging'})")
    print(f"Found {len(by_clip)} clip(s) in manifest.")
    for clip_id in sorted(by_clip.keys()):
        ok = stage_clip(run_dir, clip_id, by_clip[clip_id], args.dry_run)
        if ok:
            langs = [l for l in AUTOPOSTER_LANGS if l in by_clip[clip_id]]
            print(f"  staged clip {clip_id}: {','.join(langs)} -> outbox/{clip_id}/")
            staged += 1
        else:
            print(f"  skipped clip {clip_id}: no files found on disk")

    print(f"\nDone. {staged} clip(s) ready for the autoposter.")
    if staged:
        print("Run `python3 main.py --once` (or the watcher) to post them.")


if __name__ == "__main__":
    main()
