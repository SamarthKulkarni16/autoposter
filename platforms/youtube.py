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
        "caption": "...",   # used as description
        "tags": "...",      # optional, comma separated
    }
    page = the Playwright Page returned by engine.open_account(), already
    navigated to studio.youtube.com and logged in.
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

    # Title field is focused by default with placeholder text selected
    title_field = engine.locate(page, role="textbox", name="Add a title", timeout=8000)
    engine.select_all_and_type(page, title_field, ctx["title"])

    # Description field: click into it explicitly, it's not auto-focused
    desc_field = engine.locate(page, text="Tell viewers about your video", timeout=8000)
    engine.type_text(desc_field, ctx["caption"])

    human.wait(0.5, 1)

    # "No, it's not made for kids" is the usual default further down
    engine.click_text(page, "No, it's not made for kids")

    # Step through Next -> Next -> Next (elements/checks/visibility screens)
    for _ in range(3):
        engine.click_role(page, "button", "Next")
        human.wait(0.6, 1.2)

    # Visibility screen
    engine.click_text(page, "Public")
    human.wait(0.3, 0.6)
    engine.click_role(page, "button", "Publish")

    # Confirm the publish actually completed
    engine.wait_for_text(page, "Video published", timeout=60000)
