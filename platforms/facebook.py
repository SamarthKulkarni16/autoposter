"""
platforms/facebook.py — Reel-posting flow for a Facebook Page.

main.py already opened the shared "facebook_shared" profile (same login for
hi/ar/pt/es -- see config.py) and navigated to THIS lang's specific Page URL
(each lang has its own Page: "Samarth Kulkarni HI"/"Arabic"/"Portuguese"/
"ES", all admin'd from samarth.youtube1@gmail.com) by the time post() is
called.

Sequence, as described from live UI (Aug 2026), Reel branch only:
scroll to find "What's on your mind" -> click "Reel" (next to it, with its
own logo) -> "Add Video" (left side) -> pick file (may glitch and reopen the
picker once -- reselect if so) -> Next -> Next -> title placeholder
"Describe your reel..." (clear + fill) -> confirm visibility is Public ->
Post.

ONLY THE REEL BRANCH IS BUILT. The described sequence explicitly splits into
two paths depending on whether the video is short-form ("it becomes two
parts") -- the non-Reel/regular-post branch has not been described yet, so
post() raises clearly if it's ever asked to use that path instead of
guessing at an undocumented flow. All jobs are currently short dubbed clips,
so this covers what actually runs today.

UNTESTED FIRST DRAFT, same caveat as platforms/pinterest.py: selector
strings are best guesses from the described sequence, not confirmed
accessible names/roles. Expect at least one round of live-testing fixes.
"""

import time

import config
import engine
import human_actions as human


def post(ctx, page):
    """
    ctx = {
        "lang": "hi",
        "video_path": "/home/user/outbox/vid123/hi.mp4",
        "title": "...",
        "caption": "...",   # unused for now, same as youtube.py/pinterest.py
        "tags": "...",      # unused for now
        "page": "Samarth Kulkarni HI",   # which Page, for logging/sanity only
        "is_short": True,   # optional, defaults True -- see module docstring
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to this lang's Facebook Page URL and logged into the shared
    facebook_shared profile.
    """
    if not ctx.get("is_short", True):
        raise engine.StepFailed(
            "platforms/facebook.post() was asked to post a non-Reel video, "
            "but that branch of the sequence hasn't been described/built "
            "yet -- only the Reel path is implemented. Get the regular-post "
            "click sequence and add it to this file before running this."
        )

    # LIVE-TESTING FIX (Aug 2026): the Facebook Page URL loads in VIEWER mode
    # ("You're viewing as yourself, not the Page") unless we first switch into
    # the Page -- the wall composer ("What's on your mind?") simply does not
    # exist until we do. The login profile is the personal account that
    # administers these Pages, so a "Switch Now" / "Switch into ... Page"
    # control is present; click it to become the Page so the composer appears.
    _open_reel_composer(page, ctx)

    _upload_reel_video(page, ctx["video_path"])

    # Facebook's Reel "Next" stays disabled until the uploaded video finishes
    # its own processing (transcode/preview) -- same pattern as Pinterest's
    # title field. Wait for it to enable instead of clicking early and looping
    # on a disabled button. Can take a couple minutes for a real clip.
    engine.wait_for_enabled(page, "Next", exact=True, timeout=240000)
    human.wait(1, 2)
    engine.click_text_in_scrollable(page, "Next", max_scrolls=6)
    human.wait(0.5, 1)
    # Same "Next" button/location clicked a second time (per description: a
    # second, separate screen -- crop/edit, then details -- both use "Next"
    # at the same spot).
    engine.wait_for_enabled(page, "Next", exact=True, timeout=60000)
    engine.click_role(page, "button", "Next", exact=True, timeout=15000)
    human.wait(0.5, 1)

    title_field = engine.locate(
        page, text="Describe your reel...", exact=False, timeout=15000,
    )
    engine.select_all_and_type(page, title_field, ctx["title"])

    _ensure_public(page)

    engine.click_role(page, "button", "Post", exact=True, timeout=15000)

    # GUESS at the post-publish confirmation -- not yet confirmed against
    # the real UI. If this times out but the Reel actually posted, this is
    # the first thing to fix, same as pinterest.py's confirmation-text guess.
    engine.wait_for_text(page, "Your reel was posted", exact=False, timeout=60000)


def _open_reel_composer(page, ctx):
    """
    Switch into the Page (if needed), open the wall composer's Reel option,
    and return with the Reel creation flow ready for upload. Retries a few
    times with a fresh page reload (transient overlays), logging each step so
    we can see exactly which one blocks.
    """
    import logging
    log = logging.getLogger("facebook")
    for attempt in range(3):
        try:
            _switch_into_page(page); log.info("[FB] switch done (attempt %d)", attempt)
            engine.click_text_in_scrollable(page, "What's on your mind", max_scrolls=12)
            log.info("[FB] clicked 'What's on your mind' (attempt %d)", attempt)
            human.wait(2, 3)
            # JS click bypasses the pointer-event gate that Playwright's strict
            # click hits on the layered composer (confirmed via live DOM probe).
            engine.js_click_text(page, "Reel", exact=True, timeout=20000)
            log.info("[FB] JS-clicked 'Reel' (attempt %d)", attempt)
            human.wait(2, 3)
            engine.wait_for_text(page, "Create reel", exact=False, timeout=15000)
            log.info("[FB] Reel composer opened (attempt %d)", attempt)
            return
        except engine.StepFailed as e:
            log.warning("[FB] attempt %d failed: %s", attempt, str(e)[:120])
            try:
                _save_failure_screenshot(page, "fb_reel_open")
            except Exception:
                pass
            try:
                page_url = config.ACCOUNTS["facebook"][ctx["lang"]]["url"]
                page.goto(page_url, wait_until="domcontentloaded")
                human.wait(3, 5)
            except Exception:
                pass
    raise engine.StepFailed(
        "Could not open the Reel composer after retries (transient overlay "
        "kept intercepting)."
    )


def _save_failure_screenshot(page, label):
    from datetime import datetime as _dt
    from pathlib import Path as _Path
    ts = _dt.now().strftime("%Y%m%d_%H%M%S")
    path = _Path(__file__).parent / "failures" / f"{label}_{ts}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def _switch_into_page(page):
    """
    If the Page loaded in viewer mode (viewing as the admin's personal
    account instead of as the Page), switch into the Page first so the wall
    composer ("What's on your mind?") exists. The "Switch Now"/"Switch into
    ... Page" control disappears once we're already in the Page, so this is
    a best-effort first step that only acts when the control is present.
    """
    for label in ("Switch Now", "Switch into", "Switch"):
        try:
            el = page.get_by_text(label, exact=True).first
            if el.count() and el.is_visible():
                engine.click_locator(page, el, timeout=8000)
                human.wait(3, 5)
                # Switching can leave a full-page overlay/lightbox on top that
                # intercepts the composer clicks -- dismiss it if present.
                try:
                    page.keyboard.press("Escape")
                    human.wait(1, 2)
                except Exception:
                    pass
                return
        except Exception:
            continue


def _upload_reel_video(page, video_path):
    """
    Uploads the Reel video. The composer's file intake is genuinely finicky,
    so this uses the ONLY method PROBED to actually register a clip: dispatch
    a native click() on the composer's video <input type=file> inside an
    expect_file_chooser, then set_files() -- going through the browser's real
    file-input path that Facebook's uploader listens on. (Probed live:
    set_input_files() on the visible/dedicated input left "Next" disabled
    forever, as did clicking the "Add Video"/"Upload" text; only the native
    click -> chooser -> set_files path removed the "upload your video"
    placeholder and started processing.)
    """
    # The composer's video input -- first accept*="video/mp4" input.
    # Wait until the dropzone placeholder is actually rendered so the composer
    # is fully interactive before we click its input (grabbing it too early can
    # target a replacing/detached node).
    try:
        page.get_by_text("Upload your video", exact=False).first.wait_for(
            state="visible", timeout=15000
        )
    except Exception:
        pass  # placeholder may not be worded exactly; proceed anyway
    human.wait(1, 2)
    video_input = page.locator('input[type="file"][accept*="video/mp4"]').first
    video_input.wait_for(state="attached", timeout=30000)

    last_err = None
    for attempt in range(4):
        try:
            with page.expect_file_chooser(timeout=15000) as fc:
                video_input.evaluate("el => el.click()")
            fc.value.set_files(str(video_path))
            # Poll up to ~40s for the upload to register (placeholder leaves).
            registered = False
            deadline = time.time() + 40
            while time.time() < deadline:
                try:
                    page.get_by_text("Upload your video", exact=False).first.wait_for(
                        state="visible", timeout=2000
                    )
                except Exception:
                    registered = True
                    break
                human.wait(1, 2)
            if registered:
                human.wait(2, 3)
                return
            last_err = ValueError("upload did not register")
            human.wait(2, 3)
        except Exception as e:
            last_err = e
            human.wait(2, 3)
    engine._save_failure("fb_reel_upload", page)
    raise engine.StepFailed(f"Reel video upload failed after retries: {last_err}")


def _ensure_public(page):
    """
    Confirms the visibility/audience selector shown near Post says "Public",
    changing it if not, per "make sure it says public below (if not, change
    to public)".

    GUESS: if "Public" isn't already showing, this assumes clicking whatever
    IS showing (the current audience label -- e.g. "Friends") opens a
    dropdown/list containing a "Public" option to pick. Facebook's exact
    control here isn't confirmed yet; if this breaks, the fix is almost
    certainly narrowing this from "click whatever text is there" to the
    audience selector's specific role/name once we can see the real DOM.
    """
    try:
        engine.locate(page, text="Public", exact=False, timeout=3000)
        return  # already Public -- nothing to do
    except engine.StepFailed:
        pass

    for candidate in ("Friends", "Only me", "Friends except...", "Specific friends"):
        try:
            engine.click_text(page, candidate, exact=False, timeout=2000, retries=0)
            break
        except engine.StepFailed:
            continue
    human.wait(0.3, 0.6)
    engine.click_text(page, "Public", exact=False, timeout=8000)
