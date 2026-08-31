"""
platforms/x.py — post-composing flow directly from x.com/home.

main.py already opened this lang's dedicated, fully separate account (own
email, own login, own profile -- same pattern as instagram.py) and it's
sitting on the X home timeline by the time post() is called.

Sequence, as described + confirmed via live screenshots (Aug 2026): click
the "What's happening?" compose box at the top of the timeline -> type the
title -> click the media icon (first icon in the bottom toolbar, left of the
GIF icon) -> pick the video file -> click "Post" bottom-right of the compose
box (scroll down slightly if it's not visible) -> wait for the "Your post
was sent" confirmation.

Simpler than pinterest.py/facebook.py/instagram.py -- there's no separate
creation page/modal to navigate to first, it's all inline on the home feed
itself.

UNTESTED FIRST DRAFT, same caveat as the other platform modules: most of
this was confirmed against real screenshots (compose box location, toolbar
icon order, Post button position, confirmation text), but the media icon is
icon-only with no visible label in the screenshots, so its accessible name
below is a guess -- flagged as the most likely thing to need a
live-testing fix.
"""

import engine
import human_actions as human


def post(ctx, page):
    """
    ctx = {
        "lang": "hi",
        "video_path": "/home/user/outbox/vid123/hi.mp4",
        "title": "...",
        "caption": "...",   # unused for now, same as the other platforms
        "tags": "...",      # unused for now
        "handle": "@SamarthK_hi",   # logging/sanity only
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to x.com/home and logged into this lang's own account.
    """
    compose_box = engine.locate(
        page, role="textbox", name="What's happening?", exact=False, timeout=20000,
    )
    engine.select_all_and_type(page, compose_box, ctx["title"])

    # First icon in the toolbar, left of the GIF icon -- icon-only in the
    # screenshots, no visible label. GUESS at the accessible name ("Add
    # photos or video" is X's typical aria-label for this control); if this
    # fails to find anything, the fix is locating it by its real
    # role/name once we can inspect the live DOM, the same class of fix
    # already flagged for other platforms' icon-only controls.
    media_trigger = engine.locate(
        page, role="button", name="Add photos or video", exact=False, timeout=15000,
    )
    engine.upload_file(page, media_trigger, ctx["video_path"])
    human.wait(1.5, 3)

    # "Post" sits bottom-right of the compose box -- per the description it
    # can end up just below the fold once a video's attached, hence the
    # scroll-and-find helper rather than a plain click.
    engine.click_text_in_scrollable(page, "Post", exact=True)

    engine.wait_for_text(page, "Your post was sent", exact=False, timeout=90000)
