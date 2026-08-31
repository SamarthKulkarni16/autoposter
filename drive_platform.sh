#!/bin/bash
# drive_platform.sh <platform> [lang] [--live-video]
#
# Runs the autoposter for ONE platform end-to-end in a clean, bounded,
# reproducible way and surfaces a clear result the caller can act on.
#
# This is the entry point a debugging sub-agent calls in a loop:
#   1. It creates (or reuses) a throwaway outbox job for <platform>/<lang>.
#   2. It scopes ENABLED_PLATFORMS to just <platform>.
#   3. It clears old failure screenshots + log so the only log/screenshot
#      noise is from THIS run.
#   4. It runs `python3 main.py --once` with a hard timeout.
#   5. It prints the resulting state + screenshot list + last log lines.
#
# Exit codes:
#   0  -> post reached "posted" (success). Screenshot/state prints still shown.
#   1  -> post failed (StepFailed/timeout/etc). Diagnostics printed.
#   2  -> hard timeout (run killed) — treat as inconclusive, inspect log.
#   3  -> setup error (missing profile, bad platform, etc).
set -u

PLATFORM=${1:-}
LANG_CODE=${2:-hi}
LIVE_VIDEO=${3:-}
RUN_TIMEOUT="${DRIVE_TIMEOUT:-900}"   # seconds, hard cap on one run attempt

if [ -z "$PLATFORM" ]; then
  echo "[drive] ERROR: usage: drive_platform.sh <platform> [lang] [--live-video]" >&2
  exit 3
fi

cd /home/ubuntu/autoposter || { echo "[drive] ERROR: cd failed" >&2; exit 3; }

echo "[drive] platform=$PLATFORM lang=$LANG_CODE timeout=${RUN_TIMEOUT}s"

# --- 1. preserve current config, set ENABLED_PLATFORMS = [platform] -------
cp config.py config.py.drivebak 2>/dev/null || true
sed -i "s/^ENABLED_PLATFORMS = .*/ENABLED_PLATFORMS = [\"$PLATFORM\"]/" config.py
echo "[drive] ENABLED_PLATFORMS -> $(grep '^ENABLED_PLATFORMS' config.py)"

# --- 2. build the outbox job ----------------------------------------------
JOB="livetest_${PLATFORM}"
mkdir -p "outbox/${JOB}"

if [ "$LIVE_VIDEO" = "--live-video" ]; then
  # Try to reuse an existing real video from the real outbox; else make a throwaway.
  REAL="$(ls outbox/*/hi.mp4 2>/dev/null | grep -v livetest | head -1)"
  if [ -n "$REAL" ]; then
    echo "[drive] reusing real video: $REAL"
    cp "$REAL" "outbox/${JOB}/${LANG_CODE}.mp4"
  fi
fi

if [ ! -f "outbox/${JOB}/${LANG_CODE}.mp4" ]; then
  echo "[drive] generating throwaway ${LANG_CODE}.mp4"
  ffmpeg -f lavfi -i color=c=blue:s=720x1280:d=8 -f lavfi -i anullsrc=r=44100:cl=mono \
    -t 8 -c:v libx264 -profile:v baseline -pix_fmt yuv420p -c:a aac \
    -movflags +faststart -y "outbox/${JOB}/${LANG_CODE}.mp4" -loglevel error
fi

cat > "outbox/${JOB}/meta.json" <<JSON
{
  "platforms": ["$PLATFORM"],
  "title": {"$LANG_CODE": "Autoposter live test - $PLATFORM - DO NOT KEEP"},
  "caption": {"$LANG_CODE": "Live test post, please ignore/delete."},
  "tags": {"$LANG_CODE": ""}
}
JSON
echo "[drive] job ready: outbox/${JOB}"

# --- 3. clear old screenshots + note current log length -------------------
rm -rf failures && mkdir -p failures
LOG_START=$(wc -l < autoposter.log 2>/dev/null || echo 0)

# --- 4. run once -----------------------------------------------------------
echo "[drive] running: python3 main.py --once  (DISPLAY=${DISPLAY:-:10})"
export DISPLAY="${DISPLAY:-:10}"
export PYTHONUNBUFFERED=1

timeout "$RUN_TIMEOUT" python3 main.py --once
RC=$?

if [ $RC -eq 124 ]; then
  echo "[drive] HARD TIMEOUT after ${RUN_TIMEOUT}s (exit 124) — run killed, treat as inconclusive"
  TARGET_RC=2
else
  TARGET_RC=$RC
fi

# --- 5. restore config -----------------------------------------------------
mv config.py.drivebak config.py 2>/dev/null || true
echo "[drive] restored config.py (ENABLED_PLATFORMS -> $(grep '^ENABLED_PLATFORMS' config.py))"

# --- 6. report -------------------------------------------------------------
echo ""
echo "=== STATE ==="
python3 -c "
import json
try:
    d = json.load(open('state.json'))
    j = d.get('${JOB}', {})
    if j:
        pj = j.get('$PLATFORM', {})
        lj = pj.get('$LANG_CODE', {})
        print('status:', lj.get('status'))
        print('updated:', lj.get('updated'))
        print('note:', (lj.get('note') or '')[:400])
    else:
        print('(no state entry)')
except Exception as e:
    print('state read error:', e)
"

echo ""
echo "=== FAILURE SCREENSHOTS ==="
ls -la failures/ 2>/dev/null || echo "none"

echo ""
echo "=== NEW LOG LINES (from line $((LOG_START+1))) ==="
tail -n +$((LOG_START+1)) autoposter.log 2>/dev/null | tail -n 120

echo ""
echo "[drive] exit=$TARGET_RC"
exit "$TARGET_RC"
