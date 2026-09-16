#!/bin/bash
# MattPaint Studio — type what you want painted; local Qwen 3.8 art-directs and the gen 6 scene
# engine paints it from scratch in MattPaint, on screen. No images go in.
# Double-click. Song Forge pauses while a painting is being made and comes back after each one.
cd "$(dirname "$0")"
printf '\033]0;MattPaint Studio\007'
clear
echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║  MattPaint Studio · gen 6                        ║"
echo "  ║  local Qwen 3.8 directs · the engine paints      ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""
echo "  It can paint: skies, sun, moon, stars, aurora, clouds, mountain ridges,"
echo "  hills, still water, meadows, canyons, redwoods, pines, a big oak, rocks,"
echo "  fog and sunbeams. Each painting takes about 10-20 minutes."
echo ""
while true; do
  echo ""
  read -r -p "  What should I paint? (Enter to quit) › " PROMPT
  [ -z "$PROMPT" ] && break
  read -r -p "  How many improvement rounds? [4] › " ROUNDS
  ROUNDS="${ROUNDS:-4}"
  echo ""
  ./run_director.sh "$PROMPT" --rounds "$ROUNDS" 2>&1 | grep -v -iE "warn|fetching|it/s"
  echo ""
  echo "  Done — the best painting is on screen and saved in MattPaint/gallery/gen6/."
done
echo "  Bye."
