"""
platforms/youtube.py — upload flow for YouTube Studio.

main.py already opened the correct logged-in profile and it's sitting on
studio.youtube.com by the time post() is called. Every step here targets
real page elements by their accessible text/role, so it survives YT Studio
UI changes the same way the old OCR approach aimed to — if a step ever
breaks, it's because a label's wording changed; update the string here, not
the engine. The difference is these are DOM lookups, not screen-pixel
guesses, so there's no ambiguity between the browser's own tab title and the
in-page "Create" button, and no window-focus dance for the file picker.
"""

import engine
import human_actions as human


def post(ctx, page):
    """
    ctx = {
        "lang": "en",
        "video_path": "/home/user/outbox/vid123/en.mp4",
        "title": "...",
        "caption": "...",   # currently unused -- description step removed
        "tags": "...",      # optional, comma separated, currently unused
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to studio.youtube.com and logged in.

    Sequence, exactly: Create -> Upload videos -> SELECT FILES -> pick file
    -> title (clear + fill) -> Next -> Next -> Next -> Public -> Publish.
    No description fill, no "made for kids" click. NOTE: "made for kids" is
    normally a required radio button on the Details screen -- without an
    answer, YouTube may keep Next disabled/blocked. This was stripped out
    on purpose per explicit instruction; if the first Next stalls, that's why.
    """
    # "Create" is YT Studio's own top-nav button (role=button). No need to
    # wait for a separate "Studio" logo anchor first — Playwright's locator
    # already waits for the real element to exist and be visible/stable
    # before clicking, so there's nothing to accidentally click prematurely.
    engine.click_role(page, "button", "Create", timeout=90000)
    human.wait(0.5, 1)

    # "Upload videos" only switches Studio to the upload dialog (a dropzone
    # + a "SELECT FILES" button) -- it does NOT itself open the native file
    # picker. The "SELECT FILES" button inside that dialog is what does,
    # so that's the real file-chooser trigger.
    engine.click_text(page, "Upload videos")
    select_files_trigger = engine.locate(page, text="SELECT FILES", timeout=15000)
    engine.upload_file(page, select_files_trigger, ctx["video_path"])

    # Wait for it to register the upload before touching title/desc fields
    engine.wait_for_text(page, "Details", timeout=90000)

    # YouTube Studio auto-fills the title field from the uploaded filename
    # (our files are named "<lang>.mp4", e.g. "en.mp4") via its own async JS
    # shortly after the "Details" screen appears. Give that a moment to
    # settle before we clear+type our own title, or the two can race and
    # leave a stray filename fragment (e.g. "en") glued onto the title.
    human.wait(1.5, 2.5)

    # Title field is focused by default with placeholder text selected
    title_field = engine.locate(page, role="textbox", name="Add a title", timeout=8000)
    engine.select_all_and_type(page, title_field, ctx["title"])

    # Step through Next -> Next -> Next (elements/checks/visibility screens).
    # exact=True matters here: without it, get_by_role(name="Next") matches
    # any accessible name *containing* "Next" -- which includes Studio
    # dashboard's "Next item" carousel-arrow button (recent uploads strip),
    # sitting behind this dialog's backdrop. .first grabs whichever comes
    # first in the DOM, which was that hidden carousel arrow, not our
    # wizard's actual "Next" button -- so every click got blocked by the
    # modal backdrop intercepting the (wrong, off-screen) element.
    for _ in range(3):
        engine.click_role(page, "button", "Next", exact=True)
        human.wait(0.6, 1.2)

    # Visibility screen
    engine.click_text(page, "Public")
    human.wait(0.3, 0.6)
    engine.click_role(page, "button", "Publish", exact=True)

    # Confirm the publish actually completed
    engine.wait_for_text(page, "Video published", timeout=60000)
