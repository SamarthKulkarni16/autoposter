"""
platforms/pinterest.py — pin-creation flow for pinterest.com/pin-creation-tool/.

main.py already opened the shared "pinterest_shared" profile (same login for
hi/ar/pt/es -- see config.py) and it's sitting on the pin-creation-tool page
by the time post() is called. ctx["board"] is what makes each lang different
here: same account, different board per post ("Hindi"/"Arabic"/"Portuguese"/
"Spanish"). The English Pinterest account is separate and never touches this
file at all.

Sequence, as described from live UI (Aug 2026): Upload your media -> pick
file -> title (clear + fill) -> board (keep if already correct, else open
dropdown and pick from list) -> Publish.

UNTESTED FIRST DRAFT: unlike platforms/youtube.py (which went through
several rounds of live-testing fixes -- stale locators, wrong element
matches, race conditions), this hasn't been run against the real page yet.
Selector strings below are best guesses from the described sequence, not
confirmed accessible names/roles. Expect to need at least one round of
live-testing fixes, the same way youtube.py did.
"""

import logging
import engine
import human_actions as human

log = logging.getLogger("autoposter")


def post(ctx, page):
    """
    ctx = {
        "lang": "hi",
        "video_path": "/home/user/outbox/vid123/hi.mp4",
        "title": "...",
        "caption": "...",   # unused for now, same as youtube.py's caption
        "tags": "...",      # unused for now
        "board": "Hindi",   # REQUIRED here -- which board to pin to
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to pinterest.com/pin-creation-tool/ and logged into the shared
    pinterest_shared profile.
    """
    board = ctx.get("board")
    if not board:
        raise engine.StepFailed(
            f"platforms/pinterest.post() called without ctx['board'] (lang={ctx.get('lang')}). "
            f"Check config.ACCOUNTS['pinterest'][lang]['board']."
        )

    # LIVE-TESTING FIX (Aug 2026): originally clicked the "Upload your
    # media" label and waited for a native file-chooser dialog, same as
    # youtube.py's pattern. That timed out after 31 retries -- turns out
    # Pinterest's dropzone is backed by a real <input type="file"
    # id="storyboard-upload-input"> already sitting in the DOM, overlapping
    # the visible label and intercepting the click itself (no dialog ever
    # opens for Playwright to catch). Setting the file directly on that
    # input skips the click/interception fight entirely.
    engine.upload_file_direct(page, ctx["video_path"], selector="#storyboard-upload-input")

    # Give the upload a moment to register before touching the title field,
    # same reasoning as youtube.py's post-upload settle wait.
    human.wait(1.5, 2.5)

    # LIVE-TESTING FIX (Aug 2026): originally matched by role="textbox",
    # name="Tell everyone what your Pin is about", assuming that text was
    # the field's accessible name. It isn't -- the field has a separate
    # visible <label>Title</label> above it, so Chromium computes the
    # accessible name as "Title" instead, and "Tell everyone..." is only
    # the placeholder shown inside the empty box. That mismatch is why the
    # locate() call kept timing out even once upload/encoding were both
    # confirmed fine (the failure screenshot showed the field rendered
    # normally). Matching by placeholder instead of accessible name fixes
    # it. select_all_and_type still clears any pre-filled text before
    # typing, same as before.
    title_field = engine.locate_by_placeholder(
        page, "Tell everyone what your Pin is about",
        exact=False, timeout=15000,
    )

    # LIVE-TESTING FIX (Aug 2026): the field is visible immediately but
    # stays disabled (<input disabled ... id="storyboard-selector-title">)
    # until Pinterest finishes its own server-side video upload+processing
    # -- normal Pinterest behavior (their docs note video Pins "may require
    # additional processing time"; their community forum has reports of
    # this taking several minutes on a slow connection/large file), not
    # something particular to this automation. select_all_and_type()'s
    # click() is what actually waits for "enabled", so give it a generous
    # timeout instead of the 30s default so it outlasts real processing
    # time rather than giving up early.
    log.info(f"Waiting for Pinterest to finish processing the video (lang={ctx.get('lang')})...")
    engine.select_all_and_type(page, title_field, ctx["title"], timeout=180000)

    _select_board(page, board)

    # Publish button, top right. exact=True for the same reason youtube.py
    # uses it on its Next/Publish buttons -- avoid accidentally matching an
    # unrelated element whose accessible name merely contains "Publish".
    engine.click_role(page, "button", "Publish", exact=True, timeout=15000)

    # GUESS at the post-publish confirmation text -- not yet confirmed
    # against the real UI. If this times out but the pin actually published,
    # this is the first thing to fix: replace with whatever text/toast
    # Pinterest actually shows.
    engine.wait_for_text(page, "Published", exact=False, timeout=60000)


def _select_board(page, board_name):
    """
    The board field may already show the right board selected (per the
    described sequence: "if the language we want to post is already
    selected, keep it"). We check for that first so we don't unnecessarily
    open/re-pick from the dropdown every single post.

    NOTE: page.get_by_text(board_name) alone can't distinguish "board_name
    is the CURRENTLY SELECTED value" from "board_name merely appears
    somewhere on the page" (e.g. in a prior post's title). This is a known
    weak point -- if it causes false-positive skips or false negatives, the
    fix (once we can see the real DOM) is almost certainly narrowing this to
    a role/name specific to the board-selector control itself, the same way
    youtube.py's Next/Publish had to be narrowed with exact=True.
    """
    try:
        engine.locate(page, text=board_name, exact=False, timeout=3000)
        return  # already selected/visible -- nothing to do
    except engine.StepFailed:
        pass

    # Not already selected -- open the board dropdown. GUESS at the trigger:
    # assuming a "Board" labeled control with a dropdown arrow near it.
    engine.click_text(page, "Board", exact=False, timeout=15000)
    human.wait(0.3, 0.6)

    # The board we want may be visible immediately, or may need scrolling
    # inside the dropdown's OWN small scroll pane (per the described "3
    # scrolls -- 2 are the main page, 1 is the small one nearest the board
    # names" -- click_text_in_scrollable targets that innermost one).
    engine.click_text_in_scrollable(page, board_name, exact=False)
