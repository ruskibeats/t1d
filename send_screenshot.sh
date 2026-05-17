#!/bin/bash
# Send a screenshot via Kitty Graphics Protocol
FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "File not found: $FILE"
  exit 1
fi
# Use kitty icat if available, otherwise raw escape codes
if command -v kitty &>/dev/null; then
  kitty +kitten icat --hold "$FILE"
else
  printf '\033_Ga=T,f=100,m=0;\033\\'
  base64 "$FILE" | tr -d '\n'
  printf '\033\\\n'
fi
echo ""
echo "✅ Displayed: $FILE ($(du -sh "$FILE" | cut -f1))"