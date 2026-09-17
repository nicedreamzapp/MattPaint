#!/bin/bash
# Run director.py (gen 6, local Qwen) with the memory it needs: waits for any Song Forge song to
# finish, pauses Song Forge, takes a forge_guard seat for the model, and on exit puts Song Forge
# back. The painting window stays open on the last picture (Matt: every picture in view).
#   ./run_director.sh "DAWN RIDGES"            one subject
#   ./run_director.sh --all                     all eleven, holdouts painted once
#   ./run_director.sh "a lighthouse in a storm"    any prompt
set -u
cd "$(dirname "$0")"
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

# Pause Song Forge if it is up OR merely loaded. Checking only ace_up missed a Song Forge that was
# still starting back up from the previous run (2026-09-17 1:40a): it came up beside a 62GB model,
# memory ran out, and forge_guard froze the director.
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

LEASE="$(/usr/bin/python3 "$MEM" wait qwen-director 48 --timeout 300 2>/dev/null)"
[ -n "$LEASE" ] && echo "memory seat $LEASE" || echo "forge_guard gave no seat — running anyway"

HF_HUB_OFFLINE=1 PYTHONWARNINGS=ignore "$HOME/.local/mlx-vlm-latest/bin/python3" director.py "$@" &
PID=$!
[ -n "$LEASE" ] && /usr/bin/python3 "$HOLD" "$LEASE" "$PID" >/dev/null 2>&1 &
wait "$PID"
