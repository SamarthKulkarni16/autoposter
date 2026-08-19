"""
login_all_accounts.py — walks you through every configured account, one at a
time, so you don't have to type separate setup_profile.py commands.

Usage:
    python3 login_all_accounts.py
"""

import config
import subprocess
import sys

def main():
    accounts = []
    for platform, langs in config.ACCOUNTS.items():
        for lang in langs:
            accounts.append((platform, lang))

    print(f"{len(accounts)} account(s) to log into. Doing them one at a time.\n")

    for i, (platform, lang) in enumerate(accounts, 1):
        print(f"\n--- Account {i}/{len(accounts)}: {platform} / {lang} ---")
        answer = input("Press Enter to open Firefox for this account (or type 'skip' to skip it): ").strip().lower()
        if answer == "skip":
            print("Skipped.")
            continue
        subprocess.run([sys.executable, "setup_profile.py", platform, lang])

    print("\nAll done. Run: python3 main.py --once")

if __name__ == "__main__":
    main()
