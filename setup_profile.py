"""
setup_profile.py — run this ONCE per account to log in by hand.
After this, main.py can open that account any time without logging in
again — the login is saved inside its own persistent Chrome user-data-dir
(cookies, local storage, everything), the same way a normal Chrome profile
folder works.

Usage:
    python3 setup_profile.py youtube en

Opens a real, visible Google Chrome window (via Playwright's "chrome"
channel — the actual installed browser, not Playwright's bundled Chromium)
pointed at the account's start URL. Log in by hand (including any 2FA/OTP),
then come back to this terminal and press Enter — the profile directory is
created automatically the first time.

Chrome, not Firefox: Google's sign-in flow blocks Playwright's patched
Firefox build far more often than real Chrome running with
--disable-blink-features=AutomationControlled (see engine.py for detail).
Requires Google Chrome to be installed on this machine (install.sh does
this) — Playwright's "chrome" channel drives the real browser, it doesn't
ship its own copy of it the way it does for Chromium/Firefox/WebKit.
"""

import sys
import config
from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 setup_profile.py <platform> <lang>")
        print("Example: python3 setup_profile.py youtube en")
        sys.exit(1)

    platform, lang = sys.argv[1], sys.argv[2]
    try:
        account = config.ACCOUNTS[platform][lang]
    except KeyError:
        print(f"No account configured for {platform}/{lang} in config.py")
        sys.exit(1)

    if "profile_path" in account:
        user_data_dir = account["profile_path"]
    else:
        user_data_dir = str(config.PROFILES_DIR / account["profile"])

    print(f"Opening Chrome for {platform}/{lang} -> {account['url']}")
    print(f"Profile directory: {user_data_dir}")
    print("Log in fully (2FA/OTP included), then come back here and press Enter.")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(account["url"], wait_until="domcontentloaded")

        input("Press Enter once you're logged in and ready... ")
        context.close()

    print(f"Saved. Login for {platform}/{lang} is now stored in {user_data_dir}")


if __name__ == "__main__":
    main()
