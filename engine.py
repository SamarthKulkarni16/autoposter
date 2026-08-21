"""
engine.py — primitives that platform recipes are built from.
Recipes (platforms/*.py) should only call these, never raw pyautogui,
so all timing/retry/failure-logging behavior stays consistent everywhere.
"""

import time
import subprocess
import config
import vision
import human_actions as human


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
    last_err = None
    for attempt in range(retries + 1):
        try:
            x, y = vision.find(label_text=label_text, region=region, timeout=timeout)
            human.click(x, y)
            return
        except vision.ElementNotFound as e:
            last_err = e
            human.wait(1, 2)
    raise StepFailed(f"click_text('{label_text}') failed after retries: {last_err}")


def click_template(template_name, region=None, timeout=8, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            x, y = vision.find(template_name=template_name, region=region, timeout=timeout)
            human.click(x, y)
            return
        except vision.ElementNotFound as e:
            last_err = e
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
    deadline = time.time() + max_wait
    dialog_point = None
    while time.time() < deadline:
        dialog_point = vision.find_text("Recent", timeout=poll_interval)
        if dialog_point:
            break
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


def locate_text(label_text, region=None, timeout=60, poll=2):
    """
    Like wait_for_text, but returns the element's (x, y) center point instead
    of just True/False, so it can be used as a position anchor.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        pt = vision.find_text(label_text, region=region, timeout=poll)
        if pt:
            return pt
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
    deadline = time.time() + timeout
    while time.time() < deadline:
        pt = vision.find_text(label_text, region=region, timeout=poll)
        if pt:
            return True
        time.sleep(poll)
    raise StepFailed(f"Timed out waiting for '{label_text}'")
