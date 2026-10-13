#!/bin/sh
# KD Dashboard: download test for Kindle 4
# Writes a log to the Kindle drive as dash_test_log.txt

LOG=/mnt/us/dash_test_log.txt
IMG=/mnt/us/dash_test.png
URL_HTTPS="https://raw.githubusercontent.com/RXKADDU/KINDLE---DASH/main/test/test.png"
URL_HTTP="http://raw.githubusercontent.com/RXKADDU/KINDLE---DASH/main/test/test.png"

say() { eips 1 "$1" "$2" >/dev/null 2>&1; }

eips -c >/dev/null 2>&1
say 2 "KD Dashboard test running..."
say 4 "Please wait about 30 seconds"

{
  echo "=== KD dashboard test ==="
  echo "Date on Kindle: $(date)"
  echo "Firmware: $(cat /etc/prettyversion.txt 2>/dev/null)"
  echo ""
  echo "--- Tools available ---"
  for t in wget curl openssl eips; do
    p=$(which $t 2>/dev/null)
    echo "$t: ${p:-not found}"
  done
  wget --help 2>&1 | head -2
  echo ""
  echo "--- Network ---"
  ifconfig wlan0 2>&1 | grep -i "inet " || echo "No IP address on wlan0 (Wi-Fi off?)"
  ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1 && echo "Internet ping: OK" || echo "Internet ping: FAILED"
  nslookup raw.githubusercontent.com 2>&1 | tail -2
  echo ""
} > "$LOG" 2>&1

RESULT="FAILED"
rm -f "$IMG"

echo "--- Test 1: wget HTTPS ---" >> "$LOG"
wget -O "$IMG" "$URL_HTTPS" >> "$LOG" 2>&1
if [ -s "$IMG" ]; then RESULT="wget-https"; fi

if [ "$RESULT" = "FAILED" ] && which curl >/dev/null 2>&1; then
  echo "--- Test 2: curl HTTPS ---" >> "$LOG"
  curl -s -S -L -o "$IMG" "$URL_HTTPS" >> "$LOG" 2>&1
  if [ -s "$IMG" ]; then RESULT="curl-https"; fi
  if [ "$RESULT" = "FAILED" ]; then
    echo "--- Test 3: curl HTTPS insecure ---" >> "$LOG"
    curl -s -S -k -L -o "$IMG" "$URL_HTTPS" >> "$LOG" 2>&1
    if [ -s "$IMG" ]; then RESULT="curl-https-insecure"; fi
  fi
fi

if [ "$RESULT" = "FAILED" ]; then
  echo "--- Test 4: wget HTTP ---" >> "$LOG"
  wget -O "$IMG" "$URL_HTTP" >> "$LOG" 2>&1
  if [ -s "$IMG" ]; then RESULT="wget-http"; fi
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
