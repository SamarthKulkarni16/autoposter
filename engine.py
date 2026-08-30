"""
engine.py — primitives that platform recipes are built from.
Recipes (platforms/*.py) should only call these, never raw Playwright calls
directly, so retry/failure-logging/timeout behavior stays consistent
everywhere.

This replaces the old OCR/template-matching approach (vision.py) with real
DOM locators. Playwright finds elements by their actual accessible text/role
in the page, pierces shadow DOM automatically (YouTube Studio is built on
web components, which defeated raw CSS selectors but not this), and never
confuses the browser's own tab title or chrome for in-page content the way
screen-pixel OCR could — there's no "band_region"/"below_chrome_region"
pixel-scoping hack needed anymore, because a locator only ever searches the
page DOM, not the OS-level screenshot.
"""

import os
import time
import atexit
import config
import human_actions as human
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

FAILURES_DIR = Path(__file__).parent / "failures"
FAILURES_DIR.mkdir(exist_ok=True)


class StepFailed(Exception):
    pass


def _is_fast_mode():
    """Check if fast/debug mode is enabled via env var or CLI flag."""
    return os.environ.get("DEBUG_FAST", "").lower() in ("1", "true", "yes", "on")


def _fast_timeout(default_ms, fast_ms=12000):
    return fast_ms if _is_fast_mode() else default_ms


# --- Playwright lifecycle ---------------------------------------------------

_pw = None


def _playwright():
    global _pw
    if _pw is None:
        _pw = sync_playwright().start()
        atexit.register(_shutdown)
    return _pw


def _shutdown():
    global _pw
    if _pw is not None:
        try:
            _pw.stop()
        except Exception:
            pass
        _pw = None


def open_account(platform, lang):
    """
    Launches a persistent Chromium context (Playwright's own bundled
    Chromium — NOT the "chrome" channel; real Google Chrome has no official
    ARM64 Linux build, and this VM is an Oracle Ampere/ARM64 instance, so
    channel="chrome" hard-fails there with "Failed to install chrome") using
    the dedicated profile for this (platform, lang) account, already logged
    in, pointed at its start URL. Returns the Page — pass it to
    close_account() when done.

    Chromium, not Firefox: Google's sign-in flow actively fingerprints and
    blocks browsers it detects as automated/embedded ("This browser or app
    may not be secure"), and that block triggers far more reliably against
    Playwright's patched Firefox build than against Chromium running headed
    with --disable-blink-features=AutomationControlled.

    A persistent context IS the profile directory (cookies, local storage,
    everything), so logins made once via setup_profile.py stick around.
    """
    account = config.ACCOUNTS[platform][lang]

    if "profile_path" in account:
        user_data_dir = account["profile_path"]
    else:
        user_data_dir = str(config.PROFILES_DIR / account["profile"])
        if not Path(user_data_dir).exists():
            raise StepFailed(
                f"No saved login for {platform}/{lang}. "
                f"Run: python3 setup_profile.py {platform} {lang}"
            )

    # In headed mode, let the window take over the full screen instead of a
    # small fixed-size viewport (which showed up on RDP as a tiny "restored
    # down" window) -- viewport=None + --start-maximized makes Chromium size
    # itself to the actual screen. In headless mode there's no visible window
    # to maximize, so keep a fixed viewport as before.
    if config.HEADLESS:
        launch_kwargs = dict(viewport={"width": 1440, "height": 900})
    else:
        launch_kwargs = dict(viewport=None)

    context = _playwright().chromium.launch_persistent_context(
        user_data_dir,
        headless=config.HEADLESS,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        **launch_kwargs,
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(account["url"], wait_until="domcontentloaded")
    human.wait(config.LOAD_WAIT_SEC, config.LOAD_WAIT_SEC + 2)
    _dismiss_browser_warning(page)
    return page


def _dismiss_browser_warning(page):
    """
    Some sites (YouTube Studio included) show an 'unsupported/old browser'
    interstitial to Playwright's bundled Chromium, since its pinned version
    trails the latest real Chrome release and their UA sniffing flags it --
    with a 'Skip to <product>' link past it. Best-effort, short timeout,
    never raises: most pages never show this, so this should be a silent
    no-op almost every time.
    """
    try:
        skip_link = page.get_by_text("Skip to", exact=False).first
        skip_link.wait_for(state="visible", timeout=4000)
        human.click_locator(page, skip_link, timeout=4000)
        human.wait(1, 2)
    except Exception:
        pass


def close_account(page):
    """Closes the persistent context opened by open_account()."""
    try:
        page.context.close()
    except Exception:
        pass
    human.wait(1, 2)


def _save_failure(label, page):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = FAILURES_DIR / f"{label}_{ts}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
    return path


def locate(page, text=None, role=None, name=None, exact=False, timeout=8000):
    """
    Returns a Playwright Locator for the given text (substring, case-
    insensitive match across the whole page including shadow DOM) or
    role+name (e.g. role="button", name="Publish"). Waits for it to be
    visible. Raises StepFailed with a saved screenshot on timeout, same
    contract the old vision.find() had.
    """
    timeout = _fast_timeout(timeout)
    try:
        if role:
            locator = page.get_by_role(role, name=name, exact=exact).first
        else:
            locator = page.get_by_text(text, exact=exact).first
        locator.wait_for(state="visible", timeout=timeout)
        return locator
    except PWTimeoutError as e:
        shot_path = _save_failure((name or text or role or "unknown").replace(" ", "_"), page)
        raise StepFailed(
            f"Could not find '{name or text or role}'. Screenshot saved to {shot_path}"
        ) from e


def click_text(page, label_text, exact=False, timeout=8000, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            locator = locate(page, text=label_text, exact=exact, timeout=timeout)
            human.click_locator(page, locator, timeout=timeout)
            return
        except StepFailed as e:
            last_err = e
            human.wait(1, 2)
    raise StepFailed(f"click_text('{label_text}') failed after retries: {last_err}")


def click_role(page, role, name, exact=False, timeout=8000, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            locator = locate(page, role=role, name=name, exact=exact, timeout=timeout)
            human.click_locator(page, locator, timeout=timeout)
            return
        except StepFailed as e:
            last_err = e
            human.wait(1, 2)
    raise StepFailed(f"click_role('{role}', '{name}') failed after retries: {last_err}")


def type_into(page, label_text, text, exact=False, timeout=8000):
    """Click a text-labeled field/container and type into it."""
    locator = locate(page, text=label_text, exact=exact, timeout=timeout)
    human.type_text(locator, text)


def type_text(locator, text):
    human.type_text(locator, text)


def select_all_and_type(page, locator, text):
    """
    Clicks the field, selects everything in it, explicitly deletes the
    selection, then types. The explicit Backspace (not just typing over the
    selection) matters for contenteditable fields like YouTube's title box:
    if the field's content is still settling from an async autofill (e.g.
    YouTube prefilling the title from the uploaded filename) at the exact
    moment we select+type, relying on "typing replaces selection" can lose
    the race and leave a stray fragment of the old text. Select -> delete
    -> (brief pause so any pending DOM update finishes) -> type is more
    robust against that race.
    """
    locator.click()
    human.wait(0.1, 0.2)
    page.keyboard.press("Control+A")
    human.wait(0.1, 0.2)
    page.keyboard.press("Backspace")
    human.wait(0.2, 0.4)
    human.type_text(locator, text)


def upload_file(page, trigger_locator, file_path):
    """
    Uploads a file by clicking whatever triggers the native picker and
    intercepting the file-chooser event — Playwright hands the file straight
    to the input, no OS dialog to see, focus, or type a path into. This
    replaces the old open_file_via_dialog() Ctrl+L-into-GTK-dialog hack
    entirely; that whole class of "dialog never got window focus" bug goes
    away because there's no real OS dialog in the loop anymore.
    """
    with page.expect_file_chooser() as fc_info:
        human.click_locator(page, trigger_locator)
    file_chooser = fc_info.value
    file_chooser.set_files(str(file_path))
    human.wait(1, 2)


def wait_for_text(page, label_text, exact=False, timeout=60000):
    """Blocks until label_text appears (e.g. waiting for upload/processing)."""
    timeout = _fast_timeout(timeout, fast_ms=15000)
    try:
        page.get_by_text(label_text, exact=exact).first.wait_for(state="visible", timeout=timeout)
        return True
    except PWTimeoutError as e:
        shot_path = _save_failure(label_text.replace(" ", "_"), page)
        raise StepFailed(f"Timed out waiting for '{label_text}'. Screenshot saved to {shot_path}") from e
