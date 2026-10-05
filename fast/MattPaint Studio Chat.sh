#!/bin/bash
# MattPaint Studio for Moonstone: same as "MattPaint Studio.command", but it reads plain lines from
# stdin and prints "›" when it's ready, so Moonstone's chat box is where you type what to paint.
# Add "rounds 6" anywhere in the message to change the improvement rounds (default 0, fast).
cd "$(dirname "$0")"
echo "MattPaint Studio · gen 6 — local Gemma 4 directs, the engine paints it on screen."
echo "Type what you want painted. Fast mode: one straight painting, no sketch, no improvement rounds (add \"rounds 2\" to have it improve itself). Everything you type here gets painted, so talk to Claude in the other chat."
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
  echo "Painting \"$PROMPT\" with $ROUNDS rounds. Painter: $(basename "${MATTPAINT_MODEL:-gemma-4-31b-it-abliterated-VL-mlx-bf16}"), running locally. Watch the MattPaint window."
  # window closed since the chat opened? open it now while the model loads
  curl -s -m 1 http://localhost:9231/json/version >/dev/null 2>&1 || \
    ("$HOME/.local/mlx-server/bin/python3" open_window.py >/dev/null 2>&1 &)
  ./run_director.sh "$PROMPT" --rounds "$ROUNDS" --no-think --gray-rounds -1 2>&1 | grep --line-buffered -v -iE "warn|fetching|it/s"
  echo "Done, the best painting is on screen and saved in MattPaint/gallery/gen6/. What next?"
  printf '\n› '
done
