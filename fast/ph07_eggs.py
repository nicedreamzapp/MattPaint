"""07 — farm eggs in a stoneware bowl on linen, soft kitchen window light."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def egg_profile(L=0.57, B=0.43, n=64):
    """egg outline (Hügelschäffer-style), 1 unit = 10 cm, lying base at y=0"""
    pts = [(0.0, 0.0)]
    for i in range(1, n):
        t = i / n; y = t * L
        x = (y - L / 2) / (L / 2)
        r = (B / 2) * math.sqrt(max(1 - x * x, 0)) * (1 + 0.13 * x)   # fatter at the blunt end
        pts.append((r, y))
    pts.append((0.0, L))
    return pts
EGG = egg_profile()

def speckle(base, amt):
    def t(pl, pw, n):
        s = fbm(pl[:, 0] * 60, pl[:, 1] * 60, pl[:, 2] * 60, oct=3)
        dots = np.clip((s - 0.62) * 6, 0, 1) * amt
        tone = 0.92 + 0.16 * fbm(pl[:, 0] * 6, pl[:, 1] * 6, pl[:, 2] * 6, oct=3)
        return (V(*base)[None] * tone[:, None] * (1 - dots[:, None] * 0.55)).astype(f32)
    return t
brown = Mat("plastic", tex=speckle((0.52, 0.27, 0.13), 1.0), f0=0.03, rough=0.35)
cream = Mat("plastic", tex=speckle((0.74, 0.62, 0.46), 0.6), f0=0.03, rough=0.35)
white = Mat("plastic", tex=speckle((0.80, 0.78, 0.74), 0.2), f0=0.03, rough=0.35)

def glaze_tex(pl, pw, n):
    r = np.sqrt(pl[:, 0] ** 2 + pl[:, 2] ** 2)
    s = fbm(pl[:, 0] * 30, pl[:, 1] * 30, pl[:, 2] * 30, oct=3)
    dots = np.clip((s - 0.66) * 8, 0, 1)
    pool = np.clip(1.2 - pl[:, 1] * 1.6, 0, 1)                 # glaze pools darker lower down
    base = V(0.10, 0.16, 0.20)[None] * (1 - 0.35 * pool[:, None]) + V(0.04, 0.03, 0.02)[None] * pool[:, None]
    rim = np.clip((pl[:, 1] - 0.93) * 25, 0, 1)                # raw clay showing at the rim
    c = base * (1 - dots[:, None] * 0.5) + V(0.45, 0.33, 0.22)[None] * dots[:, None] * 0.3
    return (c * (1 - rim[:, None]) + V(0.52, 0.40, 0.28)[None] * rim[:, None]).astype(f32)
stoneware = Mat("plastic", tex=glaze_tex, f0=0.05, rough=0.04)

def linen_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    weave = 0.5 + 0.25 * np.sin(x * 95) + 0.25 * np.sin(z * 95)
    slub = fbm(x * 3, z * 40, oct=3) * 0.5 + fbm(x * 40, z * 3, oct=3) * 0.5
    stripe = (np.abs(((x + 0.6) % 2.4) - 1.2) < 0.06)
    c = V(0.55, 0.47, 0.36)[None] * (0.72 + 0.22 * weave[:, None] + 0.22 * slub[:, None])   # oatmeal linen, v2 read as paper
    return np.where(stripe[:, None], c * V(0.55, 0.62, 0.78)[None], c).astype(f32)
def linen_bump(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    fold = np.sin(z * 1.3 + fbm(x * 0.5, z * 0.5, oct=3) * 3) * 0.06
    return np.stack([np.cos(x * 95) * 0.12, np.zeros_like(x), np.cos(z * 95) * 0.12 + fold * 2.5], 1).astype(f32)
linen = Mat("diffuse", tex=linen_tex, bump=linen_bump)
def wood_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    g = 0.5 + 0.5 * np.sin(x * 4 + 7 * fbm(x * 0.35, z * 1.6, oct=5))
    return (V(0.34, 0.20, 0.10)[None] * (0.8 + 0.22 * g[:, None]) * (0.85 + 0.3 * fbm(x * 3, z * 0.6, oct=4)[:, None])).astype(f32)
table = Mat("plastic", tex=wood_tex, f0=0.03, rough=0.2)

# bowl: wide stoneware, thick wall
sc.add(Lathe(stoneware, [(0, 0), (.55, 0), (.60, .03), (.95, .40), (1.18, .86), (1.20, .95), (1.14, .96),
                         (1.10, .87), (.88, .44), (.50, .12), (0, .10)], T=(0, 0, 0)))
# eggs: nestled in the bowl, lying on their sides at slight angles
eggs = [(-0.28, 0.14, -0.10, 88, 20, brown), (0.30, 0.14, -0.18, 92, -35, cream), (0.02, 0.16, 0.30, 85, 70, brown),
        (-0.55, 0.36, 0.35, 70, 130, white), (0.55, 0.34, 0.30, 75, 200, brown), (0.02, 0.45, -0.52, 72, 10, cream),
        (-0.62, 0.40, -0.45, 68, -60, brown), (0.28, 0.60, 0.05, 80, 150, brown)]
# settle every egg: lift it until it rests on the bowl / cloth and clears the eggs already placed
EP = np.array(EGG, float)
def egg_pts(R, T):
    ys = np.linspace(0.01, EP[-1, 1] - 0.01, 24); th = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    r = np.interp(ys, EP[:, 1], EP[:, 0])
    Y, TH = np.meshgrid(ys, th); Rr = np.interp(Y, EP[:, 1], EP[:, 0])
    loc = np.stack([Rr * np.cos(TH), Y, Rr * np.sin(TH)], -1).reshape(-1, 3)
    return loc @ np.asarray(R, float).T + T
IN = np.array([(0, .10), (.50, .12), (.88, .44), (1.10, .87)])
def floor_at(p, in_bowl):
    r = np.hypot(p[:, 0], p[:, 2])
    return np.where(in_bowl & (r < 1.10), np.interp(r, IN[:, 0], IN[:, 1]), 0.0)
def inside_egg(p, R, T):
    loc = (p - T) @ np.asarray(R, float)
    rr = np.hypot(loc[:, 0], loc[:, 2]); ok = (loc[:, 1] > 0) & (loc[:, 1] < EP[-1, 1])
    return ok & (rr < np.interp(loc[:, 1], EP[:, 1], EP[:, 0]) + 0.005)
placed = []
def settle(x, z, tilt, yaw, m, in_bowl=True):
    R = rot(yaw, 0, tilt); T = np.array([x, 0.0, z])
    pts = egg_pts(R, T); T[1] += np.max(floor_at(pts, in_bowl) - pts[:, 1]) + 0.004
    for _ in range(200):
        pts = egg_pts(R, T)
        if not any(inside_egg(pts, R2, T2).any() for R2, T2 in placed): break
        T[1] += 0.01
    if in_bowl and T[1] > 0.62: return          # v1 had an egg balanced on the rim: drop anything that stacks that high
    placed.append((R, T.copy())); sc.add(Lathe(m, EGG, R=R, T=tuple(T)))
for x, y, z, tilt, yaw, m in eggs:
    settle(x, z, tilt, yaw, m)
# one egg on the cloth, outside the bowl
settle(1.75, 0.95, 90, -20, white, in_bowl=False)
sc.add(Box(linen, (2.6, .004, 1.7), R=rot(8), T=(0.2, -.004, 0.2)))
sc.add(Plane(table, T=(0, -0.01, 0)))

sc.rect_light((-5.0, 4.0, -1.5), 2.5, 2.2, (8.5, 8.6, 9.0), R=rot(yaw=15, roll=-115))
def env(d):
    y = d[:, 1]
    return (V(0.20, 0.17, 0.14)[None] * (0.5 + 0.5 * np.clip(y + 0.5, 0, 1))[:, None]).astype(f32)
sc.env = env

sc.camera(pos=(1.7, 2.6, 4.6), look=(0.1, 0.35, 0.0), vfov=31, aperture=0.04)
sc.cam["focus"] = float(np.linalg.norm(V(0.0, 0.5, 0.2) - sc.cam["pos"]))
sc.exposure = 1.25; sc.vignette = 0.3

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "07_eggs", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
