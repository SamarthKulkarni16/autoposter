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

    # "What's on your mind" can sit anywhere from mid-page to near the
    # bottom depending on the Page's layout/recent activity, per the
    # described sequence -- reuse the scroll-and-find helper built for
    # pinterest.py's board picker rather than assuming a fixed scroll depth.
    engine.click_text_in_scrollable(page, "What's on your mind", max_scrolls=12)

    # "Reel" sits at the bottom-left of that composer, with its own logo to
    # the right of the text -- get_by_text should still match on the text
    # portion regardless of the adjacent icon.
    engine.click_text(page, "Reel", exact=False, timeout=15000)
    human.wait(0.5, 1)

    _upload_reel_video(page, ctx["video_path"])

    # Scroll a bit before Next per the described sequence (the Next button
    # may start below the fold in the reel-creation panel).
    engine.click_text_in_scrollable(page, "Next", max_scrolls=6)
    human.wait(0.5, 1)
    # Same "Next" button/location clicked a second time (per description: a
    # second, separate screen -- crop/edit, then details -- both use "Next"
    # at the same spot).
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


def _upload_reel_video(page, video_path):
    """
    Clicks "Add Video" and selects the file. Per the described known glitch,
    the native file picker can silently reopen/re-trigger right after the
    first selection -- if the same "Add Video" trigger is still there a
    moment later, the first selection didn't register and needs to be redone
    (up to 2 extra attempts before giving up).
    """
    trigger = engine.locate(page, text="Add Video", exact=False, timeout=30000)
    engine.upload_file(page, trigger, video_path)
    human.wait(1.5, 3)

    for _ in range(2):
        try:
            still_there = engine.locate(page, text="Add Video", exact=False, timeout=3000)
        except engine.StepFailed:
            return  # trigger's gone -- upload registered, move on
        engine.upload_file(page, still_there, video_path)
        human.wait(1.5, 3)


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
