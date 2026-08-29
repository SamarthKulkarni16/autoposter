Read docs/CONTINUATION_BRIEFING.md in this repo first for full background,
environment, method, and bug history. Then read AIDER_TASK.md and
CLINE_TASK.md for prior handoff context (do not duplicate their setup
instructions, just absorb the task context).

YOUR MANDATE: fix platforms/youtube.py and its supporting modules
(vision.py, human_actions.py, engine.py) until `python3
debug/test_upload_step1.py` runs cleanly and prints [SUCCESS]. Run it
yourself as many times as you need, read its full stdout/stderr including
any [FAIL] exception and the [diag] diagnostic lines, form a hypothesis,
make a targeted edit, re-run, repeat. Keep going autonomously without
stopping to ask for confirmation on routine steps (reading files, running
the test script, editing code, running additional diagnostic commands you
think of yourself, committing).

KNOWN CURRENT BLOCKER (full detail in briefing Section 8 "CURRENT STATE"):
the "Create" button click executes without error but the dropdown menu
never opens, so click_text("Upload videos") reliably times out. A
diagnostic already saves debug/shots/01c_create_target_marked.png with a
red circle at the computed OCR click point, and prints the match
coordinates as "[diag] 'Create' OCR match at: (x, y)" before clicking.
Start by running the test script and reading that diagnostic output. If you
want more direct evidence, you can also write and run your own throwaway
diagnostic scripts (e.g. a raw OCR dump of the screenshot showing every
detected word, its confidence, and its coordinates) — you have full shell
access, use it.

HARD SAFETY RULE — the one thing you must never do: never modify
debug/test_upload_step1.py to click past the "Details" screen, and never
cause platforms/youtube.py to actually click Next/Publish or set
visibility during this session. A real publish to a public YouTube channel
is the one irreversible action here and it requires explicit human
sign-off first, not automation. If you believe the flow is solid enough to
attempt that next stage, stop, write up why in
docs/CONTINUATION_BRIEFING.md, and do not attempt it yourself.

KEEP THE BRIEFING DOC UPDATED: as you find bugs, apply fixes, or the
blocker changes, update docs/CONTINUATION_BRIEFING.md — especially the bug
history section and "CURRENT STATE" at the bottom — and commit those
updates alongside your code changes, so anyone picking this up later
(human or another agent) has an accurate picture.

COMMIT DISCIPLINE: commit after every meaningful fix attempt, even ones
that don't fully solve it — small frequent commits make it easy to see
what was tried and to roll back a bad change. Push periodically so
progress isn't lost if this session ends unexpectedly; you don't need to
push after every single commit, but don't let a long stretch of work sit
unpushed either.

ENVIRONMENT NOTE: if a test run's output shows a black/blank screenshot
description or something like "NO_LIVE_SESSION", that means no one is
connected to the VM over RDP — this is not a code bug. Note it clearly in
your output and in the briefing doc, and stop; a human needs to reconnect
the RDP session before GUI automation can do anything.

WHEN TO STOP: stop and clearly summarize final state in
docs/CONTINUATION_BRIEFING.md's "CURRENT STATE" section if any of:
(a) debug/test_upload_step1.py prints [SUCCESS] — goal reached;
(b) you've tried several genuinely different hypotheses (not just minor
    variations on the same idea) and are no longer making progress;
(c) you hit the human-required checkpoint above.
