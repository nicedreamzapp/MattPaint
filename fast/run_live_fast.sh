#!/bin/bash
cd "$(dirname "$0")"
mkdir -p video
STAMP=$(date +%H%M%S)
# launch visible Brave first so it settles, then record the window region while it paints
python3 - "$STAMP" <<'PY'
import asyncio, sys, time, subprocess, os
from engine import Browser, launch_brave
stamp = sys.argv[1]
async def main():
    proc = launch_brave(9231)                 # visible, frame limit off
    await asyncio.sleep(2.0)
    rec = subprocess.Popen(["screencapture","-v","-x","-R900,120,1600,990","-V","20",
                            f"video/paint_{stamp}.mov"])
    await asyncio.sleep(1.0)
    br = Browser(9231); await br.connect()
    tab = await br.new_tab("replay")
    # import and drive the same paint() used in the dry run
    import paint_fast as pf
    pf.tab = tab
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas()
    pf.T0 = time.time()
    t0 = time.time()
    await pf.paint()
    await tab.sync()
    dt = time.time() - t0
    print(f"LIVE DONE {dt:.2f}s  {tab.moves} moves = {tab.moves/dt:,.0f}/s", flush=True)
    await tab.png(f"video/final_live_{stamp}.png")
    await asyncio.sleep(1.5)
    rec.send_signal(2); 
    try: rec.wait(timeout=10)
    except Exception: rec.kill()
    await br.close()
asyncio.run(main())
PY
ls -la video/paint_${STAMP}.mov video/final_live_${STAMP}.png 2>/dev/null
