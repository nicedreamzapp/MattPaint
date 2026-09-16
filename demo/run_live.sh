#!/bin/bash
# Paints on screen in a visible Brave window and records that screen region.
cd "$(dirname "$0")"
mkdir -p video
STAMP=$(date +%Y%m%d-%H%M%S)
# window is placed at 900,120 sized 1600x990 by paint_real.py; record that rect
screencapture -v -x -R900,120,1600,990 -V 900 "video/screen_$STAMP.mov" &
REC=$!
sleep 2
python3 paint_real.py live 2>&1 | grep -v -i deprecation | tee "video/live_$STAMP.log"
sleep 2
kill -INT $REC 2>/dev/null
wait $REC 2>/dev/null
ls -la video/
