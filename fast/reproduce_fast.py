"""Fast photo reproduction in MattPaint.
Adaptive palette (~200 colours) so we set colour ~200 times total, not per stroke.
All strokes of one colour fire to the page in a single batched call.
Coarse-to-fine passes; each stroke's colour is the nearest palette colour to the sampled pixel.
"""
import asyncio, sys, time, math
import numpy as np
from PIL import Image
from engine import Browser

REF = sys.argv[1] if len(sys.argv) > 1 else "ref_eagle.png"
CW, CH = int(sys.argv[2]) if len(sys.argv) > 2 else 1400, int(sys.argv[3]) if len(sys.argv) > 3 else 700
NCOL = 220
tab = None

def load_ref():
    im = Image.open(REF).convert("RGB")
    ar_c, ar_i = CW / CH, im.width / im.height
    if ar_i > ar_c:
        w = int(im.height * ar_c); im = im.crop(((im.width - w)//2, 0, (im.width + w)//2, im.height))
    else:
        h = int(im.width / ar_c); im = im.crop((0, (im.height - h)//2, im.width, (im.height + h)//2))
    return im.resize((CW, CH), Image.LANCZOS)

def build(im):
    arr = np.asarray(im, dtype=np.float32)
    gray = arr.mean(2)
    gx = np.zeros_like(gray); gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    mag = np.hypot(gx, gy)
    # adaptive palette
    pal_img = im.convert("P", palette=Image.ADAPTIVE, colors=NCOL).convert("RGB")
    palette = np.array(sorted(set(pal_img.getdata())), dtype=np.float32)  # (K,3)
    def nearest(c):
        d = ((palette - c) ** 2).sum(1); return int(d.argmin())
    strokes_by_col = {}   # palette idx -> list of point-lists
    passes = [(44,10,1.4,0),(24,6,1.5,0),(13,4,1.6,0),(7,2,1.6,4),(4,1,1.7,12),(2,1,1.8,26)]
    for pi,(cell,bsize,lf,gmin) in enumerate(passes):
        for cy in range(cell//2, CH, cell):
            for cx in range(cell//2, CW, cell):
                y0,y1 = max(0,cy-cell//2), min(CH,cy+cell//2)
                x0,x1 = max(0,cx-cell//2), min(CW,cx+cell//2)
                patch = arr[y0:y1, x0:x1]
                if patch.size == 0: continue
                if mag[y0:y1, x0:x1].mean() < gmin: continue
                col = patch.reshape(-1,3).mean(0)
                ki = nearest(col)
                dx,dy = gx[cy,cx], gy[cy,cx]; n = math.hypot(dx,dy)
                ux,uy = (-dy/n, dx/n) if n>1e-3 else (1.0,0.0)
                L = cell*lf/2
                pts = [(float(cx-ux*L), float(cy-uy*L))]
                if bsize > 2: pts.append((float(cx), float(cy)))
                pts.append((float(cx+ux*L), float(cy+uy*L)))
                strokes_by_col.setdefault((pi, bsize, ki), []).append(pts)
    return palette, strokes_by_col

async def main():
    global tab
    im = load_ref(); im.save("ref_fit.png")
    palette, sbc = build(im)
    total = sum(len(v) for v in sbc.values())
    print(f"{total} strokes, {len(sbc)} colour-groups, {len(palette)} palette colours", flush=True)
    br = Browser(9222); await br.connect()
    tab = await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas()
    t0 = time.time()
    await tab.resize_canvas(CW, CH); await tab.measure_canvas()
    sx = tab.canvas["w"]/CW; sy = tab.canvas["h"]/CH
    avg = np.asarray(im).reshape(-1,3).mean(0).astype(int)
    await tab.fill_mode('solid'); await tab.outline_mode('none')
    await tab.set_color(2, tuple(avg)); await tab.shape('rect')
    tab.stroke([(2,2),(CW*sx-2,CH*sy-2)])
    await tab.tool('brush')
    cursize = None; gi = 0
    for (pi, bsize, ki) in sorted(sbc.keys()):
        if bsize != cursize:
            await tab.size(bsize); cursize = bsize
        await tab.set_color(1, tuple(int(v) for v in palette[ki]))
        pts_list = [[(x*sx, y*sy) for x,y in st] for st in sbc[(pi,bsize,ki)]]
        for i in range(0, len(pts_list), 120):
            tab.batch(pts_list[i:i+120])
        gi += 1
        if gi % 12 == 0:
            await tab.sync()   # let the renderer catch up; prevents the flood that crashed it
    await tab.sync()
    dt = time.time()-t0
    print(f"DONE {total} strokes in {dt:.1f}s = {total/dt:,.0f} strokes/s", flush=True)
    await tab.png("repro_fast.png")
    await tab.close(); await br.close()
asyncio.run(main())
