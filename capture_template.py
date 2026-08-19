"""
capture_template.py — run this ON THE UBUNTU DESKTOP to save a template
image for any icon-only button OCR can't reliably read (rare — most YT/IG/
FB/TikTok/X buttons have text labels, so you likely won't need many of these).

Usage:
    python3 capture_template.py plus_icon

Then: switch to the window/tab showing the icon, wait for the 5s countdown,
click-drag a tight box around JUST the icon (no surrounding whitespace/text),
and it saves to templates/plus_icon.png
"""

import sys
import time
from pathlib import Path
import pyautogui

TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 capture_template.py <name>")
        sys.exit(1)
    name = sys.argv[1]

    print("Switch to the target window now. Capturing full screen in:")
    for i in (5, 4, 3, 2, 1):
        print(i)
        time.sleep(1)

    shot = pyautogui.screenshot()
    tmp_path = TEMPLATES_DIR / f"_fullshot_{name}.png"
    shot.save(tmp_path)
    print(f"Full screenshot saved to {tmp_path}")
    print("Open it in an image viewer/editor, crop tightly around the icon,")
    print(f"and save the crop as: {TEMPLATES_DIR / (name + '.png')}")


if __name__ == "__main__":
    main()
