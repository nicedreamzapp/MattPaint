"""Reproduce a reference photo in MattPaint by sampling real pixel colors.
Coarse blocks first, then finer brush strokes following the image's edges.
Every stroke uses the exact colour sampled from the photo — unlimited colours, that's the realism.
"""
import asyncio, sys, time, math
import numpy as np
from PIL import Image, ImageFilter
from engine import Browser

REF = sys.argv[1] if len(sys.argv) > 1 else "ref_eagle.png"
CW, CH = 1000, 500                    # canvas; reference is cropped/fit to this aspect
tab = None

def load_ref():
    im = Image.open(REF).convert("RGB")
    # center-crop to canvas aspect, then resize
    ar_c, ar_i = CW / CH, im.width / im.height
    if ar_i > ar_c:
        w = int(im.height * ar_c); im = im.crop(((im.width - w) // 2, 0, (im.width + w) // 2, im.height))
    else:
        h = int(im.width / ar_c); im = im.crop((0, (im.height - h) // 2, im.width, (im.height + h) // 2))
    im = im.resize((CW, CH), Image.LANCZOS)
    return im

def build_strokes(im):
    arr = np.asarray(im, dtype=np.float32)
    gray = arr.mean(2)
    gx = np.zeros_like(gray); gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    mag = np.hypot(gx, gy)
    strokes = []   # (x1,y1,x2,y2,(r,g,b),size,pass)
    # pass config: (cell px, brush size, stroke length factor, min-gradient to place)
    passes = [(34, 8, 1.4, 0), (18, 5, 1.5, 0), (10, 3, 1.6, 0), (6, 2, 1.7, 8), (3, 1, 1.8, 22)]
    for pi, (cell, bsize, lf, gmin) in enumerate(passes):
        step = cell
        for cy in range(cell // 2, CH, step):
            for cx in range(cell // 2, CW, step):
                y0, y1 = max(0, cy - cell // 2), min(CH, cy + cell // 2)
                x0, x1 = max(0, cx - cell // 2), min(CW, cx + cell // 2)
                patch = arr[y0:y1, x0:x1]
                if patch.size == 0: continue
                g = mag[y0:y1, x0:x1].mean()
                if g < gmin: continue
                col = patch.reshape(-1, 3).mean(0)
                # stroke direction: along the iso-luminance line (perpendicular to gradient)
                dx = gx[cy, cx]; dy = gy[cy, cx]
                n = math.hypot(dx, dy)
                if n < 1e-3:
                    ux, uy = 1.0, 0.0
                else:
                    ux, uy = -dy / n, dx / n          # perpendicular to gradient
                L = cell * lf / 2
                strokes.append((float(cx - ux * L), float(cy - uy * L), float(cx + ux * L), float(cy + uy * L),
                                (int(col[0]), int(col[1]), int(col[2])), int(bsize), pi))
    return strokes

def quant(c, q=6):
    return tuple((v // q) * q for v in c)

async def main():
    global tab
    im = load_ref()
    im.save("ref_fit.png")
    strokes = build_strokes(im)
    print(f"{len(strokes)} strokes", flush=True)
    br = Browser(9222); await br.connect()
    tab = await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas()
    t0 = time.time()
    await tab.resize_canvas(CW, CH)
    await tab.measure_canvas()
    sx = tab.canvas["w"] / CW; sy = tab.canvas["h"] / CH
    # base fill: average colour of the whole image, as one big rect, so gaps never show white
    avg = np.asarray(im).reshape(-1, 3).mean(0).astype(int)
    await tab.fill_mode('solid'); await tab.outline_mode('none')
    await tab.set_color(2, tuple(avg)); await tab.shape('rect')
    tab.stroke([(2, 2), (CW * sx - 2, CH * sy - 2)])
    # brush strokes, coarse to fine; group consecutive same-colour to cut colour sets
    await tab.tool('brush')
    cur = None
    # keep pass order (coarse->fine); within a pass sort by quantised colour to batch colour sets
    strokes.sort(key=lambda s: (s[6], quant(s[4])))
    await tab.size(8); cursize = 8
    for x1, y1, x2, y2, col, bs, pi in strokes:
        qc = quant(col)
        if bs != cursize:
            await tab.size(bs); cursize = bs
        if qc != cur:
            await tab.set_color(1, col); cur = qc
        tab.stroke([(x1 * sx, y1 * sy), ((x1 + x2) / 2 * sx, (y1 + y2) / 2 * sy), (x2 * sx, y2 * sy)])
    await tab.sync()
    dt = time.time() - t0
    print(f"painted {len(strokes)} strokes in {dt:.1f}s", flush=True)
    await tab.png("repro_out.png")
    await tab.close(); await br.close()
asyncio.run(main())
