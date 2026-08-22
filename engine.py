"""
engine.py — primitives that platform recipes are built from.
Recipes (platforms/*.py) should only call these, never raw pyautogui,
so all timing/retry/failure-logging behavior stays consistent everywhere.
"""

import os
import time
import subprocess
import config
import vision
import human_actions as human


def _is_fast_mode():
    """Check if fast/debug mode is enabled via env var or CLI flag."""
    return os.environ.get("DEBUG_FAST", "").lower() in ("1", "true", "yes", "on")


def _fast_timeout(default_timeout, fast_timeout=None):
    """Return fast timeout if in fast mode, otherwise default."""
    if _is_fast_mode():
        return fast_timeout if fast_timeout is not None else min(default_timeout, 10)
    return default_timeout


def _fast_retries(default_retries, fast_retries=1):
    """Return fast retry count if in fast mode, otherwise default."""
    if _is_fast_mode():
        return fast_retries
    return default_retries


def _fast_poll(default_poll, fast_poll=None):
    """Return fast poll interval if in fast mode, otherwise default."""
    if _is_fast_mode():
        return fast_poll if fast_poll is not None else default_poll
    return default_poll


def _progress_wait(message, elapsed, interval=3):
    """Print progress message every `interval` seconds while waiting."""
    if _is_fast_mode() or elapsed % interval == 0:
        print(f"[wait] {message}, {elapsed:.0f}s elapsed...")


class StepFailed(Exception):
    pass


def open_account(platform, lang):
    """
    Opens a fresh Firefox window using the dedicated profile for this
    (platform, lang) account, already logged in, pointed at its start URL.
    Returns the subprocess handle — pass it to close_account() when done.
    -no-remote is required or Firefox just opens a tab in whatever instance
    is already running instead of using the requested profile.
    """
    account = config.ACCOUNTS[platform][lang]

    if "profile_path" in account:
        proc = subprocess.Popen([
            config.BROWSER_BIN,
            "-no-remote",
            "-profile", account["profile_path"],
            account["url"],
        ])
    else:
        profile_dir = config.PROFILES_DIR / account["profile"]
        if not profile_dir.exists():
            raise StepFailed(
                f"No saved login for {platform}/{lang}. "
                f"Run: python3 setup_profile.py {platform} {lang}"
            )
        proc = subprocess.Popen([
            config.BROWSER_BIN,
            "-no-remote",
            "-P", account["profile"],
            account["url"],
        ])

    human.wait(config.LOAD_WAIT_SEC, config.LOAD_WAIT_SEC + 2)
    return proc


def close_account(proc):
    """Closes the Chrome window opened by open_account(), cleanly then forcefully."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    human.wait(1, 2)


def click_text(label_text, region=None, timeout=8, retries=2):
    timeout = _fast_timeout(timeout, 3)
    retries = _fast_retries(retries, 1)
    last_err = None
    start_time = time.time()
    for attempt in range(retries + 1):
        try:
            x, y = vision.find(label_text=label_text, region=region, timeout=timeout)
            human.click(x, y)
            return
        except vision.ElementNotFound as e:
            last_err = e
            elapsed = time.time() - start_time
            _progress_wait(f"still looking for '{label_text}' (attempt {attempt + 1}/{retries + 1})", elapsed)
            human.wait(1, 2)
    raise StepFailed(f"click_text('{label_text}') failed after retries: {last_err}")


def click_template(template_name, region=None, timeout=8, retries=2):
    timeout = _fast_timeout(timeout, 3)
    retries = _fast_retries(retries, 1)
    last_err = None
    start_time = time.time()
    for attempt in range(retries + 1):
        try:
            x, y = vision.find(template_name=template_name, region=region, timeout=timeout)
            human.click(x, y)
            return
        except vision.ElementNotFound as e:
            last_err = e
            elapsed = time.time() - start_time
            _progress_wait(f"still looking for template '{template_name}' (attempt {attempt + 1}/{retries + 1})", elapsed)
            human.wait(1, 2)
    raise StepFailed(f"click_template('{template_name}') failed after retries: {last_err}")


def type_text(text):
    human.type_text(text)


def select_all_and_type(text):
    human.key("ctrl", "a")
    human.wait(0.1, 0.3)
    human.type_text(text)


def open_file_via_dialog(path, poll_interval=5, max_wait=40):
    """
    GTK file-chooser dialogs support Ctrl+L to reveal a location bar you can
    type a path into directly — far more reliable than clicking through a
    folder tree, and immune to icon/theme changes.

    Two things this does that a bare Ctrl+L doesn't:
      1) Polls for the dialog actually being on screen (via the 'Recent'
         sidebar label, always present in a GTK file chooser) instead of a
         fixed sleep, since Studio can take a while to spawn the dialog.
      2) Clicks that sidebar label first before sending Ctrl+L. A real OS
         mouse click reliably grabs window focus on this VM; a keyboard
         event with no prior click does not (this was the root cause of
         the old focus bug — wmctrl/xdotool can't see or activate the
         xdg-desktop-portal dialog, but a genuine click on it works fine).
    """
    max_wait = _fast_timeout(max_wait, 10)
    poll_interval = _fast_poll(poll_interval, 1)
    deadline = time.time() + max_wait
    dialog_point = None
    start_time = time.time()
    while time.time() < deadline:
        dialog_point = vision.find_text("Recent", timeout=poll_interval)
        if dialog_point:
            break
        elapsed = time.time() - start_time
        _progress_wait(f"still waiting for file dialog to appear", elapsed)
    if not dialog_point:
        raise StepFailed(f"File dialog never appeared after {max_wait}s wait")

    x, y = dialog_point
    human.click(x, y)
    human.wait(0.3, 0.6)
    human.key("ctrl", "l")
    human.wait(0.3, 0.6)
    human.type_text(str(path))
    human.wait(0.2, 0.4)
    human.key("Return")
    human.wait(1, 2)


def below_chrome_region(chrome_height=150):
    """
    Full width/height region starting below the browser's title bar + tab row
    + address bar stack. Anchor searches (e.g. locate_text('Studio', ...) used
    to confirm the real page has loaded before clicking Create) MUST be
    scoped to this region.

    Without it, OCR can match the anchor text sitting in the browser's own
    chrome instead of the actual page -- this happened directly: the Firefox
    tab title reads "YouTube Creator Studio", so an unscoped search for
    "Studio" matched the tab label (visible instantly) rather than waiting
    for the real in-page Studio logo to render, defeating the whole point of
    using it as a "page is actually ready" signal. 150px comfortably clears
    the title bar + tab row + address bar on this VM's Firefox/GNOME setup.
    """
    import pyautogui
    w, h = pyautogui.size()
    return (0, chrome_height, w, h - chrome_height)


def locate_text(label_text, region=None, timeout=60, poll=2):
    """
    Like wait_for_text, but returns the element's (x, y) center point instead
    of just True/False, so it can be used as a position anchor.
    """
    timeout = _fast_timeout(timeout, 10)
    poll = _fast_poll(poll, 1)
    deadline = time.time() + timeout
    start_time = time.time()
    while time.time() < deadline:
        pt = vision.find_text(label_text, region=region, timeout=poll)
        if pt:
            return pt
        elapsed = time.time() - start_time
        _progress_wait(f"still looking for '{label_text}'", elapsed)
        time.sleep(poll)
    raise StepFailed(f"Timed out waiting for '{label_text}'")


def band_region(anchor_y, half_height=45):
    """
    Full-width horizontal band centered on anchor_y. Use this to scope a text
    search to one specific row of the actual page UI once you know its
    y-coordinate, instead of guessing a percentage of the whole screen.

    A percentage-of-screen guess (the old top_nav_region()) can accidentally
    include the browser's own tab/title bar above the page content -- this
    bit us directly: the Firefox tab label "YouTube Creator Studio" fuzzy-
    matched a click_text('Create') search while the real page was still
    loading underneath, causing a click on the browser chrome instead of the
    in-page button. Anchoring to a real in-page element's position (e.g. via
    locate_text('Studio', ...) for the Studio logo, which only exists once
    the page has actually rendered) avoids that whole class of bug.
    """
    import pyautogui
    w, _ = pyautogui.size()
    y = max(0, anchor_y - half_height)
    return (0, y, w, half_height * 2)


def wait_for_text(label_text, region=None, timeout=60, poll=2):
    """Blocks until label_text appears (e.g. waiting for upload/processing)."""
    timeout = _fast_timeout(timeout, 10)
    poll = _fast_poll(poll, 1)
    deadline = time.time() + timeout
    start_time = time.time()
    while time.time() < deadline:
        pt = vision.find_text(label_text, region=region, timeout=poll)
        if pt:
            return True
        elapsed = time.time() - start_time
        _progress_wait(f"still waiting for '{label_text}'", elapsed)
        time.sleep(poll)
    raise StepFailed(f"Timed out waiting for '{label_text}'")
