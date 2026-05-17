#!/bin/bash
# Pi Kitty Extension: Renders an image directly into the Kitty terminal
# Uses Kitty Graphics Protocol (https://sw.kovidgoyal.net/kitty/graphics-protocol/)
# Works over SSH — image data streams through the terminal session

FILEPATH="$1"
if [ ! -f "$FILEPATH" ]; then
  echo "Error: File $FILEPATH not found."
  exit 1
fi

# Get terminal width in cells (for image sizing)
if command -v tput tcols &>/dev/null; then
  COLS=$(tput cols)
else
  COLS=80
fi

# Calculate pixel width (roughly cells * 10)
PIXEL_WIDTH=$((COLS * 10))
PIXEL_HEIGHT=$((PIXEL_WIDTH * 3 / 4))

# Send the image using Kitty's icat protocol
# This works over SSH — the escape codes pass through the SSH directly to your local Kitty terminal
printf '\033_Ga=T,f=100,m=0;'
base64 < "$FILEPATH" | tr -d '\n'
printf '\033\\\\n'

# Also send via python3 kitty icat if available (more reliable)
if command -v kitty &>/dev/null; then
  kitty +kitten icat --hold "$FILEPATH" 2>/dev/null
fi

echo -e "\n✅ [Pi Kitty] Displayed: $FILEPATH"
