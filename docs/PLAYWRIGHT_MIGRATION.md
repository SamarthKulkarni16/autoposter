# Migration: OCR/pyautogui -> Playwright (Aug 2026)

The upload automation used to work by screenshotting the whole desktop,
OCR-reading it with pytesseract, and clicking whatever pixel coordinates
matched a text string (`vision.py`, now removed). That's why so much of the
debugging history in `docs/archive-ocr-era/` is about the OS file-picker
dialog never getting window focus, the Firefox tab title "YouTube Creator
Studio" fuzzy-matching the in-page "Create"/"Studio" text and getting
clicked instead of the real button, and needing pixel-region hacks
(`below_chrome_region`, `band_region`) to work around both.

That whole category of bug is gone now, structurally, not patched around:

- **Element lookup is DOM-based**, not pixel-based. `engine.locate()` /
  `click_text()` / `click_role()` use Playwright's `get_by_text()` /
  `get_by_role()`, which only ever search the actual page content — the
  browser's own tab title and chrome are never part of that search space,
  so there's nothing for it to accidentally match.
- **Shadow DOM is handled automatically.** YouTube Studio is built from web
  components; Playwright's locators pierce shadow roots by default, no
  extra work needed.
- **File upload no longer touches an OS dialog at all.** `engine.upload_file()`
  uses Playwright's `expect_file_chooser()` + `set_files()`, which hands the
  path straight to the `<input type=file>` element. The old
  `open_file_via_dialog()` (Ctrl+L into a GTK dialog, polling for a
  "Recent" sidebar label to confirm it was even open) is gone.
- **Waiting is built in.** Every Playwright locator action already waits for
  the element to exist, be visible, be stable, and be interactable before
  acting — the manual poll-and-retry loops in the old `vision.find_text()`
  are no longer needed for that part (a light retry wrapper is kept in
  `engine.click_text`/`click_role` for genuine transient failures).
- **Logins persist the same way.** `open_account()` launches a Playwright
  *persistent context* pointed at the same profile directory format Firefox
  itself uses, so accounts logged in once via `setup_profile.py` stay logged
  in, same as before.

What's unchanged: `main.py`'s job queue / `outbox/` / `state.json` design,
the human-like mouse movement and typing cadence in `human_actions.py`
(rewritten on top of `page.mouse` instead of `pyautogui`, same bezier-curve
intent), and the one-recipe-per-platform shape in `platforms/*.py`.

Setup is simpler too: no more `tesseract-ocr`/`scrot`/`xdotool`/X11
requirement — see the updated `install.sh` and `README.md`.

The old task docs in `docs/archive-ocr-era/` are kept for history but
describe the pre-migration code; don't hand them to a new coding agent as
current instructions.
