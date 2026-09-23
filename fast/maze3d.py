"""A 3D stone maze, raytraced from scratch: random maze (recursive backtracker), block walls
traced with a grid DDA, sun shadows, ambient occlusion, brick courses, a glowing solved path.
Rendered with numpy, then painted into MattPaint on screen, scanline by scanline.
"""
import asyncio, sys, time, math, random
import numpy as np
from engine import Browser, launch_brave, paint_url

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1400
H = int(sys.argv[2]) if len(sys.argv) > 2 else 900
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 7
AA = 2
N = 11                      # maze is N x N rooms -> (2N+1)^2 grid of blocks
HW = 1.55                   # wall height (one block = 1 unit wide)

def norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-9)

# ---------- the maze ----------
def make_maze():
    random.seed(SEED)
    G = 2 * N + 1
    wall = np.ones((G, G), bool)
    seen = np.zeros((N, N), bool)
    stack = [(0, 0)]; seen[0, 0] = True; wall[1, 1] = False
    while stack:
        x, z = stack[-1]
        nb = [(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= x + dx < N and 0 <= z + dz < N and not seen[x + dx, z + dz]]
        if not nb:
            stack.pop(); continue
        nx, nz = random.choice(nb)
        seen[nx, nz] = True
        wall[2 * nx + 1, 2 * nz + 1] = False
        wall[x + nx + 1, z + nz + 1] = False
        stack.append((nx, nz))
    wall[1, 0] = False               # entrance
    wall[G - 2, G - 1] = False       # exit
    # solve with BFS for the glowing path
    from collections import deque
    start, goal = (1, 0), (G - 2, G - 1)
    prev = {start: None}; q = deque([start])
    while q:
        c = q.popleft()
        if c == goal: break
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dz)
            if 0 <= n[0] < G and 0 <= n[1] < G and not wall[n] and n not in prev:
                prev[n] = c; q.append(n)
    path = np.zeros((G, G), float)
    c = goal; k = 0; cells = []
    while c: cells.append(c); c = prev[c]
    cells.reverse()
    for i, c in enumerate(cells): path[c] = 1 + i / len(cells)   # 1..2 along the route
    return wall, path, start, goal

WALL, PATH, START, GOAL = make_maze()
G = WALL.shape[0]

# soft wall-proximity map for ambient occlusion on the floor
def blur_map(m, r=3):
    k = np.exp(-np.linspace(-2, 2, 2 * r + 1) ** 2)
    k /= k.sum()
    up = np.kron(m.astype(float), np.ones((8, 8)))           # 8 samples per block
    pad = np.pad(up, 8 * r // 2 + r, mode='edge')
    for ax in (0, 1):
        pad = np.apply_along_axis(lambda v: np.convolve(v, np.repeat(k, 4) / 4, 'same'), ax, pad)
    o = 8 * r // 2 + r
    return pad[o:o + up.shape[0], o:o + up.shape[1]]
AOMAP = blur_map(WALL)

def ao_at(x, z):
    ix = np.clip((x * 8).astype(int), 0, AOMAP.shape[0] - 1)
    iz = np.clip((z * 8).astype(int), 0, AOMAP.shape[1] - 1)
    inside = (x >= 0) & (x < G) & (z >= 0) & (z < G)
    return np.where(inside, AOMAP[ix, iz], 0.0)

# ---------- tracing ----------
SUN = norm(np.array([[-0.62, 0.48, -0.50]]))[0]
SUN_C = np.array([1.0, 0.84, 0.62]) * 1.9
SKY_AMB = np.array([0.50, 0.62, 0.92])

def trace(o, d):
    """first hit against the block grid + floor. returns t, kind (0 sky/far,1 floor,2 wall),
    normal axis (0 x,1 up,2 z) and step sign"""
    n = d.shape[0]
    inv = 1.0 / np.where(np.abs(d) < 1e-9, 1e-9, d)
    lo = np.array([0.0, 0.0, 0.0]); hi = np.array([G, HW, G], float)
    t1 = (lo[None] - o) * inv; t2 = (hi[None] - o) * inv
    tmin = np.minimum(t1, t2); tmax = np.maximum(t1, t2)
    tent = tmin.max(1); tex = tmax.min(1)
    ent_axis = tmin.argmax(1)
    hitbox = (tex > np.maximum(tent, 0))
    t = np.full(n, np.inf); kind = np.zeros(n, np.int8); nax = np.full(n, 1, np.int8)
    nsg = np.ones(n, np.int8)
    # floor outside the maze (y=0 plane) as a fallback
    tf = np.where(d[:, 1] < 0, -o[:, 1] * inv[:, 1], np.inf)
    idx = np.nonzero(hitbox)[0]
    tc = np.maximum(tent[idx], 0.0)
    oo = o[idx]; dd = d[idx]; iv = inv[idx]
    p = oo + dd * (tc + 1e-6)[:, None]
    ix = np.clip(np.floor(p[:, 0]).astype(int), 0, G - 1)
    iz = np.clip(np.floor(p[:, 2]).astype(int), 0, G - 1)
    sx = np.where(dd[:, 0] >= 0, 1, -1); sz = np.where(dd[:, 2] >= 0, 1, -1)
    tmx = ((ix + (sx > 0)) - oo[:, 0]) * iv[:, 0]
    tmz = ((iz + (sz > 0)) - oo[:, 2]) * iv[:, 2]
    dtx = np.abs(iv[:, 0]); dtz = np.abs(iv[:, 2])
    ax = np.where(tent[idx] > 0, ent_axis[idx], 1).astype(np.int8)   # axis of the face we came through
    asg = np.where(ax == 0, -sx, np.where(ax == 2, -sz, 1)).astype(np.int8)
    alive = np.ones(len(idx), bool)
    for _ in range(4 * G):
        a = np.nonzero(alive)[0]
        if len(a) == 0: break
        w = WALL[ix[a], iz[a]]
        # wall block: we are inside its column below HW -> hit at entry
        hw = a[w]
        if len(hw):
            g = idx[hw]; t[g] = tc[hw]; kind[g] = 2; nax[g] = ax[hw]; nsg[g] = asg[hw]
            alive[hw] = False
        a = a[~w]
        tn = np.minimum(tmx[a], tmz[a])
        y1 = oo[a, 1] + dd[a, 1] * tn
        fl = y1 <= 0
        hf = a[fl]
        if len(hf):
            g = idx[hf]; t[g] = -oo[hf, 1] * iv[hf, 1]; kind[g] = 1; nax[g] = 1; nsg[g] = 1
            alive[hf] = False
        a = a[~fl]
        up = (dd[a, 1] > 0) & (oo[a, 1] + dd[a, 1] * np.minimum(tmx[a], tmz[a]) > HW)
        alive[a[up]] = False
        a = a[~up]
        stepx = tmx[a] < tmz[a]
        ax_ = a[stepx]; az_ = a[~stepx]
        tc[ax_] = tmx[ax_]; ix[ax_] += sx[ax_]; tmx[ax_] += dtx[ax_]; ax[ax_] = 0; asg[ax_] = -sx[ax_]
        tc[az_] = tmz[az_]; iz[az_] += sz[az_]; tmz[az_] += dtz[az_]; ax[az_] = 2; asg[az_] = -sz[az_]
        out = (ix[a] < 0) | (ix[a] >= G) | (iz[a] < 0) | (iz[a] >= G)
        alive[a[out]] = False
    # anything unresolved: outside ground plane
    miss = (kind == 0) & np.isfinite(tf)
    t[miss] = tf[miss]; kind[miss] = 1; nax[miss] = 1
    return t, kind, nax, nsg

def sky(d):
    y = np.clip(d[:, 1], -0.2, 1)
    top = np.array([0.20, 0.38, 0.72]); hor = np.array([0.95, 0.80, 0.62])
    s = np.clip(y * 2.4, 0, 1) ** 0.7
    c = hor[None] * (1 - s)[:, None] + top[None] * s[:, None]
    sd = np.clip((d * SUN[None]).sum(1), 0, 1)
    return c + SUN_C[None] * (sd ** 1200 * 30 + sd ** 18 * 0.35)[:, None]

def hash2(a, b):
    return np.modf(np.sin(a * 127.1 + b * 311.7) * 43758.5453)[0] % 1.0

def shade(o, d):
    t, kind, nax, nsg = trace(o, d)
    col = sky(d)
    hit = kind > 0
    if not hit.any(): return col
    p = o[hit] + d[hit] * t[hit, None]
    nrm = np.zeros_like(p)
    ax = nax[hit]; sg = nsg[hit].astype(float)
    nrm[np.arange(len(p)), ax] = np.where(ax == 1, 1.0, sg)
    k = kind[hit]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    base = np.zeros_like(p)
    # ---- floor: pale gravel inside, meadow outside, glowing path ----
    fl = k == 1
    inside = (x >= 0) & (x < G) & (z >= 0) & (z < G)
    gx = np.floor(x * 3); gz = np.floor(z * 3)
    grit = hash2(gx, gz) * 0.10 + hash2(np.floor(x * 11), np.floor(z * 11)) * 0.06
    floor_in = np.array([0.74, 0.66, 0.52])
    meadow = np.array([0.36, 0.52, 0.24])
    mnoise = hash2(np.floor(x * 2), np.floor(z * 2)) * 0.12
    b_in = floor_in[None] * (0.90 + grit)[:, None]
    b_out = meadow[None] * (0.86 + mnoise)[:, None]
    base[fl] = np.where(inside[fl, None], b_in[fl], b_out[fl])
    # ---- walls: sandstone brick courses, lighter capstones ----
    wl = k == 2
    top = wl & (ax == 1)
    side = wl & (ax != 1)
    u = np.where(ax == 0, z, x)
    course = np.floor(y / 0.23)
    bx = np.floor(u / 0.5 + course * 0.5)
    mortar = (np.abs(y / 0.23 - np.round(y / 0.23)) < 0.07) | \
             (np.abs((u / 0.5 + course * 0.5) - np.round(u / 0.5 + course * 0.5)) < 0.05)
    stone = np.array([0.80, 0.62, 0.44])
    tint = (hash2(bx, course + 3 * np.floor(np.where(ax == 0, x, z))) - 0.5) * 0.18
    bs = stone[None] * (1 + tint)[:, None]
    bs = np.where(mortar[:, None], bs * 0.62, bs)
    cap = np.array([0.60, 0.50, 0.38])[None] * (0.94 + hash2(np.floor(x), np.floor(z)) * 0.08)[:, None]
    base[side] = bs[side]; base[top] = cap[top]
    # ---- light ----
    ndl = np.clip((nrm * SUN[None]).sum(1), 0, 1)
    sh = np.zeros(len(p), bool)
    lit = ndl > 0
    if lit.any():
        so = p[lit] + nrm[lit] * 2e-3
        ts, ks, _, _ = trace(so, np.broadcast_to(SUN[None], so.shape).copy())
        sd_ = np.broadcast_to(SUN[None], so.shape).copy()
        blk = (ks == 2) & np.isfinite(ts)
        for jit in ((0.012, 0, 0), (0, 0, 0.012)):        # close diagonal corner leaks in the DDA
            t2_, k2_, _, _ = trace(so + np.array(jit)[None], sd_)
            blk |= (k2_ == 2) & np.isfinite(t2_)
        sh[np.nonzero(lit)[0]] = blk
    ao = np.ones(len(p))
    ao[fl] = 1 - 0.55 * ao_at(x[fl], z[fl])
    ao[side] = 0.55 + 0.45 * np.clip(y[side] / HW, 0, 1) ** 0.6
    sky_term = np.where(ax == 1, 1.0, 0.7)
    light = SUN_C[None] * (ndl * ~sh)[:, None] + SKY_AMB[None] * (0.62 * ao * sky_term)[:, None]
    c = base * light
    # glowing solved path + start/goal pads (emissive, on the floor)
    ix = np.clip(np.floor(x).astype(int), 0, G - 1); iz = np.clip(np.floor(z).astype(int), 0, G - 1)
    pv = np.where(fl & inside, PATH[ix, iz], 0.0)
    on = pv > 0
    if on.any():
        fx = x - np.floor(x) - 0.5; fz = z - np.floor(z) - 0.5
        r = np.sqrt(fx ** 2 + fz ** 2)
        dot = np.clip(1 - r / 0.19, 0, 1) ** 0.6 * 1.6 + np.clip(1 - r / 0.55, 0, 1) ** 2 * 0.7
        f = pv - 1                                     # 0 at start .. 1 at goal
        glow = np.array([1.0, 0.78, 0.25])[None] * (1 - f)[:, None] + np.array([0.35, 0.95, 1.0])[None] * f[:, None]
        c = c * (1 - 0.5 * np.clip(dot, 0, 1) * on)[:, None] + (glow * (dot * 0.9)[:, None]) * on[:, None]
    for (cx, cz), cc in ((START, (0.3, 1.0, 0.45)), (GOAL, (1.0, 0.25, 0.25))):
        m = fl & (np.floor(x) == cx) & (np.floor(z) == cz)
        c[m] = c[m] * 0.6 + np.array(cc) * 1.4
    # distance haze
    fog = 1 - np.exp(-np.maximum(t[hit] - 34, 0) * 0.012)
    c = c * (1 - fog)[:, None] + np.array([0.95, 0.80, 0.62])[None] * fog[:, None]
    col[hit] = c
    return col

def render():
    ctr = np.array([G / 2, 0.0, G / 2])
    cam = ctr + np.array([-10.5, 20.0, 16.5])
    look = ctr + np.array([0.6, -0.5, -0.9])
    fwd = norm((look - cam)[None])[0]
    right = norm(np.cross(fwd, [0, 1, 0])[None])[0]
    up = np.cross(right, fwd)
    sh_ = math.tan(math.radians(51) / 2); aspect = W / H
    Wx, Hy = W * AA, H * AA
    ys, xs = np.mgrid[0:Hy, 0:Wx]
    px = ((xs + 0.5) / Wx * 2 - 1) * sh_ * aspect
    py = (1 - (ys + 0.5) / Hy * 2) * sh_
    d = norm(fwd[None, None] + right[None, None] * px[..., None] + up[None, None] * py[..., None]).reshape(-1, 3)
    out = np.zeros_like(d)
    CH = 300000
    for i in range(0, len(d), CH):
        dd = d[i:i + CH]
        out[i:i + CH] = shade(np.broadcast_to(cam[None], dd.shape).copy(), dd)
    hdr = np.nan_to_num(out).clip(0, 40).reshape(Hy, Wx, 3).reshape(H, AA, W, AA, 3).mean(axis=(1, 3))
    x_ = hdr * 0.62                                   # ACES filmic fit
    ldr = (x_ * (2.51 * x_ + 0.03)) / (x_ * (2.43 * x_ + 0.59) + 0.14)
    ldr = np.power(np.clip(ldr, 0, 1), 1 / 2.2)
    # vignette
    vy, vx = np.mgrid[0:H, 0:W]
    v = 1 - 0.28 * (((vx / W - 0.5) ** 2 + (vy / H - 0.5) ** 2) * 2) ** 1.4
    return np.clip(ldr * v[..., None] * 255, 0, 255).astype(np.uint8)

def to_ops(img):
    ops = []
    q = img // 3 * 3
    for y in range(H):
        row = q[y]
        change = np.nonzero(np.any(row[1:] != row[:-1], axis=1))[0] + 1
        starts = np.concatenate([[0], change]); ends = np.concatenate([change, [W]])
        for s, e in zip(starts, ends):
            c = row[s]
            ops.append([0, int(s), y, int(e - s), 1, int(c[0]), int(c[1]), int(c[2])])
    return ops

async def main():
    t0 = time.time(); img = render()
    print(f"raytraced {W}x{H} maze ({N}x{N} rooms, AA{AA}) in {time.time() - t0:.1f}s", flush=True)
    ops = to_ops(img); print(f"{len(ops)} paint ops", flush=True)
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url())
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    await asyncio.sleep(1.0)
    t1 = time.time()
    CHUNK = 2500                                   # small chunks so the picture visibly builds
    for i in range(0, len(ops), CHUNK):
        tab.fast(ops[i:i + CHUNK])
        await tab.sync()
        await asyncio.sleep(0.03)
    print(f"painted in {time.time() - t1:.1f}s", flush=True)
    await tab.png("maze3d.png")
    await br.close()                               # socket only; the paint window stays up

asyncio.run(main())
