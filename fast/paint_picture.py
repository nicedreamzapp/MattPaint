"""Repaint any picture in MattPaint, slowly enough to watch it being built (2026-09-18).

    python3 paint_picture.py PICTURE.png [SECONDS]      default ~60 s

Big soft blocks first, then smaller and smaller dabs, then the sharp edges, each pass laid down
in random order so it reads like painting, not printing. Uses Matt's fixed window size
(paint_window.json via g5lib.open_canvas). Saves the result in pictures/ as *_painted.png.
"""
import asyncio, math, random, sys, time
from pathlib import Path
import numpy as np
from PIL import Image
import g5lib

SRC = Path(sys.argv[1]).expanduser()
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
LONG = 1200                                      # canvas long side in px


def passes(arr):
    H, W, _ = arr.shape
    out = []
    for cell in (40, 16, 7, 3):                  # coarse -> fine dabs, exact average colour
        ops = []
        for y in range(0, H, cell):
            for x in range(0, W, cell):
                c = arr[y:y + cell, x:x + cell].reshape(-1, 3).mean(0)
                ops.append([0, x, y, cell, cell, int(c[0]), int(c[1]), int(c[2])])
        random.shuffle(ops)
        out.append((f"{cell}px dabs", ops))
    g = arr.astype(np.float32).mean(2)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]; gy[1:-1, :] = g[2:, :] - g[:-2, :]
    mag = np.hypot(gx, gy)
    ops = []
    for cy in range(2, H - 2, 2):                # edge strokes along the contours
        for cx in range(2, W - 2, 2):
            n = mag[cy, cx]
            if n < 16:
                continue
            ux, uy = -gy[cy, cx] / n, gx[cy, cx] / n
            c = arr[cy, cx]
            ops.append([1, round(float(cx - ux * 2.6), 1), round(float(cy - uy * 2.6), 1), round(float(cx + ux * 2.6), 1),
                        round(float(cy + uy * 2.6), 1), 1.6, int(c[0]), int(c[1]), int(c[2])])
    random.shuffle(ops)
    out.append(("edges", ops))
    return out


async def main():
    im = Image.open(SRC).convert("RGB")
    k = LONG / max(im.size)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    arr = np.asarray(im, dtype=np.int16)
    plan = passes(arr)
    total = sum(len(o) for _, o in plan)
    br, tab = await g5lib.open_canvas(im.width, im.height)
    t0 = time.time()
    done = 0
    for name, ops in plan:
        print(f"   painting {name} ({len(ops):,})", flush=True)
        chunk = max(300, len(ops) // 120)
        for i in range(0, len(ops), chunk):
            part = ops[i:i + chunk]
            tab.fast(part); await tab.sync()
            done += len(part)
            wait = t0 + SECS * done / total - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
    tab.fast_commit(); await tab.sync()
    out = Path(__file__).with_name("pictures") / (SRC.stem + "_painted.png")
    out.parent.mkdir(exist_ok=True)
    await tab.png(str(out))
    print(f"done: {total:,} strokes in {time.time() - t0:.0f}s -> {out}", flush=True)
    await br.close()


asyncio.run(main())
