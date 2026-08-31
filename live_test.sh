#!/bin/bash
set -e
PLATFORM=$1
LANG=${2:-hi}

if [ -z "$PLATFORM" ]; then
  echo "Usage: ./live_test.sh <platform> [lang]"
  exit 1
fi

echo "=== Backing up config.py ==="
cp config.py config.py.bak

echo "=== Scoping ENABLED_PLATFORMS to [$PLATFORM] ==="
sed -i "s/^ENABLED_PLATFORMS = .*/ENABLED_PLATFORMS = [\"$PLATFORM\"]/" config.py
grep "^ENABLED_PLATFORMS" config.py

echo "=== Creating a throwaway 5s test video for $PLATFORM/$LANG ==="
mkdir -p outbox/livetest_${PLATFORM}
ffmpeg -f lavfi -i color=c=blue:s=720x1280:d=5 -f lavfi -i anullsrc=r=44100:cl=mono \
  -t 5 -c:v libx264 -profile:v baseline -pix_fmt yuv420p -c:a aac -movflags +faststart -y outbox/livetest_${PLATFORM}/${LANG}.mp4 -loglevel error

cat > outbox/livetest_${PLATFORM}/meta.json << JSON
{
  "platforms": ["$PLATFORM"],
  "title": {"$LANG": "Autoposter live test - $PLATFORM - DO NOT KEEP"},
  "caption": {"$LANG": "Live test post, please ignore/delete."},
  "tags": {"$LANG": ""}
}
JSON

echo "=== Clearing old failure screenshots ==="
rm -rf failures && mkdir -p failures

echo "=== Running: python3 main.py --once ==="
python3 main.py --once || true

echo "=== Restoring config.py ==="
mv config.py.bak config.py

echo ""
echo "=== STATE for this job ==="
python3 -c "
import json
d = json.load(open('state.json'))
print(json.dumps(d.get('livetest_${PLATFORM}', {}), indent=2))
" 2>/dev/null || echo "(state.json not found yet)"

echo ""
echo "=== FAILURE SCREENSHOTS (if any) ==="
ls -la failures/ 2>/dev/null || echo "None — good sign"

echo ""
echo "=== Last 30 log lines ==="
tail -n 30 autoposter.log
