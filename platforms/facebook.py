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
    # NOTE: the composer can have a stale/disabled "Next" from a background
    # wall post + the live enabled Reel "Next" at once, so wait_for_enabled
    # returns the ENABLED one and we click exactly that (not `.first`).
    nxt = engine.wait_for_enabled(page, "Next", exact=True, timeout=480000)
    human.wait(1, 2)
    human.click_locator(page, nxt)
    human.wait(1, 2)
    # Same "Next" button/location clicked a second time (per description: a
    # second, separate screen -- crop/edit, then details -- both use "Next"
    # at the same spot).
    nxt2 = engine.wait_for_enabled(page, "Next", exact=True, timeout=60000)
    human.wait(0.5, 1)
    human.click_locator(page, nxt2)
    human.wait(0.5, 1)

    title_field = engine.locate(
        page, text="Describe your reel...", exact=False, timeout=15000,
    )
    engine.fill_contenteditable(page, title_field, ctx["title"])

    _ensure_public(page)

    # The Post button is disabled until there's a valid uploaded reel. If the
    # video upload was genuinely rejected (Facebook shows a 'can't be
    # uploaded' toast), Post never enables -- wait for it, and if it never
    # does, that's an upload rejection, not a UI hiccup.
    post = engine.wait_for_enabled(page, "Post", exact=True, timeout=120000)
    human.wait(0.5, 1)
    # JS-click bypasses any pointer-intercept overlay on the Post button.
    post.evaluate("el => el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))")

    # Post-submit confirmation, confirmed live (Aug 2026): after publishing,
    # Facebook returns to the Page wall and the Reel details composer closes.
    # A transient success banner may also appear: "Your reel has been
    # published. You can also share to stories, groups and other places."
    #
    # The banner text alone is an unreliable success signal (it's a transient
    # notification and get_by_text().first can latch onto a hidden node), so
    # the PRIMARY signal is the composer closing: the Reel details "Post"
    # publish button disappearing (composer gone back to the wall). The banner
    # is accepted as an alternative confirmation if seen.
    _wait_for_facebook_post_done(page)


def _wait_for_facebook_post_done(page, timeout=90000):
    """
    Blocks until the Reel post is confirmed submitted.

    Success signals (any one):
      1. The transient success banner "...has been published..." is visible.
      2. The Reel details composer closed -- its "Post" publish button is no
         longer visible (we're back on the Page wall).

    The composer closing is the primary signal because the banner is a
    transient notification that can appear and disappear quickly, and
    get_by_text().first can latch onto a hidden node.
    """
    import logging
    log = logging.getLogger("facebook")
    deadline = time.time() + timeout / 1000.0
    while time.time() < deadline:
        # Signal 1: success banner visible.
        try:
            bn = page.get_by_text("has been published", exact=False)
            for i in range(bn.count()):
                try:
                    if bn.nth(i).is_visible():
                        log.info("[FB] post confirmed (banner)")
                        return
                except Exception:
                    continue
        except Exception:
            pass
        # Signal 2: composer closed -- no visible "Post" publish button,
        # and the wall composer ("What's on your mind?") has returned.
        try:
            posts = page.get_by_role("button", name="Post", exact=True)
            any_post_visible = False
            for i in range(posts.count()):
                try:
                    if posts.nth(i).is_visible():
                        any_post_visible = True
                        break
                except Exception:
                    continue
            if not any_post_visible:
                try:
                    wall = page.get_by_text("What's on your mind", exact=False)
                    wall_visible = wall.count() > 0 and wall.first.is_visible()
                except Exception:
                    wall_visible = False
                if wall_visible:
                    log.info("[FB] post confirmed (composer closed)")
                    return
        except Exception:
            pass
        human.wait(1, 2)
    shot = engine._save_failure("fb_post_confirm", page)
    raise engine.StepFailed(
        "Timed out waiting for Reel post confirmation. Screenshot saved to "
        f"{shot}"
    )


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


def _upload_reel_video(page, video_path, ctx=None):
    """
    Uploads the Reel video into Facebook's Reel composer and waits for it to
    register (the "Upload your video..." placeholder clears).

    Facebook validates the uploaded file CLIENT-SIDE by decoding it as H.264
    before it accepts the upload (hence PLATFORMS_NEEDING_H264 / snap-chromium
    in config). Upload is genuinely intermittent: occasionally Facebook's
    in-browser decoder isn't ready yet and it flashes "your file can't be
    uploaded: <name>". The SAME bytes that get rejected will be accepted on a
    later attempt, so we retry on a FRESH Reel composer (re-opening clears the
    stale input bindings and the reject toast) until it registers.

    Upload strategies, in order, all confirmed live:
      1. REAL file chooser -- JS-click "Add Video" inside expect_file_chooser
         (a layered overlay intercepts Playwright's strict click) and hand the
         file to the chooser via set_files. This fires Facebook's real
         trusted handler.
      2. set_input_files on the Reel's own video-accepting <input type=file>
         (the input whose accept is "video/*,video/mp4,..." -- NOT the wall
         post "Add to your post" image/video input).
    """
    import logging
    log = logging.getLogger("facebook")

    def _video_input():
        """Return the Reel composer's dedicated video <input type=file>
        (accept starts with video-only set), or None."""
        ins = page.locator('input[type="file"]')
        for i in range(ins.count()):
            try:
                acc = (ins.nth(i).get_attribute("accept") or "").lower()
            except Exception:
                continue
            if acc.startswith("video/*,  ") or acc.startswith("video/*,") or acc.startswith("video/"):
                return ins.nth(i)
        return None

    def registered():
        """
        The actionable ready-signal is the Reel "Next" button becoming
        ENABLED (Facebook turns it on once the upload is accepted/registered).
        Confirmed live: the file uploads, Next enables, and only ~6s later a
        'can't be uploaded' toast may appear (secondary/delayed validation)
        WITHOUT disabling Next. So we gate on Next-enabled, not on raw
        placeholder/toast text -- treating the toast as fatal was aborting
        flows that had actually reached the enabled-Next state and would have
        posted fine.
        Returns True when Next is enabled+visible, else False (still pending).
        """
        try:
            nxt = page.get_by_text("Next", exact=True)
            for i in range(nxt.count()):
                try:
                    if nxt.nth(i).is_enabled() and nxt.nth(i).is_visible():
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    last_err = None
    for attempt in range(6):
        try:
            # Fresh composer before every retry (attempt 0's composer was just
            # opened by _open_reel_composer and is already fresh).
            if attempt > 0:
                _reopen_reel_composer(page)
            # Settle so Facebook's decoder/upload handler is ready before we
            # click Add Video -- reduces the premature-reject race.
            human.wait(2, 3)
            # Strategy 1: real chooser.
            try:
                with page.expect_file_chooser(timeout=15000) as fc_info:
                    page.get_by_text("Add Video", exact=False).first.evaluate(
                        "el => el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))"
                    )
                fc_info.value.set_files(str(video_path))
                log.info("[FB] upload attempt %d: via real chooser", attempt)
                ok = _wait_ingest(registered, timeout=30)
                if ok is True:
                    log.info("[FB] upload registered (placeholder cleared)")
                    return
                last_err = ok if ok is not False else ValueError("did not ingest")
            except Exception as e:
                last_err = e
                log.warning("[FB] attempt %d chooser err: %s", attempt, str(e)[:120])
            # Strategy 2: set_input_files directly on the Reel video input.
            try:
                vin = _video_input()
                if vin is not None:
                    vin.set_input_files(str(video_path))
                    log.info("[FB] upload attempt %d: set_input_files on Reel input", attempt)
                    ok = _wait_ingest(registered, timeout=30)
                    if ok is True:
                        log.info("[FB] upload registered (placeholder cleared)")
                        return
                    last_err = ok if ok is not False else ValueError("did not ingest")
            except Exception as e:
                last_err = e
            log.warning("[FB] attempt %d not ingested (last=%s), retrying fresh composer",
                        attempt, str(last_err)[:80])
        except Exception as e:
            last_err = e
            log.warning("[FB] upload attempt %d error: %s", attempt, str(e)[:140])
        human.wait(2, 3)
    engine._save_failure("fb_reel_upload", page)
    raise engine.StepFailed(f"Reel video upload failed after retries: {last_err}")


def _wait_ingest(check, timeout=30):
    """Poll `check` (returns True/False/'reject') until it resolves."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = check()
        if r is True or r == "reject":
            return r
        human.wait(2, 2)
    return False


def _reopen_reel_composer(page):
    """Close any open composer and open a fresh Reel composer (clean input
    state + clears any reject toast)."""
    import logging
    log = logging.getLogger("facebook")
    try:
        page.keyboard.press("Escape")
        human.wait(1, 2)
    except Exception:
        pass
    try:
        page.get_by_text("What's on your mind", exact=False).first.evaluate(
            "el => el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))")
        human.wait(2, 3)
        page.get_by_text("Reel", exact=True).first.evaluate(
            "el => el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))")
        human.wait(2, 3)
        engine.wait_for_text(page, "Create reel", exact=False, timeout=15000)
        log.info("[FB] reopened fresh Reel composer")
    except Exception as e:
        log.warning("[FB] reopen composer warning: %s", str(e)[:120])


def _ensure_public(page):
    """
    Confirms the audience/visibility selector shown near Post says "Public",
    changing it if not -- per "make sure it says public below (if not, change
    to public)".

    Confirmed live (Aug 2026): the Reel details screen renders the audience
    selector as a button whose accessible name is "Public / Anyone on or off
    Facebook". Both the creator wall and the Reel composer default to Public,
    so this normally only needs to DETECT that Publlic is already selected and
    return. The old implementation failed because get_by_text("Public").first
    locked onto a hidden/non-element node and its sibling collision never
    matched -- now we check for a VISIBLE "Public" (or the "Anyone on or off
    Facebook" selector button) and only attempt a change if none is found.
    """
    # 1) The audience selector button itself reads "Public / Anyone on or off
    #    Facebook" when Public is selected -- the authoritative signal.
    try:
        sel = page.get_by_role("button", name="Anyone on or off Facebook")
        if sel.count() and sel.first.is_visible():
            return
    except Exception:
        pass
    # 2) Fallback: any VISIBLE "Public" text element means we're already Public
    #    (get_by_text().first is unreliable here -- it can hit a hidden/blank
    #    node, so scan all matches).
    pubs = page.get_by_text("Public", exact=False)
    n = pubs.count()
    for i in range(n):
        try:
            if pubs.nth(i).is_visible():
                return
        except Exception:
            continue
    # 3) Not Public -- best-effort: click the current audience label to open
    #    the picker, then choose "Public". Rarely reached today (defaults to
    #    Public), kept as a defensive fallback.
    for candidate in ("Friends", "Only me", "Friends except...", "Specific friends"):
        try:
            engine.click_text(page, candidate, exact=False, timeout=2000, retries=0)
            break
        except engine.StepFailed:
            continue
    human.wait(0.3, 0.6)
    try:
        engine.click_text(page, "Public", exact=False, timeout=8000)
    except engine.StepFailed:
        pass
