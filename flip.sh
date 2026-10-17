#!/usr/bin/env bash
# Publish local/before or local/after at live/ on GitHub Pages: ./flip.sh after
set -euo pipefail
cd "$(dirname "$0")"
version="${1:?usage: ./flip.sh before|after}"
python3 build_local.py live "$version"
git add live
git commit -qm "live: $version"
git push -q
echo "Pushed live/ = $version. Pages takes about a minute; check with:"
echo "  curl -s https://nate-selzer.github.io/nhs-scraper-fixture/live/medicines/acrivastine/ | grep -o 'BEFORE (version 1)\|AFTER (version 2)'"
