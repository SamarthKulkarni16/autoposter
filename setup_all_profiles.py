"""
setup_all_profiles.py — runs setup_profile.py's login flow back-to-back for
every account of a platform that doesn't have a saved profile yet, instead
of running `python3 setup_profile.py <platform> <lang>` by hand once per
language.

What this automates: opening each account's browser window in turn,
detecting which accounts already have a saved login (skips those), and
moving on to the next one as soon as you press Enter.

What this does NOT automate, on purpose: typing your Google username/
password, or handling 2FA/OTP. Google actively fingerprints and blocks
sign-in flows it detects as scripted, and entering real account credentials
programmatically isn't something to automate here anyway -- you log into
each account by hand, same as setup_profile.py always required. This just
removes the need to re-invoke the command and re-read the instructions for
every remaining language.

Usage:
    python3 setup_all_profiles.py                 # platform=youtube, all LANGS in config.py
    python3 setup_all_profiles.py youtube          # explicit platform
    python3 setup_all_profiles.py youtube hi ar    # only specific langs
    python3 setup_all_profiles.py youtube --force  # re-login even if a profile dir already exists
"""

import sys
from pathlib import Path

import config
from playwright.sync_api import sync_playwright


def _profile_dir(account):
    if "profile_path" in account:
        return Path(account["profile_path"])
    return config.PROFILES_DIR / account["profile"]


def _already_logged_in(account):
    """
    Heuristic: a persistent Chromium user-data-dir that's actually been
    through a login has a non-trivial "Default" profile subfolder (cookies,
    local storage db, etc.) -- an empty/missing dir means setup_profile.py
    was never run (or never got to "press Enter") for this account.
    """
    profile_dir = _profile_dir(account)
    default_subdir = profile_dir / "Default"
    return profile_dir.exists() and default_subdir.exists()


def login_one(platform, lang, account):
    print(f"\n{'=' * 60}")
    print(f"  {platform}/{lang}  ->  {account['url']}")
    print(f"{'=' * 60}")
    user_data_dir = str(_profile_dir(account))
    print(f"Profile directory: {user_data_dir}")
    print("A browser window is opening. Log in fully (2FA/OTP included),")
    print("then come back here and press Enter to move to the next account.")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport=None,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(account["url"], wait_until="domcontentloaded")

        input(f"Press Enter once {platform}/{lang} is logged in and ready... ")
        context.close()

    print(f"Saved. Login for {platform}/{lang} is now stored in {user_data_dir}")


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]

    platform = args[0] if args else "youtube"
    requested_langs = args[1:] if len(args) > 1 else config.LANGS

    if platform not in config.ACCOUNTS:
        print(f"No accounts configured for platform '{platform}' in config.py")
        sys.exit(1)

    todo = []
    skipped = []
    for lang in requested_langs:
        account = config.ACCOUNTS[platform].get(lang)
        if account is None:
            print(f"Skipping {platform}/{lang}: no account entry in config.py")
            continue
        if not force and _already_logged_in(account):
            skipped.append(lang)
        else:
            todo.append((lang, account))

    if skipped:
        print(f"Already logged in, skipping (use --force to redo): {', '.join(skipped)}")

    if not todo:
        print("Nothing to do -- every requested account already has a saved login.")
        return

    print(f"Will log in, one at a time: {', '.join(lang for lang, _ in todo)}")

    for lang, account in todo:
        login_one(platform, lang, account)

    print(f"\nAll done. Logged in this run: {', '.join(lang for lang, _ in todo)}")


if __name__ == "__main__":
    main()
