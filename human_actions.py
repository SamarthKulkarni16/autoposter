"""
human_actions.py — human-shaped mouse movement and typing, built on top of
Playwright's own actionability waits instead of raw pixel coordinates.

Playwright already knows exactly where an element is in the DOM and will
wait for it to be visible/stable/enabled before interacting with it, so this
module isn't responsible for "finding" anything anymore (see engine.py) —
just for making the resulting movement/typing look less robotic than an
instant teleport-click would.
"""

import time
import random
import math


def _bezier_path(x1, y1, x2, y2, steps=20):
    dist = math.hypot(x2 - x1, y2 - y1)
    bend = random.uniform(-0.15, 0.15) * dist
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    length = max(math.hypot(dx, dy), 1)
    perp = (-dy / length, dx / length)
    cx, cy = mx + perp[0] * bend, my + perp[1] * bend

    points = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t ** 2 * x2
        y = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t ** 2 * y2
        points.append((x, y))
    return points


def move_to(page, x, y, from_x=None, from_y=None, duration=None):
    """Move the real mouse pointer to (x, y) along a slight curve instead of
    a straight teleport. from_x/from_y default to page center since
    Playwright (unlike pyautogui) has no concept of 'current OS cursor
    position' to read back."""
    x0 = from_x if from_x is not None else x + random.uniform(-80, 80)
    y0 = from_y if from_y is not None else y + random.uniform(-80, 80)
    dist = math.hypot(x - x0, y - y0)
    duration = duration or min(1.0, max(0.2, dist / 1400))
    steps = max(8, int(duration * 40))
    path = _bezier_path(x0, y0, x, y, steps=steps)
    step_time = duration / steps
    for px, py in path:
        page.mouse.move(px, py)
        time.sleep(step_time * random.uniform(0.7, 1.3))


def click_locator(page, locator, jitter=2, timeout=15000):
    """Click a Playwright Locator with human-ish mouse movement leading into
    it. Playwright's own actionability checks (visible/stable/enabled/
    receives-events) already run before this, so no manual find/retry loop
    is needed the way vision.py used to require."""
    locator.wait_for(state="visible", timeout=timeout)
    locator.scroll_into_view_if_needed(timeout=timeout)
    box = locator.bounding_box()
    if box:
        tx = box["x"] + box["width"] / 2 + random.randint(-jitter, jitter)
        ty = box["y"] + box["height"] / 2 + random.randint(-jitter, jitter)
        move_to(page, tx, ty)
        time.sleep(random.uniform(0.08, 0.22))
    locator.click(timeout=timeout)
    time.sleep(random.uniform(0.15, 0.4))


def type_text(locator, text, delay_ms_range=(35, 65)):
    """Types at a human-ish speed with small per-chunk jitter. No error
    injection — deliberate typos risk posting a broken caption, not worth
    the realism."""
    locator.click()
    # press_sequentially takes one fixed delay per call, so chunk the text
    # into small pieces and vary the delay between chunks for jitter.
    i = 0
    while i < len(text):
        chunk_len = random.randint(2, 5)
        chunk = text[i:i + chunk_len]
        locator.press_sequentially(chunk, delay=random.uniform(*delay_ms_range))
        i += chunk_len
    time.sleep(random.uniform(0.2, 0.5))


def wait(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))
