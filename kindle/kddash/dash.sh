#!/bin/sh
# KD Dashboard for Kindle 4
#   Page buttons / 5-way left-right: flip pages
#   5-way centre press: refresh now
#   Home, Back or Menu: exit back to the normal Kindle screen
# Log: dash_log.txt on the Kindle drive

trap '' HUP
set -x
KD=/mnt/us/extensions/kddash
PAGES=$KD/pages
LOG=/mnt/us/dash_log.txt
BASE="https://raw.githubusercontent.com/RXKADDU/KINDLE---DASH/output"
CURL=/tmp/kdcurl
KEYS=/tmp/kdkeys
REFRESH_MIN=25          # download fresh pages at HH:25 every hour

echo $$ > /tmp/kddash.pid
mkdir -p "$PAGES"
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 100000 ]; then mv "$LOG" "$LOG.old"; fi

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }
msg() { eips -c >/dev/null 2>&1; eips 1 3 "$1" >/dev/null 2>&1; eips 1 5 "$2" >/dev/null 2>&1; }

cp "$KD/curl-armv7" "$CURL" 2>/dev/null && chmod 755 "$CURL"
cp "$KD/kdkeys" "$KEYS" && chmod 755 "$KEYS"
if [ ! -x "$CURL" ]; then msg "curl-armv7 missing" "Copy it into extensions/kddash"; log "curl missing"; exit 1; fi

cleanup() {
  log "stopping"
  rm -f /tmp/kddash.pid
  lipc-set-prop com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1
  msg "Closing dashboard..." "Kindle screen will return shortly"
  /etc/init.d/framework start >/dev/null 2>&1
  exit 0
}
trap cleanup TERM INT

wifi_up() {
  lipc-set-prop com.lab126.cmd wirelessEnable 1 >/dev/null 2>&1
  i=0
  while [ $i -lt 30 ]; do
    ifconfig wlan0 2>/dev/null | grep -q "inet addr" && return 0
    sleep 2; i=$((i + 1))
  done
  return 1
}

fetch() {
  log "fetching"
  if ! wifi_up; then log "no wifi"; return 1; fi
  rm -rf "$PAGES/new"; mkdir -p "$PAGES/new"
  T=$(date +%s)
  get() { "$CURL" -sS -f -L --connect-timeout 20 --max-time 60 --cacert "$KD/cacert.pem" -o "$2" "$BASE/$1?t=$T" >> "$LOG" 2>&1; }
  if ! get pages.txt "$PAGES/new/pages.txt"; then log "pages.txt failed"; return 1; fi
  for f in $(cat "$PAGES/new/pages.txt"); do
    if ! get "$f" "$PAGES/new/$f"; then log "$f failed"; return 1; fi
  done
  mv "$PAGES/new/"* "$PAGES/" && rmdir "$PAGES/new"
  log "fetched $(wc -l < "$PAGES/pages.txt") pages"
  return 0
}

count() { N=$(grep -c . "$PAGES/pages.txt" 2>/dev/null); [ -z "$N" ] && N=0; }

show() {
  count
  if [ "$N" -eq 0 ]; then msg "No pages yet" "Check Wi-Fi, then press centre to retry"; return; fi
  [ "$IDX" -gt "$N" ] && IDX=1
  [ "$IDX" -lt 1 ] && IDX=$N
  F="$PAGES/$(sed -n "${IDX}p" "$PAGES/pages.txt")"
  FLIPS=$((FLIPS + 1))
  if [ "$1" = "full" ] || [ $((FLIPS % 6)) -eq 0 ]; then
    eips -f -g "$F" >/dev/null 2>&1 || eips -g "$F" >/dev/null 2>&1
  else
    eips -g "$F" >/dev/null 2>&1
  fi
}

next_refresh() {
  NOW=$(date +%s)
  NEXT=$(( NOW + 3600 - ((NOW - REFRESH_MIN * 60) % 3600) ))
}

log "starting"
lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1
msg "KD Dashboard starting..." "Fetching latest pages"
/etc/init.d/framework stop >/dev/null 2>&1
sleep 3

IDX=1; FLIPS=0; UNKNOWN=0
fetch
show full
next_refresh

while true; do
  LEFT=$(( NEXT - $(date +%s) ))
  if [ $LEFT -le 0 ]; then fetch; show full; next_refresh; continue; fi
  K=$("$KEYS" "$LEFT")
  [ "$K" != "timeout" ] && log "key $K"
  case "$K" in
    timeout) ;;
    191|193|106|108) UNKNOWN=0; IDX=$((IDX + 1)); show ;;   # next: page forward, right, down
    104|109|105|103) UNKNOWN=0; IDX=$((IDX - 1)); show ;;   # back: page back, left, up
    194)             UNKNOWN=0; msg "Refreshing..." ""; fetch; show full ;;  # centre press
    102|158|139)     cleanup ;;                             # home, back, menu
    noinput)         log "no input devices"; sleep 60 ;;
    *)               UNKNOWN=$((UNKNOWN + 1)); [ $UNKNOWN -ge 5 ] && cleanup ;;
  esac
done
