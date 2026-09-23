"""The most intricate 2-D maze: a circular (theta) maze, ~60 rings, cells split as the rings grow
so every cell stays square. One perfect maze (single solution), carved by a recursive
backtracker. Painted into MattPaint on screen: the maze first, then the solution drawn in live
from the outer gate to the center.
"""
import asyncio, sys, time, math, random
from collections import deque
import numpy as np
from engine import Browser, launch_brave, paint_url

W, H = 1400, 900
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 22
CX, CY = W / 2, H / 2
R0 = 20.0          # center hub radius
RW = 6.6           # ring width (corridor + wall)
WALL = 0.95        # half wall thickness, px
RMAX = 436.0
SS = 3             # supersampling for smooth arcs

PAPER = np.array([246, 239, 222]); INK = np.array([34, 30, 44])

# ---------- the maze ----------
NR = int((RMAX - R0) // RW)
ncell = []
n = 10
for i in range(NR):
    r = R0 + (i + 0.5) * RW
    if 2 * math.pi * r / n > 1.9 * RW: n *= 2
    ncell.append(n)
in_open = [np.zeros(k, bool) for k in ncell]     # wall to the inward parent is open
ccw_open = [np.zeros(k, bool) for k in ncell]    # wall between cell j-1 and j is open

def parent(i, j): return (i - 1, j * ncell[i - 1] // ncell[i])
def children(i, j):
    if i + 1 >= NR: return []
    f = ncell[i + 1] // ncell[i]
    return [(i + 1, j * f + k) for k in range(f)]
def nbrs(i, j):
    n = ncell[i]
    out = [(i, (j - 1) % n), (i, (j + 1) % n)] + children(i, j)
    if i > 0: out.append(parent(i, j))
    return out
def open_between(a, b):
    if a[0] == b[0]:
        n = ncell[a[0]]
        k = b[1] if (a[1] + 1) % n == b[1] else a[1]
        ccw_open[a[0]][k] = True
    else:
        o = a if a[0] > b[0] else b
        in_open[o[0]][o[1]] = True
def connected(a, b):
    if a[0] == b[0]:
        n = ncell[a[0]]
        k = b[1] if (a[1] + 1) % n == b[1] else a[1]
        return ccw_open[a[0]][k]
    o = a if a[0] > b[0] else b
    return in_open[o[0]][o[1]]

random.seed(SEED)
seen = [np.zeros(k, bool) for k in ncell]
start = (NR - 1, random.randrange(ncell[-1]))
stack = [start]; seen[start[0]][start[1]] = True
while stack:
    c = stack[-1]
    opts = [b for b in nbrs(*c) if not seen[b[0]][b[1]]]
    if not opts: stack.pop(); continue
    b = random.choice(opts)
    open_between(c, b); seen[b[0]][b[1]] = True; stack.append(b)

GATE = (NR - 1, int(ncell[-1] * 0.62))           # outer entrance, lower-left
HUB = (0, random.randrange(ncell[0]))            # the one door into the center
in_open[0][HUB[1]] = True

prev = {GATE: None}; q = deque([GATE])
while q:
    c = q.popleft()
    if c == HUB: break
    for b in nbrs(*c):
        if b not in prev and connected(c, b): prev[b] = c; q.append(b)
route = []; c = HUB
while c: route.append(c); c = prev[c]
route.reverse()
print(f"{NR} rings, {sum(ncell)} cells, outer ring {ncell[-1]} cells, solution {len(route)} cells", flush=True)

# ---------- rasterise the walls ----------
def render():
    ys, xs = np.mgrid[0:H * SS, 0:W * SS]
    x = (xs + 0.5) / SS - CX; y = (ys + 0.5) / SS - CY
    r = np.hypot(x, y); a = (np.arctan2(y, x)) % (2 * math.pi)
    ink = np.zeros(r.shape, bool)
    rr = r - R0
    ring = np.floor(rr / RW).astype(int)
    b = np.round(rr / RW).astype(int)
    near_ring = np.abs(rr - b * RW) < WALL
    # circular walls
    for bi in range(NR + 1):
        m = near_ring & (b == bi)
        if not m.any(): continue
        if bi == NR:                                   # outer wall, gate left open
            n = ncell[-1]; j = np.floor(a[m] / (2 * math.pi) * n).astype(int) % n
            ink[m] = j != GATE[1]
        else:
            n = ncell[bi]; j = np.floor(a[m] / (2 * math.pi) * n).astype(int) % n
            ink[m] = ~in_open[bi][j]
    # radial walls
    inside = (ring >= 0) & (ring < NR)
    for i in range(NR):
        m = inside & (ring == i)
        n = ncell[i]
        f = a[m] / (2 * math.pi) * n
        k = np.round(f).astype(int)
        dist = np.abs(f - k) * 2 * math.pi * r[m] / n
        wall = (dist < WALL) & ~ccw_open[i][k % n]
        cur = ink[m]; cur |= wall; ink[m] = cur
    # outer decorative double ring and the hub medallion
    ink |= np.abs(r - (RMAX + 9)) < 1.6
    ink |= np.abs(r - (RMAX + 14)) < 0.7
    hub = r < R0 - 5
    cov = ink.reshape(H, SS, W, SS).mean(axis=(1, 3))
    hubc = hub.reshape(H, SS, W, SS).mean(axis=(1, 3))
    img = PAPER[None, None] * (1 - cov[..., None]) + INK[None, None] * cov[..., None]
    gold = np.array([214, 160, 40])
    img = img * (1 - hubc[..., None]) + gold[None, None] * hubc[..., None]
    # soft paper vignette
    vy, vx = np.mgrid[0:H, 0:W]
    v = 1 - 0.10 * (((vx / W - 0.5) ** 2 + (vy / H - 0.5) ** 2) * 2.2)
    return np.clip(img * v[..., None], 0, 255).astype(np.uint8)

def to_ops(img):
    ops = []
    q = img // 4 * 4
    for y in range(H):
        row = q[y]
        ch = np.nonzero(np.any(row[1:] != row[:-1], axis=1))[0] + 1
        for s, e in zip(np.r_[0, ch], np.r_[ch, W]):
            c = row[s]; ops.append([0, int(s), y, int(e - s), 1, int(c[0]), int(c[1]), int(c[2])])
    return ops

# ---------- the solution line, in drawing order ----------
def polar(r, a): return CX + r * math.cos(a), CY + r * math.sin(a)
def ctr(c):
    i, j = c; return R0 + (i + 0.5) * RW, (j + 0.5) / ncell[i] * 2 * math.pi
def arc(r, a0, a1):
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    k = max(2, int(abs(d) * r / 1.2))
    return [polar(r, a0 + d * t / k) for t in range(k + 1)]
def line(p, q):
    k = max(2, int(math.dist(p, q) / 1.2))
    return [(p[0] + (q[0] - p[0]) * t / k, p[1] + (q[1] - p[1]) * t / k) for t in range(k + 1)]
def solution_pts():
    r, a = ctr(route[0])
    pts = line(polar(RMAX + 26, a), polar(r, a))
    for c0, c1 in zip(route, route[1:]):
        r0, a0 = ctr(c0); r1, a1 = ctr(c1)
        if c0[0] == c1[0]: pts += arc(r0, a0, a1)
        else: pts += line(polar(r0, a0), polar(r1, a0)) + arc(r1, a0, a1)
    r, a = ctr(route[-1]); pts += line(polar(r, a), (CX, CY))
    return pts

def sol_ops(pts):
    ops = []; n = len(pts)
    c0 = np.array([226, 40, 70]); c1 = np.array([30, 120, 230])
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1); c = c0 * (1 - t) + c1 * t
        ops.append([0, int(round(x - 1.5)), int(round(y - 1.5)), 3, 3, int(c[0]), int(c[1]), int(c[2])])
    return ops

async def main():
    t0 = time.time(); img = render(); ops = to_ops(img)
    print(f"rasterised in {time.time() - t0:.1f}s, {len(ops)} ops", flush=True)
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url())
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    await asyncio.sleep(1.0)
    for i in range(0, len(ops), 3000):                 # the maze, top to bottom
        tab.fast(ops[i:i + 3000]); await tab.sync(); await asyncio.sleep(0.03)
    await tab.png("maze2d.png")
    await asyncio.sleep(2.5)                           # a beat to look at it unsolved
    s = sol_ops(solution_pts())
    for i in range(0, len(s), 60):                     # then solve it live, gate to center
        tab.fast(s[i:i + 60]); await tab.sync(); await asyncio.sleep(0.012)
    await tab.png("maze2d_solved.png")
    print(f"solution drawn: {len(s)} dabs", flush=True)
    await br.close()                                   # the paint window stays up

asyncio.run(main())
