"""
config.py
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTBOX_DIR = BASE_DIR / "outbox"
PROFILES_DIR = BASE_DIR / "profiles"
PROFILES_DIR.mkdir(exist_ok=True)

# Playwright's persistent-context Firefox reads/writes a normal Firefox
# profile directory (same on-disk format as real Firefox), so accounts
# logged in once under profiles/<name>/ (or an existing real Firefox
# profile via "profile_path") stay logged in on every future run — no
# browser binary path needed anymore, Playwright ships its own Firefox.
HEADLESS = False          # Studio's upload UI behaves more reliably headed
LOAD_WAIT_SEC = 3         # short settle pause after navigation, before interacting

POLL_INTERVAL_SEC = 120
MIN_GAP_BETWEEN_POSTS = (180, 480)   # seconds, randomized gap between posts
ACTIVE_HOURS = (9, 23)

LANGS = ["en", "hi", "ar", "pt", "es"]

# Which platforms are wired up in platforms/*.py. Add as you add each one.
ENABLED_PLATFORMS = ["youtube"]

# --- Accounts -------------------------------------------------------------
# One entry per (platform, lang). "profile" = folder name under profiles/,
# created automatically the first time you run setup_profile.py for it.
# "profile_path" = an absolute path to an existing Firefox profile to reuse
# instead (e.g. one already logged in outside this tool). "url" = where the
# account should land, logged in, ready to post.
ACCOUNTS = {
    "youtube": {
        "en": {"profile": "youtube_en", "url": "https://studio.youtube.com", "profile_path": "/home/ubuntu/.config/mozilla/firefox/g7dhshsu.default-release"},
        "hi": {"profile": "youtube_hi", "url": "https://studio.youtube.com"},
        "ar": {"profile": "youtube_ar", "url": "https://studio.youtube.com"},
        "pt": {"profile": "youtube_pt", "url": "https://studio.youtube.com"},
        "es": {"profile": "youtube_es", "url": "https://studio.youtube.com"},
    },
    # "instagram": {
    #     "en": {"profile": "instagram_en", "url": "https://www.instagram.com"},
    #     ...
    # },
}
