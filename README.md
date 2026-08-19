# autoposter — GUI-level social poster

Drives real browser tabs via mouse/keyboard on your Ubuntu desktop, at human
speed, so posting doesn't depend on any platform API.

## 1. One-time setup on the Ubuntu desktop

**Must be X11, not Wayland.** GNOME on Ubuntu 22.04+ can default to Wayland,
and pyautogui/xdotool can't read screen pixels or inject input reliably
under Wayland. Check:

```bash
echo $XDG_SESSION_TYPE
```

If it says `wayland`, log out, and on the login screen click the gear icon
next to the session name and pick "Ubuntu on Xorg" (or `GNOME on Xorg`)
before logging back in.

Install system deps:

```bash
sudo apt update
sudo apt install -y tesseract-ocr python3-pip python3-tk python3-dev scrot xdotool firefox
```

Install Python deps:

```bash
cd autoposter
pip3 install -r requirements.txt
```

## 2. Account setup (manual, one time per account)

No tabs stay open. Each account (e.g. YouTube Hindi) gets its own Chrome
profile folder that remembers its login. Log in once per account:

```bash
python3 setup_profile.py youtube en
python3 setup_profile.py youtube hi
python3 setup_profile.py youtube ar
python3 setup_profile.py youtube pt
python3 setup_profile.py youtube es
```

Each command opens a fresh, blank-login Chrome window. Log in fully
(including any OTP/2FA), then press Enter in the terminal. The login is now
saved in `profiles/<account>/` permanently — the script reuses it forever
until the platform logs it out on its own.

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

Every failed `find()` saves a screenshot to `failures/<label>_<timestamp>.png`
showing exactly what the screen looked like when it couldn't find the
button. 95% of the time this means YouTube changed a label's wording —
open `platforms/youtube.py` and fix the string, no other code changes needed.

## 6. Adding a platform (Instagram / Facebook / TikTok / X)

1. Add its accounts to `config.ACCOUNTS` (profile name + start URL per lang)
   and add the platform name to `config.ENABLED_PLATFORMS`.
2. Run `setup_profile.py <platform> <lang>` once per account to save its login.
3. Create `platforms/<name>.py` with a `post(ctx)` function, same shape as
   `platforms/youtube.py`, using only `engine.click_text`, `engine.click_template`,
   `engine.type_text`, `engine.wait_for_text`. `main.py` handles opening/closing
   the right profile for you — the recipe just does the on-page steps.
4. Test with `python3 main.py --once` on one video before trusting it to
   the scheduled loop.

I built YouTube first since it has the most stable, fully-text-labeled
upload flow — best one to validate the approach on before we wire up the
other four (Instagram/TikTok in particular use more icon-only buttons,
which is where template capture via `capture_template.py` will matter).
