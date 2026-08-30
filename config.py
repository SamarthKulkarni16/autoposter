"""
config.py
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTBOX_DIR = BASE_DIR / "outbox"
PROFILES_DIR = BASE_DIR / "profiles"
PROFILES_DIR.mkdir(exist_ok=True)

# Playwright's persistent-context Chromium (its own bundled build --
# real Chrome has no official ARM64 Linux build, which this VM is) reads/
# writes a normal Chromium user-data-dir, so accounts logged in once under
# profiles/<name>/ stay logged in on every future run. Chromium, not
# Firefox: Google's own sign-in flow blocks Playwright's patched Firefox
# build far more often (see engine.open_account docstring).
HEADLESS = False          # Studio's upload UI behaves more reliably headed
LOAD_WAIT_SEC = 3         # short settle pause after navigation, before interacting

POLL_INTERVAL_SEC = 120
MIN_GAP_BETWEEN_POSTS = (180, 480)   # seconds, randomized gap between posts

# Languages main.py will build jobs for and post automatically. No "en"
# here or anywhere in ACCOUNTS below -- English channels are deliberately
# not part of this automation at all, for any platform. Add new platforms/
# languages to ACCOUNTS with the same non-English-only convention.
LANGS = ["hi", "ar", "pt", "es"]

# Which platforms are wired up in platforms/*.py. Add as you add each one.
# NOTE: "pinterest", "facebook", "instagram", and "x" are deliberately NOT in
# this list yet -- their ACCOUNTS entries below exist so
# setup_all_profiles.py can log accounts in, but pinterest.py/facebook.py/
# instagram.py are untested first drafts (see their own docstrings) and
# x.py doesn't exist yet at all. Add each platform here once its module
# exists and has been tested.
ENABLED_PLATFORMS = ["youtube"]

# --- Accounts -------------------------------------------------------------
# One entry per (platform, lang). "profile" = folder name under profiles/,
# created automatically the first time you run setup_profile.py for it.
# "profile_path" = an absolute path to an existing Chromium user-data-dir to reuse
# instead (e.g. one already logged in outside this tool). "url" = where the
# account should land, logged in, ready to post. "board" (optional) = the
# Pinterest board name to select for this lang, when several langs share one
# logged-in "profile" (see "pinterest" below) instead of each having its own.
#
# No "en" entries, for youtube or any platform added below -- English is
# handled outside this automation entirely, across every social platform.
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
        # uses a fresh Chromium profile like every other account.
        "hi": {"profile": "youtube_hi", "url": "https://studio.youtube.com"},
        "ar": {"profile": "youtube_ar", "url": "https://studio.youtube.com"},
        "pt": {"profile": "youtube_pt", "url": "https://studio.youtube.com"},
        "es": {"profile": "youtube_es", "url": "https://studio.youtube.com"},
    },
    # Pinterest: unlike YouTube, hi/ar/pt/es are NOT four separate logins --
    # they're four boards ("Hindi"/"Arabic"/"Portuguese"/"Spanish") under one
    # shared account (samarth.youtube1@gmail.com), so every lang below points
    # at the SAME "profile" folder (one login covers all four -- logging into
    # "pinterest"/"hi" via setup_profile.py/setup_all_profiles.py also logs in
    # "ar", "pt", and "es", since it's literally the same Chromium profile
    # dir/session). Only "board" differs per lang; platforms/pinterest.py
    # (not written yet) is expected to read ctx["board"] and pick that board
    # when creating each pin. The English Pinterest account
    # (samarth1616s@gmail.com) is a fully separate account and is
    # intentionally NOT configured here at all.
    "pinterest": {
        "hi": {"profile": "pinterest_shared", "board": "Hindi", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "ar": {"profile": "pinterest_shared", "board": "Arabic", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "pt": {"profile": "pinterest_shared", "board": "Portuguese", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "es": {"profile": "pinterest_shared", "board": "Spanish", "url": "https://www.pinterest.com/pin-creation-tool/"},
    },
    # Facebook: same shared-login idea as Pinterest above, but the four
    # langs are four separate PAGES (not a dropdown choice on one shared
    # URL) -- "Samarth Kulkarni HI"/"Arabic"/"Portuguese"/"ES" -- all
    # administered by the one shared personal account
    # (samarth.youtube1@gmail.com). So "profile" is still the SAME shared
    # folder for all four (one login covers all four Pages), but unlike
    # Pinterest, "url" also differs per lang -- each Page has its own
    # distinct URL, and posting as that Page means actually navigating
    # there, not selecting an option within one shared composer. "page" is
    # the Page's display name, kept here for logging/sanity-checks in
    # platforms/facebook.py (not written yet) rather than for navigation.
    "facebook": {
        "hi": {"profile": "facebook_shared", "page": "Samarth Kulkarni HI", "url": "https://www.facebook.com/profile.php?id=61589758439087"},
        "ar": {"profile": "facebook_shared", "page": "Samarth Kulkarni Arabic", "url": "https://www.facebook.com/profile.php?id=61589615735525"},
        "pt": {"profile": "facebook_shared", "page": "Samarth Kulkarni Portuguese", "url": "https://www.facebook.com/profile.php?id=61589630883062"},
        "es": {"profile": "facebook_shared", "page": "Samarth Kulkarni ES", "url": "https://www.facebook.com/profile.php?id=61589796354178"},
    },
    # Instagram: back to YouTube's pattern, not Pinterest/Facebook's -- four
    # fully separate accounts, one per lang, each its own login (own email,
    # own handle), so each gets its own "profile" folder just like youtube
    # above. "handle" is just for logging/sanity-checks (e.g. confirming the
    # right account ended up logged in), not used for navigation.
    "instagram": {
        "hi": {"profile": "instagram_hi", "handle": "@samarthkulkarni_hi", "url": "https://www.instagram.com/"},
        "ar": {"profile": "instagram_ar", "handle": "@samarthkulkarni.ar", "url": "https://www.instagram.com/"},
        "pt": {"profile": "instagram_pt", "handle": "@samarthkulkarni.pt", "url": "https://www.instagram.com/"},
        "es": {"profile": "instagram_es", "handle": "@samarthkulkarni_es", "url": "https://www.instagram.com/"},
    },
    # X (Twitter): same pattern as Instagram, not Pinterest/Facebook -- four
    # fully separate accounts/logins, one per lang, each its own "profile"
    # folder. Note the emails here overlap with OTHER platforms' emails
    # above (e.g. samarthkulkarni.es@gmail.com is Instagram/Arabic's login
    # but X/Hindi's login) -- that's fine, each (platform, lang) pair still
    # gets its own separate Chromium profile dir, so there's no collision.
    "x": {
        "hi": {"profile": "x_hi", "handle": "@SamarthK_hi", "url": "https://x.com/"},
        "ar": {"profile": "x_ar", "handle": "@SamarthK_Ar", "url": "https://x.com/"},
        "pt": {"profile": "x_pt", "handle": "@SamarthK_pt", "url": "https://x.com/"},
        "es": {"profile": "x_es", "handle": "@SamarthkEs1", "url": "https://x.com/"},
    },
}
