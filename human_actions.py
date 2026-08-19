"""
human_actions.py — human-speed mouse movement, clicking, and typing.
Speed doesn't matter for the task, but human-shaped movement reduces the
chance of any platform flagging perfectly-straight-line, zero-delay input.
"""

import time
import random
import math
import pyautogui

pyautogui.PAUSE = 0  # we control our own timing


def _bezier_path(x1, y1, x2, y2, steps=25):
    # slight random curve control point so movement isn't a straight line
    dist = math.hypot(x2 - x1, y2 - y1)
    bend = random.uniform(-0.15, 0.15) * dist
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    # perpendicular offset for the control point
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


def move_to(x, y, duration=None):
    x0, y0 = pyautogui.position()
    dist = math.hypot(x - x0, y - y0)
    duration = duration or min(1.2, max(0.25, dist / 1400))
    steps = max(10, int(duration * 60))
    path = _bezier_path(x0, y0, x, y, steps=steps)
    step_time = duration / steps
    for px, py in path:
        pyautogui.moveTo(px, py)
        time.sleep(step_time * random.uniform(0.7, 1.3))


def click(x, y, jitter=3):
    jx = x + random.randint(-jitter, jitter)
    jy = y + random.randint(-jitter, jitter)
    move_to(jx, jy)
    time.sleep(random.uniform(0.08, 0.22))
    pyautogui.click()
    time.sleep(random.uniform(0.15, 0.4))


def type_text(text, wpm_range=(180, 260)):
    """Types at a human-ish speed with tiny random pauses. No error injection
    — deliberate typos risk posting broken captions, not worth the realism."""
    for ch in text:
        pyautogui.write(ch)
        cps = random.uniform(*wpm_range) * 5 / 60  # chars/sec approx from wpm
        time.sleep(1 / cps * random.uniform(0.6, 1.4))
    time.sleep(random.uniform(0.2, 0.5))


def key(*keys):
    pyautogui.hotkey(*keys)
    time.sleep(random.uniform(0.2, 0.5))


def wait(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))
