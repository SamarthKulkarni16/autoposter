# AIDER TASK: Continue debugging the YouTube autoposter upload flow

**Read `docs/CONTINUATION_BRIEFING.md` in this repo first.** It has the full
background, environment, method, and bug history. Do not skip it.

## Your mandate

Fix `platforms/youtube.py` and its supporting modules (`vision.py`,
`human_actions.py`, `engine.py`) until `debug/test_upload_step1.py` runs
cleanly and prints `[SUCCESS]`. You are running in an automatic test loop:
after each edit, `debug/test_upload_step1.py` is re-run automatically and
its full output (including any `[FAIL]` exception and diagnostic prints) is
fed back to you. Keep iterating: diagnose from the output -> edit -> let it
re-run -> repeat, until it succeeds.

## Immediate known blocker (read Section 8 of the briefing for full detail)

The "Create" button click executes without error but the dropdown menu
never opens, so `click_text("Upload videos")` reliably times out. A
diagnostic was added that saves `debug/shots/01c_create_target_marked.png`
with a red circle at the computed OCR click point, and prints the match
coordinates as `[diag] 'Create' OCR match at: (x, y)` before clicking. Look
at that diagnostic output in the test run first. If you are given vision
capability, also inspect the marked screenshot directly.

## Hard safety rule — never automate past this point

`debug/test_upload_step1.py` deliberately stops right after the "Details"
screen is reached and the title is typed — it does NOT click Next, does NOT
set visibility, and does NOT click Publish. **Never modify the test script
to go further, and never modify `platforms/youtube.py` in a way that would
cause a real publish during this automated test loop.** This is the one
irreversible action (a real public video upload) that requires explicit
human sign-off, not automation. Stop and leave a note in
`docs/CONTINUATION_BRIEFING.md` if you believe the flow is ready for that
next stage — do not attempt it yourself.

## Keep the briefing document updated

As you find new bugs, apply fixes, or the blocker changes, update
`docs/CONTINUATION_BRIEFING.md` — especially the bug history and the
"CURRENT STATE" section at the bottom. Commit these updates alongside your
code changes so anyone (human or another agent) can pick this up cold.

## Environment notes specific to this run

- You do not have direct shell/OCR/screenshot access yourself — the test
  script does that. You only see its printed stdout/stderr after each run.
- If a run's output shows a completely black screenshot description or
  `NO_LIVE_SESSION`, that means no one is connected to the VM over RDP —
  this is not a code bug, note it and stop; a human needs to reconnect.
- Commit after every meaningful fix, even ones that don't fully solve it —
  small, frequent commits make it easier to see what was tried.
- Do not push automatically after every commit; that's fine to batch, but
  do push before you'd naturally stop or run low on ideas, so progress
  isn't lost.

## When to stop

Stop and summarize in `docs/CONTINUATION_BRIEFING.md` "CURRENT STATE" if:
- `debug/test_upload_step1.py` prints `[SUCCESS]` (goal reached).
- You've tried several genuinely different hypotheses and are no longer
  making progress (don't just repeat the same fix with minor variations).
- You hit the human-required checkpoint above (testing past Details).
