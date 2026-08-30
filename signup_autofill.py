"""
signup_autofill.py — opens a fresh account's signup page in its OWN
persistent profile and auto-types the email address that's supposed to go
with that (platform, lang) pair, reading it from config.ACCOUNTS[...]["email"].
This exists specifically so four near-identical sign-up flows back-to-back
don't end up with the wrong email on the wrong language's account, the way
happened once before doing this by hand/copy-paste.

Everything AFTER the email field -- username, password, birthday, phone
number, OTP/email verification, captchas, all of it -- is still yours to do
by hand, same as setup_profile.py/setup_all_profiles.py already require for
login. This script never submits the form and never touches a password
field; it only locates the email input and types into it.

Usage:
    python3 signup_autofill.py instagram          # all langs in config.LANGS
    python3 signup_autofill.py instagram hi ar    # just these langs
    python3 signup_autofill.py x
    python3 signup_autofill.py youtube            # will refuse -- see note below

NOTE: only platforms where config.ACCOUNTS[...][lang] actually has an
"email" key can run here -- youtube's entries don't have one yet (those
four Google-account emails were never given), so `python3
signup_autofill.py youtube` will list what's missing and stop rather than
guess. Add "email" to each youtube lang entry in config.py once you have
them, the same way pinterest/facebook/instagram/x already do.

Pinterest and Facebook are deliberately NOT in SIGNUP_URLS below -- both use
one EXISTING shared account (boards/Pages under it), not four new per-lang
signups, so there's nothing to auto-fill an email into for them.
"""

import sys

import config
import engine
from playwright.sync_api import sync_playwright

# Only platforms where each lang is actually a brand-new separate account to
# sign up for. Add an entry here (and give every lang an "email" in
# config.py) if another platform ever needs this too.
SIGNUP_URLS = {
    "instagram": "https://www.instagram.com/accounts/emailsignup/",
    "x": "https://x.com/i/flow/signup",
    "youtube": "https://accounts.google.com/signup",
}

# Tried in order; first one found on the page wins. Covers the common cases
# without needing a platform-specific selector for each site.
EMAIL_FIELD_CANDIDATES = [
    {"role": "textbox", "name": "Email"},
    {"role": "textbox", "name": "Mobile number or email"},
    {"role": "textbox", "name": "email"},
]


def _profile_dir(account):
    if "profile_path" in account:
        return account["profile_path"]
    return str(config.PROFILES_DIR / account["profile"])


def _type_email(page, email):
    for candidate in EMAIL_FIELD_CANDIDATES:
        try:
            field = engine.locate(page, role=candidate["role"], name=candidate["name"],
                                   exact=False, timeout=4000)
        except engine.StepFailed:
            continue
        engine.select_all_and_type(page, field, email)
        return True
    return False


def signup_one(platform, lang, account, signup_url):
    email = account.get("email")
    if not email:
        print(f"Skipping {platform}/{lang}: no \"email\" set for it in config.py's ACCOUNTS.")
        return False

    user_data_dir = _profile_dir(account)
    print(f"\n{'=' * 60}")
    print(f"  {platform}/{lang}  ->  {email}")
    print(f"{'=' * 60}")
    print(f"Profile directory: {user_data_dir}")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport=None,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(signup_url, wait_until="domcontentloaded")

        if _type_email(page, email):
            print(f"Typed {email} into the email field. Everything else (username, password, "
                  f"birthday, phone, verification) is yours from here.")
        else:
            print(f"Couldn't find an email field automatically on this page -- "
                  f"type {email} in yourself, carefully: this is the {lang} account.")

        input(f"Press Enter once {platform}/{lang} ({email}) is fully signed up... ")
        context.close()

    print(f"Done. Session for {platform}/{lang} saved in {user_data_dir}")
    return True


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 signup_autofill.py <platform> [lang ...]")
        print(f"Known signup pages: {', '.join(SIGNUP_URLS)}")
        sys.exit(1)

    platform = args[0]
    requested_langs = args[1:] if len(args) > 1 else config.LANGS

    if platform not in SIGNUP_URLS:
        print(f"No known signup URL for '{platform}'. Known: {', '.join(SIGNUP_URLS)}")
        print("(pinterest/facebook aren't here on purpose -- both reuse one existing shared "
              "account, so there's no new per-lang signup to autofill.)")
        sys.exit(1)

    if platform not in config.ACCOUNTS:
        print(f"No accounts configured for platform '{platform}' in config.py")
        sys.exit(1)

    signup_url = SIGNUP_URLS[platform]
    done = 0
    for lang in requested_langs:
        account = config.ACCOUNTS[platform].get(lang)
        if account is None:
            print(f"Skipping {platform}/{lang}: no account entry in config.py")
            continue
        if signup_one(platform, lang, account, signup_url):
            done += 1

    print(f"\n{done} of {len(requested_langs)} requested account(s) processed.")


if __name__ == "__main__":
    main()
