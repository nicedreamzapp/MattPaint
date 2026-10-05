#!/bin/bash
# MattPaint Studio for Moonstone: same as "MattPaint Studio.command", but it reads plain lines from
# stdin and prints "›" when it's ready, so Moonstone's chat box is where you type what to paint.
# Add "rounds 6" anywhere in the message to change the improvement rounds (default 4).
cd "$(dirname "$0")"
echo "MattPaint Studio · gen 6 — local Gemma 4 directs, the engine paints it on screen."
echo "Type what you want painted (add \"rounds 6\" to change the rounds, default 4). Each painting takes about 10-20 minutes."
printf '\n› '
while IFS= read -r PROMPT; do
  PROMPT="$(echo "$PROMPT" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  [ -z "$PROMPT" ] && { printf '\n› '; continue; }
  ROUNDS=4
  if [[ "$PROMPT" =~ [Rr]ounds?[[:space:]]*([0-9]+) ]]; then
    ROUNDS="${BASH_REMATCH[1]}"
    PROMPT="$(echo "$PROMPT" | sed -E 's/[,;]?[[:space:]]*[Rr]ounds?[[:space:]]*[0-9]+//; s/[[:space:]]+$//')"
  fi
  echo "Painting \"$PROMPT\" with $ROUNDS rounds. Painter: $(basename "${MATTPAINT_MODEL:-gemma-4-31b-it-abliterated-VL-mlx-bf16}"), running locally. Watch the MattPaint window."
  ./run_director.sh "$PROMPT" --rounds "$ROUNDS" 2>&1 | grep --line-buffered -v -iE "warn|fetching|it/s"
  echo "Done, the best painting is on screen and saved in MattPaint/gallery/gen6/. What next?"
  printf '\n› '
done
