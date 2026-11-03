#!/bin/bash
# v5: re-render both robot shots bright, paint every frame in MattPaint on screen, record the painting.
FAST=~/Desktop/PROJECTS/MattPaint/fast; G=~/Desktop/PROJECTS/MattPaint/gallery/films; X=~/Desktop/PROJECTS/MattPaint/explainer/footage
cd $FAST
for pair in "robot_forest_bl.py:robot_bright:Robot in the forest" "robot_rise_bl.py:rise_bright:The robot wakes"; do
  IFS=: read scene name title <<< "$pair"
  D=$G/$name; R=$X/${name}_paint; rm -rf $D $R; mkdir -p $D/render $R
  MP_LOOK=bright nohup /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/$scene -- $D/render > $D/blender.log 2>&1 &
  BP=$!
  ( while kill -0 $BP 2>/dev/null; do r=$(curl -s -m 5 127.0.0.1:8767/api/status | /usr/bin/python3 -c 'import sys,json;print(json.load(sys.stdin).get("jobs_running",0))' 2>/dev/null || echo 0); if [ "$r" -gt 0 ]; then kill -STOP $BP; else kill -CONT $BP; fi; sleep 15; done ) &
  /usr/bin/python3 -u record_tab.py $R > $R/rec.log 2>&1 &
  sleep 3
  /usr/bin/python3 -u paint_frames.py $D/render $name --count 120 --title "$title" > $D/paint.log 2>&1
  touch $R/stop; while pgrep -f "record_tab.py $R" >/dev/null; do sleep 3; done
  echo "$name: $(tail -1 $D/paint.log)"
done
# slow paint of one bright frame onto a blank page
S=$X/slow_paint_bright; rm -rf $S; mkdir -p $S
/usr/bin/python3 -u record_tab.py $S > $S/rec.log 2>&1 &
sleep 3; /usr/bin/python3 -u slow_paint.py $G/robot_bright/frames/0060.png --title "Robot in the forest · one frame" > $S/paint.log 2>&1
touch $S/stop; while pgrep -f "record_tab.py $S" >/dev/null; do sleep 3; done
echo "ALL DONE"
