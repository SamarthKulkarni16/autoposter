"""
platforms/youtube.py — upload flow for YouTube Studio.

main.py already opened the correct logged-in profile and it's sitting on
studio.youtube.com by the time post() is called. Every step here is
OCR-text-driven so it survives YT Studio UI changes — if a step ever
breaks, it's because a label's wording changed; update the string here,
not the engine.
"""

import engine
import human_actions as human


def post(ctx):
    """
    ctx = {
        "lang": "en",
        "video_path": "/home/user/outbox/vid123/en.mp4",
        "title": "...",
        "caption": "...",   # used as description
        "tags": "...",      # optional, comma separated
    }
    """
    # Kick off upload. Region-scoped to the top nav bar so this can't
    # accidentally match "Created" in the analytics table further down.
    engine.click_text("Create", region=engine.top_nav_region())
    human.wait(0.5, 1)
    engine.click_text("Upload videos")

    # OS file picker
    engine.open_file_via_dialog(ctx["video_path"])

    # Wait for it to register the upload before touching title/desc fields
    engine.wait_for_text("Details", timeout=90)

    # Title field is focused by default with placeholder text selected
    engine.select_all_and_type(ctx["title"])

    # Description field: click into it explicitly, it's not auto-focused
    engine.click_text("Tell viewers about your video")
    engine.type_text(ctx["caption"])

    human.wait(0.5, 1)

    # "No, it's not made for kids" is the usual default further down
    engine.click_text("No, it's not made for kids")

    # Step through Next -> Next -> Next (elements/checks/visibility screens)
    for _ in range(3):
        engine.click_text("Next")
        human.wait(0.6, 1.2)

    # Visibility screen
    engine.click_text("Public")
    human.wait(0.3, 0.6)
    engine.click_text("Publish")

    # Confirm the publish actually completed
    engine.wait_for_text("Video published", timeout=60)
