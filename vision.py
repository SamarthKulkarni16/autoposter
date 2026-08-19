"""
vision.py — finds UI elements on screen two independent ways:
  1) OCR text match (primary — survives redesigns, icon swaps, theme changes)
  2) Template image match, multi-scale (fallback — for icon-only buttons)

Never use raw fixed coordinates. If both fail, raise and save a screenshot
to failures/ so you can see exactly what broke and fix the recipe, not the code.
"""

import time
import difflib
import numpy as np
import cv2
import pytesseract
import pyautogui
from pathlib import Path
from datetime import datetime

TEMPLATES_DIR = Path(__file__).parent / "templates"
FAILURES_DIR = Path(__file__).parent / "failures"
FAILURES_DIR.mkdir(exist_ok=True)

pyautogui.FAILSAFE = True  # move mouse to corner to abort


class ElementNotFound(Exception):
    pass


def _screenshot():
    img = pyautogui.screenshot()
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def _save_failure(label, frame):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = FAILURES_DIR / f"{label}_{ts}.png"
    cv2.imwrite(str(path), frame)
    return path


def find_text(label_text, region=None, min_ratio=0.72, timeout=8, poll=0.5):
    """
    OCR-scan the screen (or a region) for text approximately matching label_text.
    Fuzzy match so minor rendering/case differences don't cause false failures.
    Returns (x, y) center point in screen coords, or None.
    """
    deadline = time.time() + timeout
    target = label_text.strip().lower()

    while time.time() < deadline:
        frame = _screenshot()
        crop = frame
        ox, oy = 0, 0
        if region:
            x, y, w, h = region
            crop = frame[y:y + h, x:x + w]
            ox, oy = x, y

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        # upscale small UI text for better OCR accuracy
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

        best_ratio, best_box = 0, None
        n = len(data["text"])
        for i in range(n):
            word = data["text"][i].strip().lower()
            if not word:
                continue
            ratio = difflib.SequenceMatcher(None, word, target).ratio()
            # also check if target is a short phrase contained across adjacent words
            if ratio > best_ratio:
                best_ratio = ratio
                bx, by, bw, bh = (data["left"][i], data["top"][i],
                                   data["width"][i], data["height"][i])
                best_box = (bx / 2 + ox, by / 2 + oy, bw / 2, bh / 2)  # /2 to undo upscale

        if best_ratio >= min_ratio and best_box:
            bx, by, bw, bh = best_box
            return (int(bx + bw / 2), int(by + bh / 2))

        time.sleep(poll)

    return None


def find_template(template_name, region=None, threshold=0.82, scales=None, timeout=8, poll=0.5):
    """
    Multi-scale template match against templates/<template_name>.png.
    Use for icon-only buttons with no reliable text (e.g. a bare '+' icon).
    """
    scales = scales or [0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15]
    tpl_path = TEMPLATES_DIR / f"{template_name}.png"
    if not tpl_path.exists():
        raise FileNotFoundError(f"No template saved for '{template_name}'. "
                                 f"Capture one with capture_template.py first.")
    template = cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE)

    deadline = time.time() + timeout
    while time.time() < deadline:
        frame = _screenshot()
        crop = frame
        ox, oy = 0, 0
        if region:
            x, y, w, h = region
            crop = frame[y:y + h, x:x + w]
            ox, oy = x, y
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        best_val, best_loc, best_size = 0, None, None
        for s in scales:
            resized = cv2.resize(template, None, fx=s, fy=s)
            if resized.shape[0] > gray.shape[0] or resized.shape[1] > gray.shape[1]:
                continue
            res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val, best_loc, best_size = max_val, max_loc, resized.shape[::-1]

        if best_val >= threshold and best_loc:
            cx = ox + best_loc[0] + best_size[0] // 2
            cy = oy + best_loc[1] + best_size[1] // 2
            return (int(cx), int(cy))

        time.sleep(poll)

    return None


def find(label_text=None, template_name=None, region=None, timeout=8):
    """
    Try OCR text first, then template fallback. This dual-path approach is
    what makes recipes survive platform redesigns long-term.
    """
    point = None
    if label_text:
        point = find_text(label_text, region=region, timeout=timeout)
    if point is None and template_name:
        point = find_template(template_name, region=region, timeout=timeout)

    if point is None:
        frame = _screenshot()
        shot_path = _save_failure((label_text or template_name or "unknown").replace(" ", "_"), frame)
        raise ElementNotFound(
            f"Could not find '{label_text or template_name}'. Screenshot saved to {shot_path}"
        )
    return point
