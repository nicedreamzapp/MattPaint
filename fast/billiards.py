"""Photoreal still: a pool table just after the break, low camera, cue lined up on the cue ball.
A Monte Carlo path tracer written from scratch in numpy: area-lit by the table lamp with
next-event estimation, clearcoat balls (Fresnel), numbered decals, felt, a varnished rail with
diamond sights, a chalk cube, thin-lens depth of field with bokeh from bar lights behind.
Rendered across CPU cores, then painted into MattPaint on screen (preview pass, then final).
"""
import asyncio, sys, time, math, os
import numpy as np
from multiprocessing import get_context
from PIL import Image, ImageDraw, ImageFont
from engine import Browser, launch_brave, paint_url

W, H = 1400, 900
SPP = 384
PREVIEW = 12
WORKERS = 14
BOUNCES = 4
f32 = np.float32
np.seterr(all="ignore")          # Accelerate matmul raises spurious fp warnings

def norm(v): return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-9)

# ---------------- scene ----------------
BALLS = [  # number, x, z, color (linear), stripe
    (0,   1.25,   3.0, (0.80, 0.78, 0.70), False),
    (8,  -1.10,  -5.2, (0.012, 0.012, 0.014), False),
    (3,   3.60,  -1.6, (0.62, 0.030, 0.025), False),
    (1,  -4.60,  -2.2, (0.85, 0.52, 0.02), False),
    (11,  0.90, -10.5, (0.55, 0.035, 0.03), True),
    (6,  -6.30,  -9.2, (0.02, 0.24, 0.07), False),
    (13,  5.20, -13.4, (0.85, 0.25, 0.02), True),
    (2,  -2.60, -15.6, (0.02, 0.07, 0.42), False),
    (9,   7.40,  -7.1, (0.85, 0.52, 0.02), True),
    (4,  10.50, -18.5, (0.16, 0.03, 0.26), False),
    (5,  -9.80, -17.0, (0.85, 0.25, 0.02), False),
    (7,  -12.5,  -6.5, (0.20, 0.02, 0.02), False),
]
NB = len(BALLS)
BC = np.array([[b[1], 1.0, b[2]] for b in BALLS], f32)
BCOL = np.array([b[3] for b in BALLS], f32)
BSTRIPE = np.array([b[4] for b in BALLS])
CAM = np.array([-2.2, 2.35, 11.8], f32)
rng0 = np.random.default_rng(11)
def rot_facing(center, i):
    """random-looking orientation, but most number circles turned partly toward the camera"""
    if BALLS[i][0] == 0: return np.eye(3, dtype=f32)
    toward = norm((CAM - center)[None])[0]
    z = norm((toward * 0.75 + rng0.normal(size=3) * 0.55)[None])[0]
    x = norm(np.cross(rng0.normal(size=3), z)[None])[0]
    y = np.cross(z, x)
    return np.stack([x, y, z]).astype(f32)             # rows: local axes in world space
BROT = np.stack([rot_facing(BC[i], i) for i in range(NB)])

# number decals: white disc + black number, 128px each
def make_decals():
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 70)
    out = np.zeros((NB, 128, 128), f32)
    for i, b in enumerate(BALLS):
        if b[0] == 0: continue
        im = Image.new("L", (128, 128), 0); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, 127, 127], fill=255)
        s = str(b[0]); bb = d.textbbox((0, 0), s, font=font)
        d.text((64 - (bb[0] + bb[2]) / 2, 64 - (bb[1] + bb[3]) / 2), s, font=font, fill=20)
        out[i] = np.asarray(im, f32) / 255
    return out
DECAL = make_decals()
DEC_COS = math.cos(math.radians(22)); DEC_SIN = math.sin(math.radians(22))

# boxes: cushion (felt), rail (wood), chalk
BOXES = np.array([
    [-60, 0.0, -23.6, 60, 1.30, -22.0],     # cushion
    [-60, 0.0, -31.0, 60, 1.52, -23.6],     # rail
    [7.2, 1.52, -26.3, 9.0, 3.12, -24.5],   # chalk cube on the rail
], f32)
# cue stick: tip just behind the cue ball, aimed through it
AIM = norm(np.array([[-0.52, -0.05, -1.0]], f32))[0]
CUE_T = BC[0] - AIM * 1.55                              # tip
CUE_B = CUE_T - AIM * 70.0                              # butt, far out of frame
CUE_R = 0.46
# lamp: rectangle facing down
LAMP_Y, LX0, LX1, LZ0, LZ1 = 34.0, -22.0, 22.0, -26.0, 4.0
LAMP_A = (LX1 - LX0) * (LZ1 - LZ0)
LAMP_LE = np.array([1.0, 0.86, 0.66], f32) * 5.2
# bar lights far behind (bokeh)
rb = np.random.default_rng(4)
BOKEH = np.array([[rb.uniform(-90, 90), rb.uniform(6, 34), rb.uniform(-190, -140)] for _ in range(22)], f32)
BOKEH_R = 1.6
BOKEH_C = np.array([[1.0, 0.55, 0.18], [1.0, 0.72, 0.35], [0.95, 0.25, 0.20], [0.35, 0.55, 1.0]], f32)[
    rb.integers(0, 4, len(BOKEH))] * rb.uniform(3, 9, (len(BOKEH), 1)).astype(f32)

# ids: 0..NB-1 balls, NB felt, NB+1.. boxes, CUE, LAMP, BOK
FELT = NB; BOX0 = NB + 1; CUE = BOX0 + len(BOXES); LAMP = CUE + 1; BOK = LAMP + 1

def hit_spheres(o, d, C, r, tbest, ibest, base):
    for i in range(len(C)):
        oc = o - C[i]
        b = (oc * d).sum(1); c = (oc * oc).sum(1) - r * r
        disc = b * b - c
        m = disc > 0
        sq = np.sqrt(np.where(m, disc, 0))
        t = -b - sq
        t = np.where(t > 1e-4, t, -b + sq)
        ok = m & (t > 1e-4) & (t < tbest)
        tbest[ok] = t[ok]; ibest[ok] = base + i

def intersect(o, d):
    n = len(o)
    t = np.full(n, np.inf, f32); idx = np.full(n, -1, np.int32)
    hit_spheres(o, d, BC, 1.0, t, idx, 0)
    # felt plane y=0 (in front of the cushion)
    tp = -o[:, 1] / np.where(np.abs(d[:, 1]) < 1e-9, -1e-9, d[:, 1])
    zp = o[:, 2] + d[:, 2] * tp
    ok = (tp > 1e-4) & (tp < t) & (zp > -22.0)
    t[ok] = tp[ok]; idx[ok] = FELT
    inv = 1.0 / np.where(np.abs(d) < 1e-9, 1e-9, d)
    for k, bx in enumerate(BOXES):
        t1 = (bx[:3] - o) * inv; t2 = (bx[3:] - o) * inv
        tn = np.minimum(t1, t2).max(1); tf = np.maximum(t1, t2).min(1)
        ok = (tf >= tn) & (tn > 1e-4) & (tn < t)
        t[ok] = tn[ok]; idx[ok] = BOX0 + k
    # cue (finite cylinder + tip cap)
    po = o - CUE_B; ax = AIM
    L = float(np.linalg.norm(CUE_T - CUE_B))
    dpar = d @ ax; opar = po @ ax
    dp = d - dpar[:, None] * ax; op = po - opar[:, None] * ax
    a = (dp * dp).sum(1); b = (dp * op).sum(1); c = (op * op).sum(1) - CUE_R ** 2
    disc = b * b - a * c
    m = (disc > 0) & (a > 1e-9)
    tc = (-b - np.sqrt(np.where(m, disc, 0))) / np.where(a > 1e-9, a, 1)
    s = opar + dpar * tc
    ok = m & (tc > 1e-4) & (tc < t) & (s > 0) & (s < L)
    t[ok] = tc[ok]; idx[ok] = CUE
    tcap = (L - opar) / np.where(np.abs(dpar) < 1e-9, 1e-9, dpar)
    pc = po + d * tcap[:, None] - L * ax
    ok = (tcap > 1e-4) & (tcap < t) & ((pc * pc).sum(1) < CUE_R ** 2)
    t[ok] = tcap[ok]; idx[ok] = CUE
    # lamp
    tl = (LAMP_Y - o[:, 1]) / np.where(np.abs(d[:, 1]) < 1e-9, 1e-9, d[:, 1])
    xl = o[:, 0] + d[:, 0] * tl; zl = o[:, 2] + d[:, 2] * tl
    ok = (tl > 1e-4) & (tl < t) & (xl > LX0) & (xl < LX1) & (zl > LZ0) & (zl < LZ1)
    t[ok] = tl[ok]; idx[ok] = LAMP
    hit_spheres(o, d, BOKEH, BOKEH_R, t, idx, BOK)
    return t, idx

def occluded(o, d, tmax):
    t, idx = intersect(o, d)
    return (t < tmax * 0.999) & (idx < LAMP)

def hash3(p):
    return np.modf(np.abs(np.sin(p[:, 0] * 12.9898 + p[:, 1] * 78.233 + p[:, 2] * 37.719) * 43758.5453))[0]

def value_noise(x, y):
    xi, yi = np.floor(x), np.floor(y); xf, yf = x - xi, y - yi
    def h(a, b): return np.modf(np.abs(np.sin(a * 127.1 + b * 311.7) * 43758.5453))[0]
    u = xf * xf * (3 - 2 * xf); v = yf * yf * (3 - 2 * yf)
    return (h(xi, yi) * (1 - u) + h(xi + 1, yi) * u) * (1 - v) + (h(xi, yi + 1) * (1 - u) + h(xi + 1, yi + 1) * u) * v

def env(d):
    """the dark bar room behind: warm, dim, a little lighter near the floor line"""
    y = d[:, 1]
    c = np.array([0.020, 0.014, 0.010], f32)[None] * (1.0 + 0.8 * np.clip(-y * 4 + 0.6, 0, 1))[:, None]
    return c

def material(p, n, idx, d):
    """albedo, clearcoat F0, gloss roughness per hit"""
    k = len(p)
    alb = np.zeros((k, 3), f32); f0 = np.zeros(k, f32); rough = np.full(k, 0.02, f32)
    ball = idx < NB
    if ball.any():
        bi = idx[ball]
        loc = np.einsum('nij,nj->ni', BROT[bi], n[ball])       # normal in ball space
        col = BCOL[bi].copy()
        stripe = BSTRIPE[bi]
        white = np.array([0.80, 0.78, 0.70], f32)
        col = np.where((stripe & (np.abs(loc[:, 0]) > 0.52))[:, None], white[None], col)
        pole = np.abs(loc[:, 2]) > DEC_COS
        num = BALLS_NUM[bi] > 0
        dm = pole & num
        if dm.any():
            u = loc[dm, 0] * np.sign(loc[dm, 2]) / DEC_SIN; v = -loc[dm, 1] / DEC_SIN
            px = np.clip(((u + 1) * 64).astype(int), 0, 127); py = np.clip(((v + 1) * 64).astype(int), 0, 127)
            g = DECAL[bi[dm], py, px]
            c2 = col[dm]
            ink = np.array([0.012, 0.012, 0.012], f32)
            c2 = np.where((g > 0.5)[:, None], white[None] * np.ones_like(c2), c2)
            c2 = np.where(((g > 0.02) & (g < 0.5))[:, None], ink[None] * np.ones_like(c2), c2)
            col[dm] = c2
        alb[ball] = col; f0[ball] = 0.05; rough[ball] = 0.012
    fl = (idx == FELT) | (idx == BOX0)
    if fl.any():
        q = p[fl]
        nz = value_noise(q[:, 0] * 9, q[:, 2] * 9) * 0.5 + value_noise(q[:, 0] * 37, q[:, 2] * 37) * 0.5
        wear = value_noise(q[:, 0] * 0.25 + 3, q[:, 2] * 0.25) * 0.10
        base = np.array([0.030, 0.205, 0.105], f32)
        alb[fl] = base[None] * (0.86 + 0.28 * nz + wear)[:, None]
    rail = idx == BOX0 + 1
    if rail.any():
        q = p[rail]
        top = n[rail, 1] > 0.5
        g = q[:, 0] * 1.1 + 2.2 * np.sin(q[:, 2] * 0.9 + q[:, 0] * 0.07) + 1.5 * value_noise(q[:, 0] * 0.3, q[:, 2] * 1.4)
        grain = 0.5 + 0.5 * np.sin(g * 3.0)
        dark = np.array([0.075, 0.022, 0.008], f32); light = np.array([0.20, 0.070, 0.025], f32)
        c = dark[None] * (1 - grain[:, None]) + light[None] * grain[:, None]
        # mother-of-pearl diamond sights along the rail top
        dx = np.abs(((q[:, 0] + 7.5) % 15.0) - 7.5); dz = np.abs(q[:, 2] + 27.0)
        dia = top & (dx / 0.45 + dz / 0.85 < 1)
        c = np.where(dia[:, None], np.array([0.75, 0.74, 0.70], f32)[None] * np.ones_like(c), c)
        alb[rail] = c; f0[rail] = 0.045; rough[rail] = 0.05
    chalk = idx == BOX0 + 2
    if chalk.any():
        q = p[chalk]
        top = n[chalk, 1] > 0.5
        r2 = (q[:, 0] - 8.1) ** 2 + (q[:, 2] + 25.4) ** 2
        c = np.where(top[:, None] & (r2 < 0.45)[:, None], np.array([[0.10, 0.28, 0.62]], f32) * 0.55,
                     np.array([[0.06, 0.20, 0.55]], f32))
        c = np.where(top[:, None] & (r2 >= 0.45)[:, None], np.array([[0.55, 0.55, 0.50]], f32), c)
        alb[chalk] = c
    cue = idx == CUE
    if cue.any():
        s = (p[cue] - CUE_B) @ AIM
        L = float(np.linalg.norm(CUE_T - CUE_B))
        fromtip = L - s
        maple = np.array([0.62, 0.45, 0.24], f32)
        c = np.where((fromtip < 0.42)[:, None], np.array([[0.05, 0.12, 0.40]], f32),
             np.where((fromtip < 1.35)[:, None], np.array([[0.82, 0.80, 0.74]], f32), maple[None]))
        grain = value_noise(s * 3.0, np.arctan2(p[cue, 1] - 1, p[cue, 0]) * 2) * 0.15
        c = c * (0.92 + grain)[:, None]
        alb[cue] = c; f0[cue] = np.where(fromtip < 0.42, 0.0, 0.04); rough[cue] = 0.06
    return alb, f0, rough

BALLS_NUM = np.array([b[0] for b in BALLS])

def normal_at(p, idx, d):
    n = np.zeros_like(p)
    ball = idx < NB
    n[ball] = norm(p[ball] - BC[idx[ball]])
    n[idx == FELT] = (0, 1, 0)
    for k, bx in enumerate(BOXES):
        m = idx == BOX0 + k
        if not m.any(): continue
        q = p[m]; c = (bx[:3] + bx[3:]) / 2; hs = (bx[3:] - bx[:3]) / 2
        rel = (q - c) / hs
        ax = np.abs(rel).argmax(1)
        nn = np.zeros_like(q); nn[np.arange(len(q)), ax] = np.sign(rel[np.arange(len(q)), ax])
        n[m] = nn
    cue = idx == CUE
    if cue.any():
        po = p[cue] - CUE_B; s = po @ AIM
        L = float(np.linalg.norm(CUE_T - CUE_B))
        radial = norm(po - s[:, None] * AIM)
        n[cue] = np.where((s > L - 1e-3)[:, None], AIM[None], radial)
    return n

def onb(n):
    s = np.where(n[:, 2:3] >= 0, 1.0, -1.0).astype(f32)
    a = -1.0 / (s[:, 0] + n[:, 2]); b = n[:, 0] * n[:, 1] * a
    t = np.stack([1 + s[:, 0] * n[:, 0] ** 2 * a, s[:, 0] * b, -s[:, 0] * n[:, 0]], 1)
    bb = np.stack([b, s[:, 0] + n[:, 1] ** 2 * a, -n[:, 1]], 1)
    return t, bb

def cosine_dir(n, rng):
    u1, u2 = rng.random(len(n), dtype=f32), rng.random(len(n), dtype=f32)
    r = np.sqrt(u1); ph = 2 * np.pi * u2
    t, b = onb(n)
    return norm(t * (r * np.cos(ph))[:, None] + b * (r * np.sin(ph))[:, None] + n * np.sqrt(1 - u1)[:, None])

# ---------------- camera + path tracing ----------------
LOOK = np.array([0.4, 0.75, -6.0], f32)
FWD = norm((LOOK - CAM)[None])[0]; RIGHT = norm(np.cross(FWD, [0, 1, 0])[None])[0]; UP = np.cross(RIGHT, FWD)
VFOV = math.radians(34); TH = math.tan(VFOV / 2)
FOCUS = float(np.linalg.norm(BC[0] - CAM)) - 0.3
APERTURE = 0.16

def trace_rows(args):
    y0, y1, spp, seed = args
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[y0:y1, 0:W]
    ys = ys.ravel().astype(f32); xs = xs.ravel().astype(f32)
    acc = np.zeros((len(xs), 3), f32)
    for s in range(spp):
        jx = xs + rng.random(len(xs), dtype=f32); jy = ys + rng.random(len(xs), dtype=f32)
        px = (jx / W * 2 - 1) * TH * (W / H); py = (1 - jy / H * 2) * TH
        d = norm(FWD[None] + RIGHT[None] * px[:, None] + UP[None] * py[:, None])
        fp = CAM[None] + d * (FOCUS / (d @ FWD))[:, None]
        r = APERTURE * np.sqrt(rng.random(len(xs), dtype=f32)); ph = rng.random(len(xs), dtype=f32) * 2 * np.pi
        # hexagonal-ish aperture feel is overkill; round lens
        o = CAM[None] + RIGHT[None] * (r * np.cos(ph))[:, None] + UP[None] * (r * np.sin(ph))[:, None]
        d = norm(fp - o)
        thr = np.ones((len(xs), 3), f32); rad = np.zeros((len(xs), 3), f32)
        alive = np.arange(len(xs)); spec = np.ones(len(xs), bool)
        for bounce in range(BOUNCES):
            if len(alive) == 0: break
            oo, dd = o[alive], d[alive]
            t, idx = intersect(oo, dd)
            miss = idx < 0
            rad[alive[miss]] += thr[alive[miss]] * env(dd[miss])
            em = idx >= LAMP
            if em.any():
                e = np.where((idx[em] == LAMP)[:, None], LAMP_LE[None], BOKEH_C[np.clip(idx[em] - BOK, 0, len(BOKEH) - 1)])
                cnt = spec[alive[em]]                               # lamp seen directly or in a reflection
                rad[alive[em]] += thr[alive[em]] * e * cnt[:, None]
            keep = ~miss & ~em
            alive = alive[keep]; t = t[keep]; idx = idx[keep]; dd = dd[keep]; oo = oo[keep]
            if len(alive) == 0: break
            p = oo + dd * t[:, None]
            n = normal_at(p, idx, dd)
            n = np.where(((n * dd).sum(1) > 0)[:, None], -n, n)
            alb, f0, rough = material(p, n, idx, dd)
            cosi = np.clip(-(n * dd).sum(1), 0, 1)
            F = f0 + (1 - f0) * (1 - cosi) ** 5 * (f0 > 0)
            # next-event estimation toward the lamp (diffuse part)
            lp = np.stack([rng.uniform(LX0, LX1, len(p)), np.full(len(p), LAMP_Y), rng.uniform(LZ0, LZ1, len(p))], 1).astype(f32)
            ld = lp - p; dist = np.linalg.norm(ld, axis=1); ld = ld / dist[:, None]
            cs = np.clip((n * ld).sum(1), 0, 1); cl = np.clip(ld[:, 1], 0, 1)
            so = p + n * 2e-3
            vis = ~occluded(so, ld, dist)
            direct = alb / np.pi * LAMP_LE[None] * (cs * cl * LAMP_A / (dist * dist) * vis * (1 - F))[:, None]
            rad[alive] += thr[alive] * direct
            # choose: specular (clearcoat) with prob F, else diffuse
            pick_spec = rng.random(len(p), dtype=f32) < F
            refl = dd - 2 * (dd * n).sum(1)[:, None] * n
            refl = norm(refl + rng.normal(0, 1, refl.shape).astype(f32) * rough[:, None])
            dif = cosine_dir(n, rng)
            nd = np.where(pick_spec[:, None], refl, dif)
            thr[alive] *= np.where(pick_spec[:, None], 1.0, alb)
            spec[alive] = pick_spec
            o[alive] = p + n * 2e-3; d[alive] = nd
        acc += rad
    return y0, (acc / spp).reshape(y1 - y0, W, 3)

def render(spp, seed):
    rows = [(y, min(y + 30, H), spp, seed * 10007 + y) for y in range(0, H, 30)]
    img = np.zeros((H, W, 3), f32)
    with get_context("fork").Pool(WORKERS) as pool:
        for y0, blk in pool.imap_unordered(trace_rows, rows):
            img[y0:y0 + len(blk)] = blk
    return img

def develop(hdr):
    hdr = np.nan_to_num(hdr).clip(0, 200)
    # bloom from the hot spots (lamp reflections, bokeh)
    hot = np.clip(hdr - 1.2, 0, None)
    from scipy.ndimage import gaussian_filter
    bloom = sum(gaussian_filter(hot, sigma=(s, s, 0)) * w for s, w in ((4, 0.10), (16, 0.06), (48, 0.04)))
    x = (hdr + bloom) * 1.35
    ldr = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)          # ACES
    ldr = np.power(np.clip(ldr, 0, 1), 1 / 2.2)
    vy, vx = np.mgrid[0:H, 0:W]
    v = 1 - 0.32 * (((vx / W - 0.5) ** 2 * 1.2 + (vy / H - 0.5) ** 2) * 2.2) ** 1.3
    ldr = ldr * v[..., None]
    grain = np.random.default_rng(1).normal(0, 0.006, ldr.shape[:2])[..., None]
    return np.clip((ldr + grain) * 255, 0, 255).astype(np.uint8)

def to_ops(img, q=2):
    ops = []; qi = img // q * q
    for y in range(img.shape[0]):
        row = qi[y]; ch = np.nonzero(np.any(row[1:] != row[:-1], axis=1))[0] + 1
        for s, e in zip(np.r_[0, ch], np.r_[ch, W]):
            c = row[s]; ops.append([0, int(s), y, int(e - s), 1, int(c[0]), int(c[1]), int(c[2])])
    return ops

async def paint(tab, img, chunk=6000):
    ops = to_ops(img)
    for i in range(0, len(ops), chunk):
        tab.fast(ops[i:i + chunk]); await tab.sync(); await asyncio.sleep(0.01)
    return len(ops)

async def main():
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url())
    import pt
    await tab.measure_canvas(); await tab.resize_canvas(W, H + pt.TOPBAR + 2)
    hdr = lambda im: pt.with_header(im, "Pool table after the break", len(to_ops(im)))
    t0 = time.time(); prev = render(PREVIEW, 1)
    print(f"preview {PREVIEW} spp in {time.time() - t0:.0f}s", flush=True)
    n = await paint(tab, hdr(develop(prev))); print(f"preview painted ({n} ops)", flush=True)
    t0 = time.time(); fin = render(SPP, 2)
    fin = (fin * SPP + prev * PREVIEW) / (SPP + PREVIEW)
    print(f"final {SPP} spp in {time.time() - t0:.0f}s", flush=True)
    n = await paint(tab, hdr(develop(fin))); print(f"final painted ({n} ops)", flush=True)
    await tab.png(os.path.join(pt.GALLERY, "01_billiards.png"))
    await br.close()                                   # the paint window stays up

if __name__ == "__main__":
    asyncio.run(main())
