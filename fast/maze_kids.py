"""Kid-friendly circular maze: ten wide rainbow rings, chunky rounded walls, a bunny at the gate
and a carrot in the middle. One path through (perfect maze), short enough for a kid to trace
with a finger. Painted into MattPaint on screen; the solution is NOT drawn, that part is theirs.
"""
import asyncio, sys, time, math, random, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine import Browser, launch_brave, paint_url

W, H = 1400, 900
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
SS = 3
CX, CY = 860, 455
R0, RW = 70.0, 38.0
NR = 9
RMAX = R0 + NR * RW
WALLW = 9                       # wall thickness, px
BG = (255, 250, 236); INK = (72, 46, 110)

# ---------- the maze ----------
ncell = []; n = 6
for i in range(NR):
    r = R0 + (i + 0.5) * RW
    if 2 * math.pi * r / n > 1.9 * RW: n *= 2
    ncell.append(n)
in_open = [[False] * k for k in ncell]
ccw_open = [[False] * k for k in ncell]
def parent(i, j): return (i - 1, j * ncell[i - 1] // ncell[i])
def children(i, j):
    if i + 1 >= NR: return []
    f = ncell[i + 1] // ncell[i]
    return [(i + 1, j * f + k) for k in range(f)]
def nbrs(i, j):
    n = ncell[i]; out = [(i, (j - 1) % n), (i, (j + 1) % n)] + children(i, j)
    if i > 0: out.append(parent(i, j))
    return out
def open_between(a, b):
    if a[0] == b[0]:
        k = b[1] if (a[1] + 1) % ncell[a[0]] == b[1] else a[1]
        ccw_open[a[0]][k] = True
    else:
        o = a if a[0] > b[0] else b
        in_open[o[0]][o[1]] = True

GATE = (NR - 1, ncell[-1] // 2 - 1)              # left side, facing the bunny
GATE_Y = CY + (RMAX) * math.sin(math.radians((GATE[1] + 0.5) * 360 / ncell[-1]))

def connected(a, b):
    if a[0] == b[0]:
        k = b[1] if (a[1] + 1) % ncell[a[0]] == b[1] else a[1]
        return ccw_open[a[0]][k]
    o = a if a[0] > b[0] else b
    return in_open[o[0]][o[1]]

def carve(seed):
    """growing tree (newest 55% / random 45%): it branches all along the way. A pure backtracker
    from the gate made its first long run the answer, with zero forks on it (2026-09-22)."""
    global in_open, ccw_open
    in_open = [[False] * k for k in ncell]; ccw_open = [[False] * k for k in ncell]
    rnd = random.Random(seed)
    seen = [[False] * k for k in ncell]
    live = [GATE]; seen[GATE[0]][GATE[1]] = True
    while live:
        idx = len(live) - 1 if rnd.random() < 0.55 else rnd.randrange(len(live))
        c = live[idx]
        opts = [b for b in nbrs(*c) if not seen[b[0]][b[1]]]
        if not opts: live.pop(idx); continue
        b = rnd.choice(opts); open_between(c, b); seen[b[0]][b[1]] = True; live.append(b)
    hub = rnd.randrange(ncell[0]); in_open[0][hub] = True
    return hub

def grade(hub):
    """route from the gate to the carrot, and how many forks on it are real choices
    (the wrong turn leads into 4+ rooms, so it takes a look to rule out)"""
    from collections import deque
    prev = {GATE: None}; q = deque([GATE])
    while q:
        c = q.popleft()
        for b in set(nbrs(*c)):
            if b not in prev and connected(c, b): prev[b] = c; q.append(b)
    route = []; c = (0, hub)
    while c: route.append(c); c = prev[c]
    on = set(route); good = 0
    for c in route:
        for b in set(nbrs(*c)):
            if b in on or not connected(c, b): continue
            size, st, vis = 0, [b], {b}
            while st:
                x = st.pop(); size += 1
                for y in set(nbrs(*x)):
                    if y not in on and y not in vis and connected(x, y): vis.add(y); st.append(y)
            good += size >= 4
    return len(route), good

best = None
for sd in range(SEED * 1000, SEED * 1000 + 400):     # keep the maze with the most real choices
    n_route, forks = grade(carve(sd))
    if 35 <= n_route <= 70 and (best is None or forks > best[0]): best = (forks, sd, n_route)
FORKS, BEST_SEED, ROUTE_LEN = best
HUB = carve(BEST_SEED)
print(f"maze {BEST_SEED}: {sum(ncell)} rooms, route {ROUTE_LEN} rooms, {FORKS} real choices on the way", flush=True)

# ---------- draw it (supersampled, then painted) ----------
def S(v): return v * SS
def pt(r, deg):
    a = math.radians(deg); return (S(CX + r * math.cos(a)), S(CY + r * math.sin(a)))
def disc(d, x, y, r, fill, outline=None, w=0):
    d.ellipse([S(x - r), S(y - r), S(x + r), S(y + r)], fill=fill, outline=outline, width=S(w))

def render():
    im = Image.new("RGB", (W * SS, H * SS), BG); d = ImageDraw.Draw(im)
    # soft polka dots on the paper
    rnd = random.Random(3)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        if math.hypot(x - CX, y - CY) < RMAX + 30 or (x < 470 and y < 330): continue
        h = rnd.random(); c = tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, 0.90, 0.7))
        disc(d, x, y, rnd.uniform(5, 12), c)
    # rainbow rings (the floor of each corridor)
    disc(d, CX, CY, RMAX + 16, (255, 255, 255), INK, 4)
    ga = (GATE[1] + 0.5) * 360 / ncell[-1]; gs = 360 / ncell[-1] * 0.5   # gap in the frame at the gate
    d.pieslice([S(CX - RMAX - 22), S(CY - RMAX - 22), S(CX + RMAX + 22), S(CY + RMAX + 22)], ga - gs, ga + gs, fill=BG)
    for i in reversed(range(NR)):
        c = tuple(int(v * 255) for v in colorsys.hls_to_rgb(i / NR * 0.85, 0.86, 0.75))
        disc(d, CX, CY, R0 + (i + 1) * RW, c)
    disc(d, CX, CY, R0, (255, 236, 150))
    # walls: arcs + radial spokes with round caps
    cap = WALLW / 2
    def arc(r, a0, a1):
        R = r + WALLW / 2                           # PIL strokes arcs inside the box
        d.arc([S(CX - R), S(CY - R), S(CX + R), S(CY + R)], a0, a1, fill=INK, width=S(WALLW))
        for a in (a0, a1):
            x, y = pt(r, a); d.ellipse([x - S(cap), y - S(cap), x + S(cap), y + S(cap)], fill=INK)
    def spoke(a, r0, r1):
        p, q = pt(r0, a), pt(r1, a); d.line([p, q], fill=INK, width=S(WALLW))
        for x, y in (p, q): d.ellipse([x - S(cap), y - S(cap), x + S(cap), y + S(cap)], fill=INK)
    for i in range(NR):
        n = ncell[i]; step = 360 / n; r = R0 + i * RW
        for j in range(n):
            if not in_open[i][j]: arc(r, j * step, (j + 1) * step)
            if not ccw_open[i][j]: spoke(j * step, r, r + RW)
    n = ncell[-1]; step = 360 / n
    for j in range(n):
        if j != GATE[1]: arc(RMAX, j * step, (j + 1) * step)
    # the carrot in the middle
    cx, cy = CX, CY + 8
    d.polygon([(S(cx - 17), S(cy - 22)), (S(cx + 17), S(cy - 22)), (S(cx), S(cy + 34))],
              fill=(245, 128, 30), outline=(150, 70, 20), width=S(3))
    for k in (-8, 0, 8):
        d.line([(S(cx - 9), S(cy - 6 + k * 0.9 + 8)), (S(cx - 1), S(cy - 4 + k * 0.9 + 8))], fill=(190, 90, 20), width=S(3))
    for ang in (-35, 0, 35):
        a = math.radians(ang - 90)
        d.ellipse([S(cx + 18 * math.cos(a) - 7), S(cy - 22 + 18 * math.sin(a) - 11),
                   S(cx + 18 * math.cos(a) + 7), S(cy - 22 + 18 * math.sin(a) + 11)],
                  fill=(70, 180, 70), outline=(30, 110, 40), width=S(2))
    # the bunny at the gate
    gx, gy = CX - RMAX - 105, GATE_Y - 10
    white, pink, line_c = (255, 255, 255), (255, 170, 190), (80, 60, 90)
    for dx, tilt in ((-16, -10), (16, 10)):                      # ears
        ear = Image.new("RGBA", (S(40), S(110)), (0, 0, 0, 0)); e = ImageDraw.Draw(ear)
        e.ellipse([S(2), S(2), S(38), S(108)], fill=white, outline=line_c, width=S(4))
        e.ellipse([S(12), S(18), S(28), S(92)], fill=pink)
        ear = ear.rotate(-tilt, resample=Image.BICUBIC, expand=True)
        im.paste(ear, (int(S(gx + dx) - ear.width / 2), int(S(gy - 115))), ear)
    disc(d, gx, gy + 70, 52, white, line_c, 4)                  # body
    disc(d, gx + 48, gy + 88, 14, white, line_c, 3)               # tail
    disc(d, gx, gy, 46, white, line_c, 4)                         # head
    for ex in (-17, 17):
        disc(d, gx + ex, gy - 6, 8, (40, 30, 50)); disc(d, gx + ex + 3, gy - 9, 3, white)
    disc(d, gx - 26, gy + 14, 9, (255, 190, 200)); disc(d, gx + 26, gy + 14, 9, (255, 190, 200))
    disc(d, gx, gy + 8, 6, (240, 110, 140))
    d.arc([S(gx - 12), S(gy + 6), S(gx), S(gy + 20)], 0, 180, fill=line_c, width=S(3))
    d.arc([S(gx), S(gy + 6), S(gx + 12), S(gy + 20)], 0, 180, fill=line_c, width=S(3))
    for fx in (-26, 26): disc(d, gx + fx, gy + 118, 18, white, line_c, 4)   # feet
    # arrow from bunny into the gate
    ax0, ax1 = gx + 62, CX - RMAX - 22
    d.line([(S(ax0), S(GATE_Y)), (S(ax1), S(GATE_Y))], fill=(240, 90, 60), width=S(8))
    d.polygon([(S(ax1 + 16), S(GATE_Y)), (S(ax1 - 4), S(GATE_Y - 14)), (S(ax1 - 4), S(GATE_Y + 14))], fill=(240, 90, 60))
    # title
    f1 = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", S(54))
    f2 = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", S(30))
    words = [("Help", (240, 90, 60)), ("Bunny", (120, 80, 200)), ("find the", (40, 150, 200)), ("carrot!", (245, 128, 30))]
    y = 50
    for w_, c in words:
        d.text((S(46), S(y)), w_, font=f1, fill=c, stroke_width=S(3), stroke_fill=(255, 255, 255)); y += 66
    d.text((S(50), S(H - 70)), "Start at the arrow. Don't cross a line!", font=f2, fill=INK)
    return np.asarray(im.resize((W, H), Image.LANCZOS))

def to_ops(img):
    ops = []; q = img // 4 * 4
    for y in range(H):
        row = q[y]; ch = np.nonzero(np.any(row[1:] != row[:-1], axis=1))[0] + 1
        for s, e in zip(np.r_[0, ch], np.r_[ch, W]):
            c = row[s]; ops.append([0, int(s), y, int(e - s), 1, int(c[0]), int(c[1]), int(c[2])])
    return ops

async def main():
    img = render(); ops = to_ops(img); print(f"{len(ops)} ops", flush=True)
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url())
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    await asyncio.sleep(1.0)
    for i in range(0, len(ops), 1500):
        tab.fast(ops[i:i + 1500]); await tab.sync(); await asyncio.sleep(0.03)
    await tab.png("maze_kids.png")
    await br.close()                                   # the paint window stays up

asyncio.run(main())
