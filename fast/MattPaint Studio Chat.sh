#!/bin/bash
# MattPaint Studio for Moonstone: same as "MattPaint Studio.command", but it reads plain lines from
# stdin and prints "›" when it's ready, so Moonstone's chat box is where you type what to paint.
# Add "rounds 6" anywhere in the message to change the improvement rounds (default 0, fast).
cd "$(dirname "$0")"
echo "MattPaint Studio — Claude builds the scene in 3D, real light is worked out, and MattPaint paints it on screen so it looks like a photo. About 3 to 5 minutes."
echo "Type what you want painted. Start with \"cartoon\" for the old quick engine (about a minute and a half). Everything you type here gets painted, so talk to Claude in the other chat."
# Matt 2026-10-05: open MattPaint the moment the chat opens, so the window is
# up and moving before he has typed anything. Skipped if the window is already up (a painting may be running).
if ! curl -s -m 1 http://localhost:9231/json/version >/dev/null 2>&1; then
  "$HOME/.local/mlx-server/bin/python3" open_window.py >/dev/null 2>&1 \
    && echo "MattPaint is open." || echo "MattPaint didn't open, it will try again when you send something."
fi
printf '\n› '
while IFS= read -r PROMPT; do
  PROMPT="$(echo "$PROMPT" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  [ -z "$PROMPT" ] && { printf '\n› '; continue; }
  ROUNDS=0
  if [[ "$PROMPT" =~ [Rr]ounds?[[:space:]]*([0-9]+) ]]; then
    ROUNDS="${BASH_REMATCH[1]}"
    PROMPT="$(echo "$PROMPT" | sed -E 's/[,;]?[[:space:]]*[Rr]ounds?[[:space:]]*[0-9]+//; s/[[:space:]]+$//')"
  fi
  # Matt 2026-11-02 ("make it look real"): photoreal is the default now; "cartoon ..." keeps the gen-6 engine.
  if [[ ! "$PROMPT" =~ ^[Cc]artoon[[:space:]:,]* ]]; then
    curl -s -m 1 http://localhost:9231/json/version >/dev/null 2>&1 || \
      ("$HOME/.local/mlx-server/bin/python3" open_window.py >/dev/null 2>&1 &)
    echo "Painting \"$PROMPT\" to look real. Watch the MattPaint window: a rough pass first, then the final."
    /usr/bin/python3 -u photo_director.py "$PROMPT" 2>&1 | grep --line-buffered -v -iE "warn|fp = o|cam\\["
    echo "Done, it's on screen and saved in MattPaint/gallery/opus-photoreal/. What next?"
    printf '\n› '
    continue
  fi
  PROMPT="$(echo "$PROMPT" | sed -E 's/^[Cc]artoon[[:space:]:,]*//')"
  echo "Painting \"$PROMPT\" with $ROUNDS rounds. Painter: Claude. Watch the MattPaint window."
  # window closed since the chat opened? open it now while the model loads
  curl -s -m 1 http://localhost:9231/json/version >/dev/null 2>&1 || \
    ("$HOME/.local/mlx-server/bin/python3" open_window.py >/dev/null 2>&1 &)
  # Matt 2026-10-05: Claude draws (about 1.5 min, a real dog); local Gemma took 5 min for a blob. No local
  # model, so Song Forge is never paused. MATTPAINT_PAINTER=local brings the Gemma path back.
  if [ "${MATTPAINT_PAINTER:-claude}" = claude ]; then
    MATTPAINT_NAME="Claude Opus 5.5" PYTHONWARNINGS=ignore "$HOME/.local/mlx-vlm-latest/bin/python3" director.py "$PROMPT" \
      --painter claude --rounds "$ROUNDS" --gray-rounds -1 2>&1 | grep --line-buffered -v -iE "warn|fetching|it/s"
  else
    ./run_director.sh "$PROMPT" --rounds "$ROUNDS" --no-think --gray-rounds -1 2>&1 | grep --line-buffered -v -iE "warn|fetching|it/s"
  fi
  echo "Done, the best painting is on screen and saved in MattPaint/gallery/gen6/. What next?"
  printf '\n› '
done
