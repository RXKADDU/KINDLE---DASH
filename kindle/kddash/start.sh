#!/bin/sh
# Launch the dashboard in the background so it survives the Kindle UI being stopped
if [ -f /tmp/kddash.pid ] && kill -0 "$(cat /tmp/kddash.pid)" 2>/dev/null; then
  exit 0
fi
nohup /bin/sh /mnt/us/extensions/kddash/dash.sh > /dev/null 2>&1 &
