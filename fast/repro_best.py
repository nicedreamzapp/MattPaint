"""Region-aware photo reproduction via MattPaint's fast-draw accelerator.
Flat areas -> solid rects (clean, cheap). Edges -> directional strokes (crisp, painterly).
Exact per-op colour, so no palette banding. Draws straight to the canvas -> ~100x+ faster.
"""
import asyncio, sys, time, math
import numpy as np
from PIL import Image
from engine import Browser

REF = sys.argv[1] if len(sys.argv) > 1 else "ref_eagle.png"
CW = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
CH = int(sys.argv[3]) if len(sys.argv) > 3 else 600
VISIBLE = "--hidden" not in sys.argv   # on-screen by DEFAULT; hiding must be explicit
tab = None

def load_ref():
    im = Image.open(REF).convert("RGB")
    arc, ari = CW/CH, im.width/im.height
    if ari > arc:
        w = int(im.height*arc); im = im.crop(((im.width-w)//2,0,(im.width+w)//2,im.height))
    else:
        h = int(im.width/arc); im = im.crop((0,(im.height-h)//2,im.width,(im.height+h)//2))
    return im.resize((CW, CH), Image.LANCZOS)

def build(im):
    arr = np.asarray(im, dtype=np.int16)
    g = arr.astype(np.float32).mean(2)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:,1:-1] = g[:,2:]-g[:,:-2]; gy[1:-1,:] = g[2:,:]-g[:-2,:]
    mag = np.hypot(gx, gy)
    ops = []
    # base mosaic: 3px cells, exact average colour, full coverage (kills confetti)
    cell = 2
    for y in range(0, CH, cell):
        for x in range(0, CW, cell):
            p = arr[y:y+cell, x:x+cell]
            c = p.reshape(-1,3).mean(0)
            ops.append([0, x, y, cell, cell, int(c[0]), int(c[1]), int(c[2])])
    base = len(ops)
    # edge strokes: where gradient is strong, a short directional stroke sharpens the edge
    for cy in range(2, CH-2, 2):
        for cx in range(2, CW-2, 2):
            if mag[cy, cx] < 16: continue
            dx, dy = gx[cy,cx], gy[cy,cx]; n = math.hypot(dx,dy)
            if n < 1e-3: continue
            ux, uy = -dy/n, dx/n
            L = 2.6
            c = arr[cy, cx]
            ops.append([1, cx-ux*L, cy-uy*L, cx+ux*L, cy+uy*L, 1.6, int(c[0]), int(c[1]), int(c[2])])
    return ops, base

def rnd(ops):
    out=[]
    for o in ops:
        if o[0]==1:
            out.append([1, round(float(o[1]),1), round(float(o[2]),1), round(float(o[3]),1), round(float(o[4]),1), float(o[5]), int(o[6]), int(o[7]), int(o[8])])
        else: out.append([0, int(o[1]), int(o[2]), int(o[3]), int(o[4]), int(o[5]), int(o[6]), int(o[7])])
    return out

async def main():
    global tab
    im = load_ref(); im.save("ref_fit.png")
    ops, base = build(im)
    print(f"{base} fill rects + {len(ops)-base} edge strokes = {len(ops)} ops", flush=True)
    if VISIBLE:
        from engine import launch_brave
        proc = launch_brave(9231, size=(1500, 900)); await asyncio.sleep(2.0)
        br = Browser(9231)
    else:
        br = Browser(9222)
    await br.connect()
    tab = await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas()
    t0 = time.time()
    await tab.resize_canvas(CW, CH)
    ops = rnd(ops)
    CHUNK = 6000
    for i in range(0, len(ops), CHUNK):
        tab.fast(ops[i:i+CHUNK])
        if (i//CHUNK) % 4 == 0: await tab.sync()
    tab.fast_commit(); await tab.sync()
    dt = time.time()-t0
    print(f"DONE {len(ops)} ops in {dt:.2f}s = {len(ops)/dt:,.0f} ops/s", flush=True)
    await tab.png("repro2.png")
    if not VISIBLE:
        await tab.close()
    await br.close()
asyncio.run(main())
