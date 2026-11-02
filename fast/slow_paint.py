"""slow_paint — paints ONE picture onto a blank white MattPaint canvas in small batches, so a recording
clearly shows the strokes sweeping down (explainer footage, 2026-11-02).
    slow_paint.py IMAGE.png [--batch 1500] [--pause 0.03] [--title "..."]"""
import argparse, asyncio, json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pt

async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("image")
    ap.add_argument("--batch", type=int, default=1500); ap.add_argument("--pause", type=float, default=0.03)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    from engine import Browser, paint_url
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url()); await tab.measure_canvas()
    img = np.asarray(Image.open(a.image).convert("RGB"))
    await tab.resize_canvas(img.shape[1], img.shape[0])
    tab.fast(pt.to_ops(np.full_like(img, 255))); await tab.sync()      # blank white page
    await asyncio.sleep(2.0)
    ops = pt.to_ops(img)
    for k in range(0, len(ops), a.batch):
        tab.fast(ops[k:k + a.batch]); await tab.sync()
        if a.title:
            await tab.eval(pt.BANNER_JS + "window.__opusBanner(" + json.dumps(
                f"<b>{a.title}</b><br>{min(k + a.batch, len(ops)):,} / {len(ops):,} strokes") + ")", ret=False)
        await asyncio.sleep(a.pause)
    await asyncio.sleep(3.0)
    await tab.eval("document.getElementById('opus-banner')?.remove()", ret=False)
    print(f"painted {len(ops):,} strokes", flush=True)
    await br.close()

asyncio.run(main())
