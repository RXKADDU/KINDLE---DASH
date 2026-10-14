#!/bin/sh
# Launch the dashboard so it keeps running after the Kindle UI is stopped.
# Writes a start-up log to dash_start_log.txt on the Kindle drive.
KD=/mnt/us/extensions/kddash
L=/mnt/us/dash_start_log.txt
{
  echo "=== start.sh $(date) ==="
  echo "nohup:  $(which nohup 2>/dev/null)"
  echo "setsid: $(which setsid 2>/dev/null)"
  echo "start-stop-daemon: $(which start-stop-daemon 2>/dev/null)"
  ls -l "$KD"
} > "$L" 2>&1

eips 1 37 "Starting KD Dashboard...          " >/dev/null 2>&1

if which setsid >/dev/null 2>&1; then
  echo "launch: setsid" >> "$L"
  setsid /bin/sh "$KD/dash.sh" >> "$L" 2>&1 < /dev/null &
elif which nohup >/dev/null 2>&1; then
  echo "launch: nohup" >> "$L"
  nohup /bin/sh "$KD/dash.sh" >> "$L" 2>&1 < /dev/null &
else
  echo "launch: plain background" >> "$L"
  /bin/sh "$KD/dash.sh" >> "$L" 2>&1 < /dev/null &
fi
echo "start.sh finished, dash pid $!" >> "$L"
sync
