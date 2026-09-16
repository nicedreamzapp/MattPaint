"""Paint the Divine Tribe logo ON SCREEN, paced so it's watchable, while recording frames."""
import asyncio, time, os, glob, base64, subprocess, sys
from engine import Browser, launch_brave
import logo_hd as L

CW,CH = 1600,1000
FR="logorec"

async def main():
    L.ops.clear()
    L.CW, L.CH = CW, CH
    L.build()
    ops=L.ops
    print(f"{len(ops)} ops", flush=True)
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version",timeout=1); up=True
    except Exception: up=False
    if not up:
        launch_brave(9231,size=(1660,1050)); await asyncio.sleep(2.0)
    br=Browser(9231); await br.connect()
    tab=await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas()
    await tab.resize_canvas(CW,CH)
    os.makedirs(FR,exist_ok=True)
    for f in glob.glob(f"{FR}/*.jpg"): os.remove(f)
    stop=asyncio.Event()
    async def grab():
        i=0
        while not stop.is_set():
            try:
                c=tab.canvas
                r=await tab.call("Page.captureScreenshot",{"format":"jpeg","quality":78,
                    "clip":{"x":c["x"],"y":c["y"],"width":c["w"],"height":c["h"],"scale":1},
                    "captureBeyondViewport":True})
                open(f"{FR}/f{i:04d}.jpg","wb").write(base64.b64decode(r["data"])); i+=1
            except Exception: pass
            await asyncio.sleep(0.0)
        return i
    g=asyncio.create_task(grab())
    t0=time.time()
    CHUNK=max(1,len(ops)//170)          # ~170 visible steps
    for i in range(0,len(ops),CHUNK):
        tab.fast(ops[i:i+CHUNK]); await tab.sync()
        await asyncio.sleep(0.075)
    tab.fast_commit(); await tab.sync()
    dt=time.time()-t0
    await asyncio.sleep(0.8)
    stop.set(); n=await g
    print(f"built on screen in {dt:.1f}s, {n} frames", flush=True)
    await tab.png("logo_hd.png")
    await br.close()
asyncio.run(main())
