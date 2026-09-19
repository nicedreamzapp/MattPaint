#!/bin/bash
# 2026-09-18 experiment (Matt): the haunted-village prompt, painted by each local model twice —
# BLIND (prompt only) and SEEING (prompt + the target picture). Same Song Forge pause + memory
# seat as run_director.sh, taken ONCE for all six runs. Log: experiments/village/run_v7.log
set -u
cd "$(dirname "$0")"
EXP=experiments/village
PROMPT="$(cat $EXP/prompt.txt)"
PLIST="$HOME/Library/LaunchAgents/com.nicedreamz.songforge-m5-stack.plist"
MEM="$HOME/SongForgeM5/mem_client.py"
HOLD="$HOME/Desktop/PROJECTS/Local AI Setup/launchers/lib/hold_mem_lease.py"
busy() { curl -s -m 5 http://127.0.0.1:8767/api/status 2>/dev/null |
  /usr/bin/python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('jobs_running',0)+d.get('queue_depth',0))" 2>/dev/null || echo 0; }
FORGE_STOPPED=0; LEASE=""
restore() {
  [ -n "$LEASE" ] && /usr/bin/python3 "$MEM" release "$LEASE" >/dev/null 2>&1
  [ "$FORGE_STOPPED" = 1 ] || return 0
  echo "putting Song Forge back..."
  launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null
  launchctl start com.nicedreamz.songforge-m5-stack 2>/dev/null
}
trap restore EXIT INT TERM
if curl -s -m 3 http://127.0.0.1:8767/api/status 2>/dev/null | grep -q '"ace_up"' \
   || launchctl print "gui/$(id -u)/com.nicedreamz.songforge-m5-stack" >/dev/null 2>&1; then
  while [ "$(busy)" != "0" ]; do echo "waiting for a Song Forge song to finish..."; sleep 10; done
  echo "pausing Song Forge"
  launchctl bootout "gui/$(id -u)/com.nicedreamz.songforge-m5-stack" 2>/dev/null
  for port in 8001 8767 9420; do
    p=$(lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null | head -1); [ -n "$p" ] && kill "$p" 2>/dev/null
  done
  FORGE_STOPPED=1; sleep 5
fi
HUB="$HOME/.cache/huggingface/hub"
for spec in \
  "Gemma 4|_gemma|$HUB/gemma-4-31b-it-abliterated-VL-mlx-bf16" \
  "Qwen 3.8|_qwen|donedynamics/Qwen3.8-27B-heretic-VL-MLX-bf16" \
  "SuperGemma|_supergemma|DreamFoundries/SuperGemma-4-12b-abliterated-4bit"; do
  IFS='|' read -r NAME TAG MODEL <<< "$spec"
  for mode in blind seeing; do
    echo; echo "##### $NAME — $mode  $(date +%H:%M)"
    # a fresh seat per run: hold_mem_lease releases the seat when its process exits
    LEASE="$(/usr/bin/python3 "$MEM" wait qwen-director 48 --timeout 300 2>/dev/null)"
    echo "memory seat ${LEASE:-none}"
    extra=(); [ "$mode" = seeing ] && extra=(--ref "$EXP/target.png")
    ( trap - EXIT INT TERM      # the background copy must never run restore()
      MATTPAINT_NAME="$NAME" MATTPAINT_TAG="${TAG}_${mode}_v7" MATTPAINT_MODEL="$MODEL" HF_HUB_OFFLINE=1 PYTHONWARNINGS=ignore \
        exec "$HOME/.local/mlx-vlm-latest/bin/python3" director.py "$PROMPT" --rounds 1 ${extra[@]+"${extra[@]}"} ) &
    PID=$!
    [ -n "$LEASE" ] && /usr/bin/python3 "$HOLD" "$LEASE" "$PID" >/dev/null 2>&1 &
    wait "$PID"; LEASE=""
  done
done
echo "##### ALL DONE $(date +%H:%M)"
