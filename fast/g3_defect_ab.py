"""A/B the photographic-defect pass. One canvas, two saves, nothing else different.

BEFORE = gen3 DAWN RIDGES at the keeper stage (deterministic seed).
AFTER  = the same canvas with ONLY the defect pass added on top.
"""
import asyncio, time, urllib.request, sys
sys.argv = ["g3_ridges_paintable.py", "texture"]
import art as A
from art import stamp
import g3_ridges_paintable as RP
import defects as DF

a = RP.a
W, H = RP.W, RP.H
from art import TOPBAR

async def run():
    n = stamp(a)
    print(f"BEFORE: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up=True
    except Exception: up=False
    if not up: launch_brave(9231, size=(1560,1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r="+str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    tab.run_meta = {"generation": 3, "subject": "dawn_ridges", "stage": "defect_AB_before"}
    for i in range(0, len(a.ops), 1800):
        tab.fast(a.ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.04)
    await tab.sync()
    await tab.png("ab_before.png")
    print("saved ab_before.png", flush=True)

    ops = DF.defect_pass("ab_before.png", W, H, top_guard=TOPBAR+2,
                         focal_y=H*0.78, seed=4001)
    print(f"DEFECT PASS: {len(ops):,} strokes "
          f"({100.0*len(ops)/n:.1f}% of the painting)", flush=True)
    tab.run_meta = {"generation": 3, "subject": "dawn_ridges", "stage": "defect_AB_after",
                    "base_ops": n, "defect_ops": len(ops)}
    for i in range(0, len(ops), 1800):
        tab.fast(ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.04)
    await tab.sync()
    await tab.png("ab_after.png")
    print("saved ab_after.png", flush=True)
    await br.close()

asyncio.run(run())
