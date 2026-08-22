# CLINE TASK: Continue debugging the YouTube autoposter upload flow

**Read `docs/CONTINUATION_BRIEFING.md` in this repo first — it has the full
background, environment, method, and bug history. Do not skip it; it will
save you hours of re-discovering things already solved.**

## Your mandate

Keep debugging and fixing `platforms/youtube.py` (via the safe test harness
`debug/test_upload_step1.py`) until it reliably reaches the "Details" screen
and prints `[SUCCESS]`. Work autonomously — don't stop to ask permission for
routine steps (writing workflow files, pushing commits, triggering test runs,
reading logs/screenshots, patching code, re-running). Keep going in a loop:
diagnose → fix → push → re-run → look at the screenshots → repeat, until it
either succeeds or you hit something you genuinely cannot resolve yourself
(see "When to actually stop and ask" below).

## Hard rule — the one thing you must NOT automate

**Never let any script click "Next" past the Details screen, or click
"Publish," or otherwise complete an irreversible action** (this would really
post a video publicly). `debug/test_upload_step1.py` is deliberately
non-destructive and stops before that point — keep it that way. If you reach
the point where the Details-screen flow is solid and you want to test the
rest of the flow (description field, visibility settings, Publish), stop and
explicitly tell the human what you want to test and why, and wait for their
go-ahead before writing or running anything that could actually publish.
This is the only checkpoint that requires a human. Everything else, keep
moving on your own.

## How to reach the VM

You are very likely running with normal, unrestricted network access (unlike
the AI that did the earlier sessions, which was sandboxed to github.com/
api.github.com only). Check first:

1. **Try direct SSH** to `ubuntu@140.238.229.141` if you have (or the human
   gives you) the private key. This is simpler and faster than the relay
   method below — no need for the GitHub Actions round-trip if you can just
   SSH straight in.
2. **If direct SSH isn't available**, fall back to the GitHub Actions relay
   method fully documented in `docs/CONTINUATION_BRIEFING.md` Section 4 —
   this is proven working and is what all prior fixes were made through.
   The relevant workflow is
   `oracle-vm-setup/.github/workflows/test-youtube-upload.yml`.

Either way, you still need a live GNOME desktop session on the VM to test
against (the human connects over RDP). If a screenshot comes back solid
black, that means no one is connected — ask the human to connect, then
continue once they confirm.

## GitHub PAT

Ask the human for a current PAT if you don't have one (the one used in prior
sessions should be treated as expired/rotated by now — don't assume it still
works). Scopes needed: `repo`, `workflow`.

## Immediate next step (exactly where the last session left off)

The last fix pushed (commit `6664c62` on `autoposter` main) added a
diagnostic to `debug/test_upload_step1.py`: right before clicking "Create,"
it now finds the OCR match location and saves a screenshot
(`01c_create_target_marked.png`) with a red circle drawn exactly where it's
about to click. **This diagnostic run has NOT been executed yet** — that's
your first action. Trigger the test, then actually look at
`01c_create_target_marked.png`:

- If the red circle is clearly ON the visible "Create" button → the click
  target is correct, and the bug is something else (button not responding to
  the click event itself, a timing issue, or the click landing but the
  dropdown closing before the next screenshot — investigate
  `human_actions.py`'s `click()` next, maybe try a slower/more deliberate
  click sequence, or add an immediate zero-delay screenshot right after).
- If the red circle is OFF the button (even slightly) → there's a genuine
  coordinate calculation bug in `vision.py`'s `find_text()` (check the /2
  upscale-undo math, or whether `pyautogui.screenshot()` and
  `pyautogui.click()` disagree about coordinate space — unlikely but
  possible on some X11/xrdp configs).

Full context for this specific investigation is in
`docs/CONTINUATION_BRIEFING.md` Section 8 ("CURRENT STATE").

## Keep the briefing document updated

As you make progress — new bugs found, fixes applied, current blocker
changes — **update `docs/CONTINUATION_BRIEFING.md` to reflect it**,
especially Section 5 (bug history) and Section 8 (current state). Commit
those updates alongside your code changes. This document is what lets
*anyone* (human or AI) pick this up cold if you also run out of
context/credits — keep it accurate so the next agent doesn't waste time
either.
