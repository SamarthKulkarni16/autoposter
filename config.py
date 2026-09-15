"""
config.py
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTBOX_DIR = BASE_DIR / "outbox"

# --- Real Chrome, dedicated automation-only profile copy (replaces the old
# Playwright-bundled-Chromium-per-(platform,lang) scheme) -------------------
# All accounts in ACCOUNTS below are already logged in -- copied from the
# desktop's real ~/.config/google-chrome (where they're logged in via the
# regular RDP session Samarth uses) into a SEPARATE, automation-only
# directory: ~/.config/chrome-automation (one-time rsync copy; see
# oracle-vm-setup's setup-automation-chrome-dir.yml). Two things forced this
# split, both learned live rather than anticipated:
#   1. Real Chrome allows only ONE running process per user-data-dir, full
#      stop -- launching straight against the real ~/.config/google-chrome
#      collided with whatever windows the human's own desktop Chrome already
#      had open there ("Target page, context or browser has been closed" /
#      SingletonLock errors)
#   2. Chrome refuses to open a --remote-debugging-port at all on "the
#      default" profile directory as a security measure ("DevTools remote
#      debugging requires a non-default data directory") -- confirmed live,
#      no flag combination gets around it -- which also ruled out attaching
#      via CDP to the real directory even if (1) were solved
# A dedicated copy solves both: it's automation-exclusive (nothing else ever
# opens it, so no collision) and it's non-default (so debugging would work
# too, though this design doesn't need it -- back to a plain
# launch_persistent_context() per job, closed via close_account() before the
# next job starts, same as any other sequential single-process use).
# Real Chrome (not Playwright's bundled Chromium) still matters for the
# non-collision reasons above and because it decodes H.264 natively, fixing
# Pinterest/Facebook's client-side video validation (see git history for the
# old SNAP_CHROMIUM_EXECUTABLE workaround this removed).
#
# NOTE: this copy is a one-time snapshot, not a live sync -- if Samarth logs
# into a NEW platform/lang account for the first time, or an existing login
# expires and needs re-entering, that has to happen once in THIS directory
# too (e.g. open it manually with `google-chrome-stable
# --user-data-dir=~/.config/chrome-automation --profile-directory="Profile
# N"`), not just in the regular desktop Chrome -- the two no longer share
# state.
CHROME_USER_DATA_DIR = os.path.expanduser("~/.config/chrome-automation")

# Playwright's executable_path is passed straight to the OS process launcher,
# not through a shell -- it does NOT do a $PATH lookup the way typing
# "google-chrome-stable" in bash does (confirmed live: "Failed to launch
# chromium because executable doesn't exist at google-chrome-stable"), so
# this needs an actual resolved path. shutil.which() replicates PATH lookup
# in Python; if that comes up empty (e.g. a stripped-down SSH non-interactive
# PATH), fall back to the standard install path for Google's own .deb
# package on Debian/Ubuntu, which is what this VM uses.
CHROME_EXECUTABLE = (
    shutil.which("google-chrome-stable")
    or shutil.which("google-chrome")
    or "/usr/bin/google-chrome-stable"
)

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
ENABLED_PLATFORMS = ["facebook"]

# --- Accounts -------------------------------------------------------------
# One entry per (platform, lang). "chrome_profile" = the real Chrome profile
# directory name on the VM (e.g. "Profile 23") that's already logged into
# this account -- confirmed via a ground-truth scan of
# ~/.config/google-chrome/*/Preferences (see memory). "url" = where the
# account should land, logged in, ready to post. "board" (optional) = the
# Pinterest board name to select for this lang, when several langs share one
# logged-in chrome_profile (see "pinterest" below) instead of each having
# its own. Several (platform, lang) entries can point at the same
# chrome_profile when they're actually the same Google account (e.g.
# pinterest's hi/ar/pt/es all share Profile 23) -- that's expected, not a
# collision, since each job still gets its own dedicated browser window
# and posts are processed sequentially, never in parallel, by main.py.
#
# No "en" entries, for youtube or any platform added below -- English is
# handled outside this automation entirely, across every social platform.
ACCOUNTS = {
    "youtube": {
        "hi": {"chrome_profile": "Profile 23", "email": "samarth.youtube1@gmail.com", "url": "https://studio.youtube.com"},
        "ar": {"chrome_profile": "Profile 12", "email": "samarthkulkarni16s@gmail.com", "url": "https://studio.youtube.com"},
        "pt": {"chrome_profile": "Profile 28", "email": "samarthkulkarni.pt@gmail.com", "url": "https://studio.youtube.com"},
        "es": {"chrome_profile": "Profile 27", "email": "samarthkulkarni.es@gmail.com", "url": "https://studio.youtube.com"},
    },
    # Pinterest: hi/ar/pt/es are NOT four separate logins -- they're four
    # boards ("Hindi"/"Arabic"/"Portuguese"/"Spanish") under one shared
    # account (samarth.youtube1@gmail.com, chrome_profile "Profile 23"), so
    # every lang below points at the SAME chrome_profile. Only "board"
    # differs per lang; platforms/pinterest.py reads ctx["board"] and picks
    # that board when creating each pin. The English Pinterest account
    # (samarth1616s@gmail.com) is a fully separate account and is
    # intentionally NOT configured here at all.
    "pinterest": {
        "hi": {"chrome_profile": "Profile 23", "board": "Hindi", "email": "samarth.youtube1@gmail.com", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "ar": {"chrome_profile": "Profile 23", "board": "Arabic", "email": "samarth.youtube1@gmail.com", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "pt": {"chrome_profile": "Profile 23", "board": "Portuguese", "email": "samarth.youtube1@gmail.com", "url": "https://www.pinterest.com/pin-creation-tool/"},
        "es": {"chrome_profile": "Profile 23", "board": "Spanish", "email": "samarth.youtube1@gmail.com", "url": "https://www.pinterest.com/pin-creation-tool/"},
    },
    # Facebook: same shared-login idea as Pinterest above, but the four
    # langs are four separate PAGES (not a dropdown choice on one shared
    # URL) -- "Samarth Kulkarni HI"/"Arabic"/"Portuguese"/"ES" -- all
    # administered by the one shared personal account (samarth.youtube1@gmail.com,
    # "Profile 23"). So chrome_profile is still the SAME for all four (one
    # login covers all four Pages), but unlike Pinterest, "url" also differs
    # per lang -- each Page has its own distinct URL, and posting as that
    # Page means actually navigating there, not selecting an option within
    # one shared composer. "page" is the Page's display name, kept here for
    # logging/sanity-checks in platforms/facebook.py rather than for
    # navigation.
    "facebook": {
        "hi": {"chrome_profile": "Profile 23", "page": "Samarth Kulkarni HI", "email": "samarth.youtube1@gmail.com", "url": "https://www.facebook.com/profile.php?id=61589758439087"},
        "ar": {"chrome_profile": "Profile 23", "page": "Samarth Kulkarni Arabic", "email": "samarth.youtube1@gmail.com", "url": "https://www.facebook.com/profile.php?id=61589615735525"},
        "pt": {"chrome_profile": "Profile 23", "page": "Samarth Kulkarni Portuguese", "email": "samarth.youtube1@gmail.com", "url": "https://www.facebook.com/profile.php?id=61589630883062"},
        "es": {"chrome_profile": "Profile 23", "page": "Samarth Kulkarni ES", "email": "samarth.youtube1@gmail.com", "url": "https://www.facebook.com/profile.php?id=61589796354178"},
    },
    # Instagram: back to YouTube's pattern, not Pinterest/Facebook's -- four
    # fully separate accounts, one per lang, each its own login (own email,
    # own handle, own chrome_profile), just like youtube above. "handle" is
    # just for logging/sanity-checks (e.g. confirming the right account
    # ended up logged in), not used for navigation.
    "instagram": {
        "hi": {"chrome_profile": "Profile 23", "handle": "@samarthkulkarni_hi", "email": "samarth.youtube1@gmail.com", "url": "https://www.instagram.com/"},
        "ar": {"chrome_profile": "Profile 27", "handle": "@samarthkulkarni.ar", "email": "samarthkulkarni.es@gmail.com", "url": "https://www.instagram.com/"},
        "pt": {"chrome_profile": "Profile 28", "handle": "@samarthkulkarni.pt", "email": "samarthkulkarni.pt@gmail.com", "url": "https://www.instagram.com/"},
        "es": {"chrome_profile": "Profile 12", "handle": "@samarthkulkarni_es", "email": "samarthkulkarni16s@gmail.com", "url": "https://www.instagram.com/"},
    },
    # X (Twitter): same pattern as Instagram, not Pinterest/Facebook -- four
    # fully separate accounts/logins, one per lang, each its own
    # chrome_profile. Note the emails/profiles here overlap with OTHER
    # platforms' (e.g. Profile 27 = samarthkulkarni.es@gmail.com is both
    # Instagram/Arabic's login AND X/Hindi's login) -- that's fine and
    # expected, not a collision (see the ACCOUNTS docstring above).
    "x": {
        "hi": {"chrome_profile": "Profile 27", "handle": "@SamarthK_hi", "email": "samarthkulkarni.es@gmail.com", "url": "https://x.com/"},
        "ar": {"chrome_profile": "Profile 12", "handle": "@SamarthK_Ar", "email": "samarthkulkarni16s@gmail.com", "url": "https://x.com/"},
        "pt": {"chrome_profile": "Profile 28", "handle": "@SamarthK_pt", "email": "samarthkulkarni.pt@gmail.com", "url": "https://x.com/"},
        "es": {"chrome_profile": "Profile 23", "handle": "@SamarthkEs1", "email": "samarth.youtube1@gmail.com", "url": "https://x.com/"},
    },
}
