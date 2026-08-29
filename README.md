# autoposter — browser-automation social poster

Drives real, logged-in browser profiles to post videos, at a human-ish
pace, so posting doesn't depend on any platform API. Element lookup goes
through Playwright's DOM locators (real text/role matching against the
actual page, shadow DOM included) rather than screen-pixel OCR — see
`docs/PLAYWRIGHT_MIGRATION.md` for why that changed and what it fixed.

## 1. One-time setup

No X11/Wayland requirement anymore — Playwright can drive a headed or
headless Chrome either way, it doesn't read screen pixels or inject OS-level
input.

```bash
cd autoposter
pip3 install -r requirements.txt
python3 -m playwright install --with-deps chrome
```

(`install.sh` does both of the above for you on a fresh VM.)

## 2. Account setup (manual, one time per account)

Each account (e.g. YouTube Hindi) gets its own persistent Chrome profile
directory that remembers its login. Log in once per account:

```bash
python3 setup_profile.py youtube en
python3 setup_profile.py youtube hi
python3 setup_profile.py youtube ar
python3 setup_profile.py youtube pt
python3 setup_profile.py youtube es
```

Each command opens a real, visible Chrome window. Log in fully (including
any OTP/2FA), then press Enter in the terminal. The login is now saved in
`profiles/<account>/` permanently — the script reuses it forever until the
platform logs it out on its own.

Currently wired: YouTube, all 5 languages (see `config.ACCOUNTS`).

## 3. Feed it videos

Drop files into `outbox/<video_id>/`:

```
outbox/
  my_video_001/
    en.mp4
    hi.mp4
    ar.mp4
    meta.json
```

`meta.json` — see `outbox/sample_video_001/meta.json` for the exact shape:
per-language `title`, `caption`, `tags`, plus a `platforms` list.

## 4. Run it

```bash
python3 main.py --once     # process whatever's queued, then exit (good for testing)
python3 main.py            # run forever, polling outbox/ every 2 min
```

Logs go to `autoposter.log`. State (what's posted where) lives in
`state.json` — safe to inspect/edit by hand if you need to force a retry
(set a lang/platform back to `"pending"`).

## 5. If a step fails

Every failed lookup/wait saves a full-page screenshot to
`failures/<label>_<timestamp>.png` showing exactly what the page looked
like when it couldn't find or confirm something. Most of the time this
means YouTube changed a label's wording — open `platforms/youtube.py` and
fix the string, no other code changes needed.

`debug/test_upload_step1.py` is a non-destructive dry run that walks
through video-pick + title-fill and stops before Next/Publish, saving a
screenshot at every step to `debug/shots/` — good for iterating on a broken
step without risking an accidental publish.

## 6. Adding a platform (Instagram / Facebook / TikTok / X)

1. Add its accounts to `config.ACCOUNTS` (profile name + start URL per lang)
   and add the platform name to `config.ENABLED_PLATFORMS`.
2. Run `setup_profile.py <platform> <lang>` once per account to save its login.
3. Create `platforms/<name>.py` with a `post(ctx, page)` function, same
   shape as `platforms/youtube.py`, using only `engine.click_text`,
   `engine.click_role`, `engine.type_text`, `engine.upload_file`,
   `engine.wait_for_text`. `main.py` handles opening/closing the right
   profile and handing you the `page` — the recipe just does the on-page
   steps.
4. Test with `python3 main.py --once` on one video before trusting it to
   the scheduled loop.

I built YouTube first since it has the most stable, fully-text-labeled
upload flow — best one to validate the approach on before wiring up the
other four.
