"""
signup_autofill.py — opens an account's LOGIN page in its own persistent
profile and auto-types the email/identifier that's supposed to go with that
(platform, lang) pair, reading it from config.ACCOUNTS[...]["email"]. Exists
specifically so several near-identical login flows back-to-back don't end up
with the wrong email on the wrong language's account.

CORRECTED (was pointed at SIGNUP pages, wrong for accounts that already
exist): originally used platform signup URLs (accounts.google.com/signup,
instagram.com/accounts/emailsignup/, x.com/i/flow/signup), which dumped
straight into "create a brand-new account" wizards instead of a sign-in
form -- confirmed by real symptoms: YouTube landed on Google's "Create your
account" page, Instagram landed on a "Get Started" onboarding screen instead
of Log In, and X's signup wizard's "Continue" button wouldn't enable (it
needs name/birthday/etc. filled too, not just email, before it unlocks --
a login flow only needs the identifier). Since the handles for Instagram/X
were already known before any of this ran, these are treated as EXISTING
accounts that need signing INTO, not created. Now: youtube and instagram
navigate to their normal app URL (config.ACCOUNTS[...]["url"]) -- both
auto-redirect to (or directly show) a proper sign-in form when logged
out -- and x gets an explicit login-flow URL, since x.com/ logged-out is
just landing-page buttons with no field to type into yet.

Everything AFTER the identifier field -- password, 2FA/OTP, "is this you"
checks, all of it -- is still yours to do by hand, same as
setup_profile.py/setup_all_profiles.py already require. This script never
touches a password field and never submits the form for you.

Usage:
    python3 signup_autofill.py instagram          # all langs in config.LANGS
    python3 signup_autofill.py instagram hi ar    # just these langs
    python3 signup_autofill.py x
    python3 signup_autofill.py youtube

Pinterest and Facebook are deliberately NOT here -- both reuse one existing
shared account (boards/Pages under it), so setup_all_profiles.py (not this
script) is what logs those in.
"""

import sys

import config
import engine
from playwright.sync_api import sync_playwright

# Where to navigate for the LOGIN form. Default is the platform's own app
# URL (config.ACCOUNTS[...]["url"]) -- for youtube and instagram, visiting
# that while logged out lands you on (or redirects to) a real sign-in form.
# x.com/ logged-out is just landing-page buttons with nothing to type into,
# so it needs an explicit login-flow URL instead.
LOGIN_URL_OVERRIDES = {
    "x": "https://x.com/i/flow/login",
}

SUPPORTED_PLATFORMS = ("youtube", "instagram", "x")

# Tried in order; first one found on the page wins. Named per-platform since
# each site's identifier field has a different accessible name.
EMAIL_FIELD_CANDIDATES = [
    {"role": "textbox", "name": "Email or phone"},                              # Google
    {"role": "textbox", "name": "Phone number, username, or email address"},    # Instagram
    {"role": "textbox", "name": "Phone, email, or username"},                   # X
    {"role": "textbox", "name": "Email"},
    {"role": "textbox", "name": "email"},
]


def _profile_dir(account):
    if "profile_path" in account:
        return account["profile_path"]
    return str(config.PROFILES_DIR / account["profile"])


def _login_url(platform, account):
    return LOGIN_URL_OVERRIDES.get(platform, account["url"])


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


def login_one(platform, lang, account):
    email = account.get("email")
    if not email:
        print(f"Skipping {platform}/{lang}: no \"email\" set for it in config.py's ACCOUNTS.")
        return False

    login_url = _login_url(platform, account)
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
        page.goto(login_url, wait_until="domcontentloaded")

        if _type_email(page, email):
            print(f"Typed {email} into the identifier field. Password/2FA/verification "
                  f"is yours from here.")
        else:
            print(f"Couldn't find an identifier field automatically on this page -- "
                  f"type {email} in yourself, carefully: this is the {lang} account.")

        input(f"Press Enter once {platform}/{lang} ({email}) is fully logged in... ")
        context.close()

    print(f"Done. Session for {platform}/{lang} saved in {user_data_dir}")
    return True


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 signup_autofill.py <platform> [lang ...]")
        print(f"Supported: {', '.join(SUPPORTED_PLATFORMS)}")
        sys.exit(1)

    platform = args[0]
    requested_langs = args[1:] if len(args) > 1 else config.LANGS

    if platform not in SUPPORTED_PLATFORMS:
        print(f"'{platform}' isn't handled here. Supported: {', '.join(SUPPORTED_PLATFORMS)}")
        print("(pinterest/facebook aren't here on purpose -- both reuse one existing shared "
              "account; use setup_all_profiles.py for those instead.)")
        sys.exit(1)

    if platform not in config.ACCOUNTS:
        print(f"No accounts configured for platform '{platform}' in config.py")
        sys.exit(1)

    done = 0
    for lang in requested_langs:
        account = config.ACCOUNTS[platform].get(lang)
        if account is None:
            print(f"Skipping {platform}/{lang}: no account entry in config.py")
            continue
        if login_one(platform, lang, account):
            done += 1

    print(f"\n{done} of {len(requested_langs)} requested account(s) processed.")


if __name__ == "__main__":
    main()
