#!/bin/sh
# KD Dashboard: download test for Kindle 4 (v2, uses a modern bundled curl)
# Writes a log to the Kindle drive as dash_test_log.txt

KD=/mnt/us/extensions/kddash
LOG=/mnt/us/dash_test_log.txt
IMG=/mnt/us/dash_test.png
URL="https://raw.githubusercontent.com/RXKADDU/KINDLE---DASH/main/test/test.png"
CURL=/tmp/kdcurl

say() { eips 1 "$1" "$2" >/dev/null 2>&1; }

eips -c >/dev/null 2>&1
say 2 "KD Dashboard test v2 running..."
say 4 "Please wait about 30 seconds"

{
  echo "=== KD dashboard test v2 ==="
  echo "Date on Kindle: $(date)"
  echo "Kernel: $(uname -r)"
  echo ""
  echo "--- Network ---"
  ifconfig wlan0 2>&1 | grep -i "inet " || echo "No IP address on wlan0 (Wi-Fi off?)"
  echo ""
  echo "--- Bundled curl ---"
  ls -l "$KD" 2>&1
} > "$LOG" 2>&1

RESULT="FAILED"
rm -f "$IMG"

if [ ! -f "$KD/curl-armv7" ]; then
  echo "curl-armv7 NOT FOUND in $KD" >> "$LOG"
else
  cp "$KD/curl-armv7" "$CURL" && chmod 755 "$CURL"
  echo "" >> "$LOG"
  echo "--- curl version ---" >> "$LOG"
  "$CURL" --version >> "$LOG" 2>&1
  echo "exit code: $?" >> "$LOG"

  echo "" >> "$LOG"
  echo "--- Test A: HTTPS with CA bundle ---" >> "$LOG"
  "$CURL" -sS -L --connect-timeout 20 --max-time 60 --cacert "$KD/cacert.pem" -o "$IMG" "$URL" >> "$LOG" 2>&1
  echo "exit code: $?" >> "$LOG"
  if [ -s "$IMG" ]; then RESULT="https-verified"; fi

  if [ "$RESULT" = "FAILED" ]; then
    echo "--- Test B: HTTPS without certificate check ---" >> "$LOG"
    "$CURL" -sS -k -L --connect-timeout 20 --max-time 60 -o "$IMG" "$URL" >> "$LOG" 2>&1
    echo "exit code: $?" >> "$LOG"
    if [ -s "$IMG" ]; then RESULT="https-unverified"; fi
  fi
fi

echo "" >> "$LOG"
echo "=== RESULT: $RESULT ===" >> "$LOG"
[ -s "$IMG" ] && ls -l "$IMG" >> "$LOG" 2>&1

eips -c >/dev/null 2>&1
if [ "$RESULT" != "FAILED" ]; then
  eips -g "$IMG" >> "$LOG" 2>&1
  echo "Shown on screen with eips" >> "$LOG"
else
  say 2 "Download test FAILED"
  say 4 "Plug into laptop and send Claude"
  say 5 "the file dash_test_log.txt"
fi
sync
