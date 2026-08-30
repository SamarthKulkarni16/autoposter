"""
platforms/instagram.py — post-creation flow from instagram.com/ (home feed).

main.py already opened this lang's dedicated, fully separate account (own
email, own login -- unlike pinterest/facebook's shared-profile trick, see
config.py) and it's sitting on the Instagram home feed by the time post()
is called.

Sequence, as described + confirmed via live screenshots (Aug 2026): click
"+"/"Create" (left nav) -> "Post" (dropdown) -> "Select from computer"
(triggers native file picker) -> pick file -> click the crop-size icon
(bottom-left of the crop panel) -> pick "9:16" -> Next -> Next -> click the
big caption area below the account name and type the title -> Share -> wait
for the spinner to finish and confirm "Your reel has been shared".

NOTE: choosing "Post" (not a separate "Reel" option) is what leads to the
"New reel" screen per the screenshots -- Instagram's own upload flow treats
a video posted this way as a reel automatically, so there's no separate
short-vs-long branch to handle here the way platforms/facebook.py has to.

UNTESTED FIRST DRAFT, same caveat as pinterest.py/facebook.py: most of this
was confirmed against real screenshots (crop step, caption screen, share
button placement), but a few icon-only controls (the "+"/Create nav item,
the crop-ratio icon) don't have a confirmed accessible name/role yet --
those are flagged below and are the most likely things to need a
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
        "handle": "@samarthkulkarni_hi",   # logging/sanity only
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to instagram.com/ and logged into this lang's own account.
    """
    # "+" in the left nav, shows "Create" as its hover tooltip per the
    # screenshot description -- GUESS: matching on the "Create" text since
    # that's the only confirmed label, but this is an icon-only nav item, so
    # if this fails to find anything the real fix is locating it by its
    # aria-label/role instead (most likely role="link", name="New post" or
    # similar) once we can inspect the live DOM.
    engine.click_text(page, "Create", exact=False, timeout=15000)
    human.wait(0.3, 0.6)

    engine.click_text(page, "Post", exact=True, timeout=10000)
    human.wait(0.3, 0.6)

    # "Select from computer" triggers the native file picker directly.
    select_trigger = engine.locate(page, text="Select from computer", timeout=20000)
    engine.upload_file(page, select_trigger, ctx["video_path"])
    human.wait(1.5, 3)

    _set_aspect_ratio_9_16(page)

    # Two "Next" screens (crop confirm, then filters/edits), same button
    # position both times per the description. exact=True for the same
    # reason youtube.py needs it on its Next/Publish buttons -- avoid
    # matching an unrelated element whose accessible name merely contains
    # "Next".
    for _ in range(2):
        engine.click_role(page, "button", "Next", exact=True, timeout=15000)
        human.wait(0.6, 1.2)

    # Caption screen: a large blank area below the account name/handle (see
    # screenshot 2). No visible placeholder text to key off of in the
    # screenshot -- GUESS at "Write a caption..." as the field's accessible
    # name, Instagram's typical wording for this box in past UI versions.
    # select_all_and_type still works fine even on an empty field (nothing
    # to clear), so this is safe either way.
    caption_field = engine.locate(
        page, role="textbox", name="Write a caption...", exact=False, timeout=15000,
    )
    engine.select_all_and_type(page, caption_field, ctx["title"])

    engine.click_text(page, "Share", exact=True, timeout=15000)

    # Confirmed via the described flow: a spinner shows while uploading,
    # then a checkmark with "Your reel has been shared" underneath.
    engine.wait_for_text(page, "Your reel has been shared", exact=False, timeout=120000)


def _set_aspect_ratio_9_16(page):
    """
    Clicks the crop-size icon (two diagonal arrows, bottom-left of the crop
    panel per the screenshot) to open the ratio menu, then picks "9:16".

    GUESS at the icon's accessible name -- "Select crop" was Instagram's
    typical aria-label for this control in past UI versions, but isn't
    confirmed against this exact build. If this fails, the fix is finding
    the real name/role from the live DOM, the same class of fix
    pinterest.py's board-dropdown trigger and facebook.py's audience
    selector are already flagged as needing.
    """
    crop_icon = engine.locate(page, role="button", name="Select crop", exact=False, timeout=15000)
    human.click_locator(page, crop_icon)
    human.wait(0.3, 0.6)
    engine.click_text(page, "9:16", exact=True, timeout=8000)
