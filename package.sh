#!/usr/bin/env bash
# Build grampsclean addon zip for GRAMPS distribution
set -e

VERSION=$(python3 -c "
import re, sys
with open('grampsclean/grampsclean.gpr.py') as f:
    m = re.search(r'version=\"([^\"]+)\"', f.read())
print(m.group(1) if m else sys.exit(1))
")

ZIPNAME="grampsclean-${VERSION}.zip"

# Remove old zip if exists
rm -f "$ZIPNAME"

# Build zip: include all .py files and README.md inside grampsclean/
# Exclude __pycache__ and .DS_Store
zip -r "$ZIPNAME" grampsclean/ \
    --exclude "grampsclean/__pycache__/*" \
    --exclude "grampsclean/*.pyc" \
    --exclude "grampsclean/.DS_Store"

echo "Built: $ZIPNAME"
