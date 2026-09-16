"""throughput test: how many movements per second in each mode / window kind"""
import asyncio, sys, time, json, urllib.request, random
from engine import *

async def bench(browser, mode, label):
    t = await browser.new_tab(mode)
    await t.goto("https://nicedreamzwholesale.com/paint/?r=" + str(time.time()))
    await t.measure_canvas()
    await t.tool('brush'); await t.size(3); await t.sync()
    await t.set_color(1, (200, 40, 60)); await t.sync()
    t0 = time.time(); t.moves = 0
    for i in range(300):
        x = random.uniform(20, 760); y = random.uniform(20, 560)
        pts = [(x + k * 3, y + 20 * __import__('math').sin(k / 3)) for k in range(30)]
        t.stroke(pts)
    await t.sync()
    dt = time.time() - t0
    print(f"{label:28s} {mode:7s} {t.moves} moves in {dt:.2f}s = {t.moves/dt:,.0f} moves/s, {300/dt:.0f} strokes/s", flush=True)
    await t.png(f"bench_{label}_{mode}.png")
    await t.close()

async def main():
    br = Browser(9222); await br.connect()
    for mode in ("input", "replay"):
        await bench(br, mode, "hidden-broker")
    await br.close()
    proc = launch_brave(9231)
    br = Browser(9231); await br.connect()
    for mode in ("input", "replay"):
        await bench(br, mode, "visible-nolimit")
    await br.close(); proc.terminate()
asyncio.run(main())
