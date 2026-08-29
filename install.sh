#!/bin/bash
# install.sh — run this once on the Oracle VM after unzipping autoposter.
# Usage: cd autoposter && bash install.sh
set -e

echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "Installing real Google Chrome (Playwright's 'chrome' channel) + OS deps..."
python3 -m playwright install --with-deps chrome

echo ""
echo "Done. Next step — log in to each account (type these one at a time):"
echo "  python3 setup_profile.py youtube en"
echo "  python3 setup_profile.py youtube hi"
echo "  python3 setup_profile.py youtube ar"
echo "  python3 setup_profile.py youtube pt"
echo "  python3 setup_profile.py youtube es"
