"""Paint while grabbing canvas frames, then ffmpeg them into an mp4.
The paint runs at full speed; we snapshot on a timer so the video shows the build.
"""
import asyncio, time, os, base64, glob, subprocess
from engine import Browser
import paint_fast as pf

FRAMES = "frames"
async def grabber(tab, stop):
    i = 0
    os.makedirs(FRAMES, exist_ok=True)
    for f in glob.glob(f"{FRAMES}/*.jpg") + glob.glob(f"{FRAMES}/*.png"): os.remove(f)
    while not stop.is_set():
        try:
            c = tab.canvas
            r = await tab.call("Page.captureScreenshot", {"format":"jpeg","quality":70,
                    "clip":{"x":c["x"],"y":c["y"],"width":c["w"],"height":c["h"],"scale":1},
                    "captureBeyondViewport": True})
            open(f"{FRAMES}/f{i:04d}.jpg","wb").write(base64.b64decode(r["data"]))
            i += 1
        except Exception as e: pass
        await asyncio.sleep(0.0)
    return i

async def main():
    br = Browser(9222); await br.connect()
    tab = await br.new_tab("replay")
    pf.tab = tab
    _drag, _path = pf.drag, pf.path
    async def sdrag(*a, **k):
        await _drag(*a, **k); await asyncio.sleep(0.012)
    async def spath(*a, **k):
        await _path(*a, **k); await asyncio.sleep(0.012)
    pf.drag = sdrag; pf.path = spath
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas()
    stop = asyncio.Event()
    g = asyncio.create_task(grabber(tab, stop))
    pf.T0 = time.time(); t0 = time.time()
    await pf.paint(); await tab.sync()
    dt = time.time() - t0
    # a few tail frames of the finished piece
    await asyncio.sleep(0.4)
    stop.set(); n = await g
    print(f"painted {dt:.2f}s, captured {n} frames", flush=True)
    await tab.close(); await br.close()
asyncio.run(main())
