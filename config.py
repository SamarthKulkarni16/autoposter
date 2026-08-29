"""
config.py
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTBOX_DIR = BASE_DIR / "outbox"
PROFILES_DIR = BASE_DIR / "profiles"
PROFILES_DIR.mkdir(exist_ok=True)

# Playwright's persistent-context Chrome (real installed Google Chrome, via
# the "chrome" channel) reads/writes a normal Chrome user-data-dir, so
# accounts logged in once under profiles/<name>/ stay logged in on every
# future run. Chrome, not Firefox: Google's own sign-in flow blocks
# Playwright's patched Firefox build far more often than real Chrome
# (see engine.open_account docstring).
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
# "profile_path" = an absolute path to an existing Chrome user-data-dir to reuse
# instead (e.g. one already logged in outside this tool). "url" = where the
# account should land, logged in, ready to post.
ACCOUNTS = {
    "youtube": {
        # NOTE: previously used "profile_path" to reuse the VM's real Firefox
        # profile directly, but Playwright bundles its own Firefox build,
        # and that real profile had been touched by a newer system Firefox
        # than Playwright's -- Firefox refuses to open a profile stamped by
        # a newer version ("This profile was last used with a newer version
        # of this application. Please create a new profile."). We also then
        # hit Google actively blocking Playwright's Firefox at sign-in
        # ("This browser or app may not be secure"), so this account now
        # uses a fresh Chrome profile like every other account; log in once
        # with: python3 setup_profile.py youtube en
        "en": {"profile": "youtube_en", "url": "https://studio.youtube.com"},
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
