"""
setup_profile.py — run this ONCE per account to log in by hand.
After this, the script can open that account any time without logging in
again — the login is saved inside its own Firefox profile.

Usage:
    python3 setup_profile.py youtube en

Registers a dedicated Firefox profile for that account (if not already
registered), opens it, and you log in by hand (including any 2FA/OTP).
When done, come back to this terminal and press Enter.
"""

import sys
import subprocess
import config


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

    profile_name = account["profile"]
    profile_dir = config.PROFILES_DIR / profile_name

    if not profile_dir.exists():
        print(f"Registering new Firefox profile: {profile_name}")
        subprocess.run([
            config.BROWSER_BIN, "-CreateProfile",
            f"{profile_name} {profile_dir}"
        ], check=True)

    print(f"Opening Firefox for {platform}/{lang} → {account['url']}")
    print("Log in fully (2FA/OTP included), then come back here and press Enter.")

    proc = subprocess.Popen([
        config.BROWSER_BIN,
        "-no-remote",
        "-P", profile_name,
        account["url"],
    ])

    input("Press Enter once you're logged in and ready... ")
    proc.terminate()
    print(f"Saved. Login for {profile_name} is now stored in {profile_dir}")


if __name__ == "__main__":
    main()

