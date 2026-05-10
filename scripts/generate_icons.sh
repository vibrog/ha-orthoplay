#!/usr/bin/env bash
# Generates PNG icons from SVG source using ImageMagick.
# Usage: ./scripts/generate_icons.sh

set -e

SOURCE="$(cd "$(dirname "$0")/.." && pwd)/assets/orthoplay.svg"
DEST="$(cd "$(dirname "$0")/.." && pwd)/custom_components/orthoplay/brand"

if command -v magick &> /dev/null; then
    magick -background none "$SOURCE" -resize 256x256 "$DEST/icon.png"
    magick -background none "$SOURCE" -resize 512x512 "$DEST/icon@2x.png"
else
    echo "ERROR: ImageMagick not found. Install one and retry."
    exit 1
fi

echo "Icons written to $DEST"
