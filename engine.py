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


def open_file_via_dialog(path, wait_for_dialog=2.0):
    """
    GTK file-chooser dialogs support Ctrl+L to reveal a location bar you can
    type a path into directly — far more reliable than clicking through a
    folder tree, and immune to icon/theme changes.
    """
    time.sleep(wait_for_dialog)
    human.key("ctrl", "l")
    human.wait(0.3, 0.6)
    human.type_text(str(path))
    human.wait(0.2, 0.4)
    human.key("Return")
    human.wait(1, 2)


def wait_for_text(label_text, region=None, timeout=60, poll=2):
    """Blocks until label_text appears (e.g. waiting for upload/processing)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pt = vision.find_text(label_text, region=region, timeout=poll)
        if pt:
            return True
        time.sleep(poll)
    raise StepFailed(f"Timed out waiting for '{label_text}'")
