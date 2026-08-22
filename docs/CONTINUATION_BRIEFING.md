# Autoposter — YouTube Upload Debugging — Continuation Briefing

**Purpose of this document:** hand this to ANY AI agent that has (1) shell/HTTP
execution, (2) image/vision understanding, (3) file read/write, and (4) can run
in a loop without a human re-prompting every step. It should be able to
continue this exact debugging task with zero prior context, picking up from
the current state, without re-discovering anything below. Written so it is
self-contained — the agent should not need the original chat history.

If you are an AI reading this: **read this entire document before doing
anything.** Then jump to "CURRENT STATE — START HERE" near the bottom.

---

## 1. The goal

Get `platforms/youtube.py::post()` in the `autoposter` project reliably
uploading a video to YouTube Studio via OS-level GUI automation (OCR +
pyautogui), end-to-end, without human intervention. This is one platform of a
larger multi-platform (X, Facebook, Instagram, LinkedIn, Pinterest) automated
posting pipeline — YouTube is the current focus because it's the most complex
UI to automate reliably.

## 2. Why GUI automation instead of an API or browser-automation framework

Already decided and settled — do not revisit this without new evidence:

- **YouTube Data API v3 upload** was not chosen for this pipeline (channels
  are ordinary creator accounts, not verified for unrestricted API quota, and
  the existing infra is GUI-automation-first across all platforms for
  consistency). Assume this constraint holds unless the human says otherwise.
- **Playwright/Selenium/CDP-based browser automation was tried and
  abandoned.** Root cause: any framework that drives a browser via Chrome
  DevTools Protocol (CDP) — even with every known stealth flag disabled — gets
  detected and blocked by Google/X login systems. This is a structural
  limitation, not a bug. Confirmed directly: a manually-logged-in Playwright
  Chromium profile got bounced back to the login page the instant Playwright's
  CDP channel touched it, even though the exact same profile folder had just
  logged in successfully moments earlier via a normal, non-automated launch.
- **OS-level input (pyautogui mouse/keyboard events) is the working
  approach**, because it's indistinguishable from a human — it's literally
  the same OS input events real usage produces. This is proven: login always
  worked fine with this approach; all bugs so far have been UI-targeting bugs
  (wrong click, timing, OCR false-positives), never detection/blocking.

## 3. Environment

- **VM:** Oracle Cloud `samarth-ubuntu-desktop`, IP `140.238.229.141`, user
  `ubuntu`, ARM64 (Ampere `VM.Standard.A1.Flex`), Ubuntu 22.04 GNOME, accessed
  by the human via Windows RDP → xrdp.
- **Repos (both on GitHub, owner `SamarthKulkarni16`):**
  - `autoposter` — the actual automation code (this is what you'll be editing)
  - `oracle-vm-setup` — infra/relay repo, holds the GitHub Actions workflows
    used to remotely control the VM (see Section 4)
- Google Chrome does not exist for Linux ARM64 at all (Google doesn't ship
  it). Chromium via snap is broken under this VM's xrdp session (cgroup
  error, never opens a window). The only two working browsers on this VM are:
  Firefox (installed from Mozilla's own APT repo, NOT the snap/apt-stub —
  see the install command in `oracle-vm-remote-control-summary` history if
  it's ever missing), and Playwright's bundled Chromium binary (works for
  manual launches, not for CDP-driven automation, see Section 2).
- YouTube account profile used for automation: Firefox profile at
  `/home/ubuntu/.config/mozilla/firefox/g7dhshsu.default-release`
  (`config.ACCOUNTS["youtube"]["en"]`), already logged in.

## 4. THE CRITICAL METHOD: you cannot SSH into the VM directly

Your own tool sandbox almost certainly only allows a fixed domain allowlist
(github.com, api.github.com, pypi, npm, etc.) — not arbitrary IPs. So you
cannot SSH into `140.238.229.141` directly, and you cannot fetch raw GitHub
Actions log output either (it's on a blob-storage domain outside the
allowlist). **You must control the VM indirectly via GitHub Actions as a
relay.** Full recipe:

### 4a. Setup already done (don't redo it)
- `VM_SSH_PRIVATE_KEY` is stored as a GitHub Actions secret in the
  `oracle-vm-setup` repo.
- The VM's `authorized_keys` already trusts that key.
- Several reusable workflows already exist in
  `oracle-vm-setup/.github/workflows/`, including `deploy-autoposter.yml`
  (fresh `git clone` of `autoposter` onto the VM) and
  `test-youtube-upload.yml` (runs the non-destructive test script and ships
  screenshots back — see Section 6). **Check what's already there with a
  `git clone` + `ls .github/workflows/` before writing a new workflow file —
  don't duplicate one that already exists.**

### 4b. The loop for anything new
1. `git clone https://<PAT>@github.com/SamarthKulkarni16/<repo>.git`
2. Write/edit a `.github/workflows/<name>.yml` with `on: workflow_dispatch:`
   (accept a `vm_ip` input, default `140.238.229.141`), `permissions:
   contents: write`, a step that writes the SSH key from the secret, a step
   that SSHs in and runs commands, and a step that commits output back to
   `logs/<name>-latest.txt` in the repo.
3. **Before every push, validate:** `python3 -c "import yaml;
   yaml.safe_load(open(path))"`. The #1 recurring failure: **nested heredocs
   break GitHub's YAML parser.** If the outer `ssh ... << 'REMOTE_SCRIPT'`
   heredoc contains a second, inner heredoc, GitHub silently fails to parse
   the file (422 error, no useful message, `workflow_dispatch` stops being
   recognized). **Never nest heredocs.** Use `printf '%s\n' 'line1' 'line2' >
   file` instead of a second heredoc when you need to write a file remotely.
4. Push, wait ~10-15s if the workflow file is brand new (GitHub needs to
   index it), then trigger:
   ```
   POST https://api.github.com/repos/SamarthKulkarni16/<repo>/actions/workflows/<name>.yml/dispatches
   Authorization: token <PAT>
   Body: {"ref":"main","inputs":{"vm_ip":"140.238.229.141"}}
   ```
   `204` = queued successfully.
5. Poll (every 10-15s, don't busy-loop):
   ```
   GET https://api.github.com/repos/SamarthKulkarni16/<repo>/actions/workflows/<name>.yml/runs?per_page=1
   ```
   Check `status` and `conclusion`.
6. `git pull` the repo again, read `logs/<name>-latest.txt`.

### 4c. Getting screenshots back (essential for this task)
Text logs are not enough for GUI debugging — you must SEE the screen.
Screenshots travel through the text-log channel as base64:

**Remote side (inside the SSH heredoc), after taking screenshots:**
```bash
tar -czf /tmp/shots.tar.gz -C debug/shots .
echo "===SHOTS_BASE64_START==="
base64 -w0 /tmp/shots.tar.gz
echo ""
echo "===SHOTS_BASE64_END==="
```

**Your side, after pulling the log:**
```python
import re, base64
text = open("run_output.txt").read()
m = re.search(r"===SHOTS_BASE64_START===\n(.*?)\n===SHOTS_BASE64_END===", text, re.S)
open("/tmp/shots.tar.gz", "wb").write(base64.b64decode(m.group(1)))
# tar -xzf into logs/shots/, commit the real .png files, git pull, then
# actually VIEW them with your image tool before deciding what's wrong.
```
This is the single highest-leverage trick here. A GUI bug that's invisible in
a Python traceback is often obvious in one screenshot — e.g. "element not
found" can mean the page hadn't loaded yet, or that OCR matched something
else entirely. **Always look at the actual screenshots. Do not diagnose from
stack traces alone.**

### 4d. Getting a live GUI session (needed for anything that touches the screen)
The automation needs a live GNOME desktop session (the human connected over
RDP) to click/type into — there's nothing to interact with otherwise. Grab
the live session's real DISPLAY/DBUS from the current `gnome-shell` process
(works even if the human's RDP client shows a locked/black screen — locking
doesn't kill the session):
```bash
SHELL_PID=$(pgrep -u ubuntu -f gnome-shell | sort -n | tail -1)
REAL_DISPLAY=$(sudo cat /proc/$SHELL_PID/environ | tr '\0' '\n' | grep '^DISPLAY=' | cut -d= -f2-)
REAL_DBUS=$(sudo cat /proc/$SHELL_PID/environ | tr '\0' '\n' | grep '^DBUS_SESSION_BUS_ADDRESS=' | cut -d= -f2-)
# then: sudo -u ubuntu env DISPLAY="$REAL_DISPLAY" DBUS_SESSION_BUS_ADDRESS="$REAL_DBUS" <command>
```
If `pgrep` finds nothing, no one is connected over RDP — tell the human to
connect and wait for confirmation before running anything screen-touching.

If a run's first screenshot comes back **solid black**, the RDP session is
disconnected/locked/idle-timed-out, not a code bug — tell the human to check
their RDP connection. (This exact thing happened once already and was traced
to a GNOME idle-lock regression — see Section 5, item 6 — already fixed as of
this writing, but keep the black-screen diagnostic in mind regardless.)

## 5. Bug history — what's already been found and fixed (don't rediscover these)

In chronological order, each with root cause so you don't waste time
re-diagnosing:

1. **File-picker dialog focus bug.** A bare `Ctrl+L` keyboard event with no
   prior mouse click doesn't reliably grab focus on the GTK file-chooser
   dialog under this VM's xrdp/portal setup (`wmctrl`/`xdotool` can't see or
   activate the xdg-desktop-portal dialog at all). **Fix (in `engine.py`,
   `open_file_via_dialog`):** poll for the dialog via OCR-finding the
   "Recent" sidebar label (always present), click it first to force real
   focus, THEN send Ctrl+L. Also added a 5s/40s poll loop for slow dialog
   appearance. **Status: fixed, believed working** (not yet re-verified after
   later fixes, since the flow hasn't reached this step again yet).

2. **"Create" vs "Created" OCR mismatch.** Studio's analytics table has a
   "Created" column header that a fuzzy OCR match for "Create" could hit
   instead of the actual Create button. **Status: superseded by items 3-4
   below** (region-scoping evolved further).

3. **False-positive Create click on Firefox's own tab title.** A
   percentage-of-screen "top nav region" guess overlapped Firefox's tab bar,
   which reads "YouTube Creator Studio" — fuzzy-matched as "Create" (`min_ratio
   =0.72` in `vision.find_text`) while the real page was still loading
   underneath, so the click landed on browser chrome, not the in-page button.
   **Fix:** replaced the percentage guess with `engine.locate_text()` +
   `engine.band_region()` — wait for a real in-page anchor (the "Studio"
   logo) first, then scope the "Create" search to a tight band around that
   anchor's actual y-coordinate.

4. **The anchor search itself had the same bug, one level up.**
   `locate_text("Studio", ...)` was initially unscoped, so it ALSO matched
   the Firefox tab title (same string, "Studio" is a substring of "YouTube
   Creator Studio") before the real page rendered. **Fix:** added
   `engine.below_chrome_region()` — a fixed 150px exclusion zone from the top
   of the screen that comfortably clears the title bar + tab row + address
   bar stack on this VM, used to scope the anchor search itself.

5. **`gnome-screenshot` package missing.** `pyautogui.screenshot()` requires
   it on Linux (or `scrot`, but this pyautogui/Pillow version combo
   specifically demanded gnome-screenshot). Every screenshot call was
   crashing before this was installed. **Fix:** `sudo apt-get install -y
   gnome-screenshot` added to the relevant workflow(s). If you write a new
   workflow that takes screenshots, make sure this is installed too — check
   first, it may already be present from prior runs.

6. **GNOME idle-lock regression (infra, not code).** The human's RDP session
   started getting logged out after a period of inactivity, when previously
   it stayed connected indefinitely. Root cause: `org.gnome.desktop.session
   idle-delay` was `300` (5 min), `org.gnome.desktop.screensaver
   lock-enabled` / `idle-activation-enabled` were both `true`, and
   `org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type` was
   `'suspend'` — likely toggled by an unattended system update at some
   point. **Fix (already applied via `oracle-vm-setup/.github/workflows/
   fix-idle-logout.yml`):** set `idle-delay=0`, `lock-enabled=false`,
   `idle-activation-enabled=false`, `sleep-inactive-ac-type='nothing'`. Also
   checked `/etc/xrdp/xrdp.ini` for `MaxIdleTime`/`MaxDisconnectionTime` —
   neither key was present (xrdp itself was not the cause; defaults apply
   and are unlimited). xrdp service was restarted to be safe, which
   disconnects any active RDP session — the human had to reconnect once.
   **Status: fixed and verified via gsettings readback in the workflow log.**

7. **Leftover Firefox process across test runs causing duplicate tabs.**
   `close_account()` calls `proc.terminate()` on the `subprocess.Popen`
   handle, but Firefox commonly forks into a detached real process while the
   launcher exits — so `terminate()` may only kill the launcher, leaving the
   actual browser window running. This caused two tabs to accumulate across
   consecutive test runs, and once caused Firefox to show an
   `about:sessionrestore` recovery tab after a workflow-side `pkill` killed
   it uncleanly. **Fix applied so far:** `test-youtube-upload.yml` now does a
   *targeted* `pkill -u ubuntu -f "g7dhshsu.default-release"` (matches only
   this specific profile path, not all Firefox — important, don't disrupt
   anything else the human has open) before each run, then deletes
   `sessionstore.jsonlz4` and `sessionstore-backups/` for that profile so the
   next launch has nothing to "recover" and won't spawn the extra tab.
   **`close_account()` itself in `engine.py` has NOT yet been fixed** to
   properly kill the real forked process (e.g. via `proc.pid` process-group
   kill or `pkill -f <profile>` instead of `proc.terminate()`) — this is a
   good next improvement if duplicate tabs recur.

## 6. Current test harness (non-destructive, safe to re-run freely)

**Gotcha to know before you start debugging interactively:** several
functions here have deliberately long timeouts for production robustness —
`locate_text(timeout=90)`, `click_text`'s internal retry window (~24s),
`open_file_via_dialog`'s 40s dialog-appearance poll. When running
interactively (e.g. via an agent like Cline sitting in a terminal), these
can look exactly like a hang — there's no output for tens of seconds while
it's legitimately waiting/retrying before reporting failure. **This already
caused real confusion in a prior session** (a human mistook a normal
90s-timeout wait for a frozen AI agent). If you're debugging interactively:
add a fast/debug mode that cuts these timeouts way down (e.g. 90s → 10s) and
prints a visible line on every retry/wait ("still waiting, Ns elapsed...")
so it's obvious it's waiting on purpose, not stuck. Only use the full
production timeouts for a final verification run, not routine debugging.

`autoposter/debug/test_upload_step1.py` — runs the upload flow only through
the "Details" screen (video file picked, title typed), deliberately WITHOUT
clicking Next/Publish, so re-running it never actually publishes anything.
Screenshots after every step to `debug/shots/`. Uses a dummy 3-second test
video auto-generated via `ffmpeg` at `outbox/test1/en.mp4` if one doesn't
already exist (workflow creates it automatically).

`oracle-vm-setup/.github/workflows/test-youtube-upload.yml` runs this script
end-to-end via the relay method (Section 4), including: live-session check,
fresh `autoposter` clone, system deps (`gnome-screenshot`, `ffmpeg`),
dummy-video creation, targeted leftover-Firefox cleanup, running the script,
and packing+committing screenshots. **This is the workflow to re-trigger to
continue testing** — check it still exists and reflects the latest fixes
before assuming it's ready to run as-is (an agent before you may have edited
it further).

**IMPORTANT SAFETY RULE for any test script you write or modify:** never let
it click Next/Publish/Send/Delete or otherwise complete an irreversible
action. Stop one step before the point of no return, always. If you need to
test further into the flow, extend the stopping point deliberately and
mention it explicitly to the human before running — don't let it happen as a
side effect of chasing a bug.

## 7. Credentials (SENSITIVE — see note below)

**Do not commit a real PAT into this repo or any file — GitHub's push
protection will reject the push anyway (this happened once already), and
more importantly it's just bad practice.** Ask the human for a current
GitHub PAT (scopes: `repo`, `workflow`) at the start of your session. Any
PAT used in a prior session should be treated as due for rotation — don't
assume an old one still works, and don't reuse one you find lying around in
chat history or old logs. Keep whatever PAT you're given in memory/an
environment variable only, never in a committed file. Remind the human to
rotate it once your task is done or your session ends, whichever comes
first.

## 8. CURRENT STATE — START HERE

As of the end of the most recent session:

- The GNOME idle-lock regression (Section 5, item 6) is confirmed fixed —
  a subsequent run got real (non-black) screenshots successfully, so the RDP
  session stability issue is resolved.
- **Confirmed reproducible failure, same across two consecutive clean runs:**
  the Create button click (via `engine.locate_text("Studio", ...)` +
  `engine.band_region()` + `engine.click_text("Create", ...)`) executes
  without raising an error, the dashboard is fully loaded and visually
  correct in the screenshot taken right after
  (`02_after_create_click.png` shows a completely normal, unopened Create
  button — no dropdown, no visible change from before the click at all), and
  the subsequent `click_text("Upload videos")` then reliably times out after
  its full ~24s retry window (confirmed via the final failure screenshot
  also showing no dropdown ever appeared). **This means the dropdown menu is
  never opening at all** — not a flicker/timing race, an outright non-event.
- `vision.py` (`find_text`, coordinate math) and `human_actions.py` (`click`,
  `move_to`) were both read in full and look structurally correct — no
  obvious HiDPI/scaling bug, no obvious off-by-factor bug in the /2
  upscale-undo math. Nothing wrong was found by code review alone.
- **Diagnostic added but NOT YET RUN** (this is the immediate next step for
  whoever picks this up): `debug/test_upload_step1.py` now finds the OCR
  match location for "Create" and saves a screenshot
  (`debug/shots/01c_create_target_marked.png`) with a red circle drawn
  exactly at the computed click point, BEFORE actually clicking. This will
  give direct visual proof of whether the click coordinate is really on the
  button or subtly off it. **Trigger one more test run and look at that
  image first** — it should immediately narrow this down to either "click
  target is correct, investigate why the button isn't responding to the
  click event" or "click target is genuinely off, there's a coordinate math
  bug to find."
- Two secondary things noticed but not yet acted on:
  - `close_account()` still doesn't reliably kill the real forked Firefox
    process (see Section 5, item 7) — currently worked around at the
    workflow level (targeted `pkill` before each run), not fixed at the
    code level. Low priority unless duplicate tabs start interfering with
    OCR again.
  - No new evidence on this point, but worth keeping in mind: YouTube
    Studio's "Create" button may use a non-standard click handler (e.g. a
    JS framework that listens for `mousedown`+`mouseup` with specific timing,
    or ignores synthetic-feeling event sequences even from genuine OS-level
    input if the sequence is too fast/slow). If the marker diagnostic shows
    a correct click target and the button still doesn't respond, this is
    the next hypothesis to test — e.g. try an explicit double-attempt click,
    or a slightly longer pause between mouse-down and mouse-up.
- Once "Upload videos" reliably opens and gets clicked, the flow should
  reach `open_file_via_dialog()` (Section 5, item 1 — believed fixed but not
  yet re-verified end-to-end since later fixes were layered on top), then
  the "Details" screen. Getting a full green run of
  `debug/test_upload_step1.py` (reaching "Details" with title set, script
  prints `[SUCCESS]`) is the immediate goal.
- After that: the *real* `platforms/youtube.py::post()` still has an
  untested tail end (description field, "not made for kids" click, three
  "Next" clicks, visibility=Public, Publish, confirmation wait) that has
  never been exercised even once — Section 6's test script deliberately
  stops before it. That whole back half needs the same
  screenshot-per-step treatment before it can be trusted, ideally as a
  second debug script (`debug/test_upload_step2_full_publish.py` or similar)
  that a human explicitly confirms is safe to let complete a real publish
  before it's ever run.

---

*This document reflects real state as of the session that generated it
(around Aug 21, 2026). File contents and workflow existence should be
verified against the actual repos before being trusted at face value — they
may have changed if another agent worked on this since.*
