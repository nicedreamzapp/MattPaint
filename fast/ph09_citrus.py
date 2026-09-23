"""09 — oranges and lemons on an olive-wood board, one orange cut open, knife resting, window light."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def peel_bump(scale, amt):
    def b(pl, pw, n):
        e = 0.3 / scale
        f = lambda x, y, z: vnoise(x * scale, y * scale, z * scale)
        x, y, z = pl[:, 0], pl[:, 1], pl[:, 2]
        g = np.stack([f(x + e, y, z) - f(x, y, z), f(x, y + e, z) - f(x, y, z), f(x, y, z + e) - f(x, y, z)], 1) / e
        return (-g * amt).astype(f32)
    return b
def peel_tex(c1, c2):
    def t(pl, pw, n):
        m = fbm(pl[:, 0] * 3, pl[:, 1] * 3, pl[:, 2] * 3, oct=4)
        return (V(*c1)[None] * (1 - m[:, None]) + V(*c2)[None] * m[:, None]).astype(f32)
    return t
orange = Mat("plastic", tex=peel_tex((0.80, 0.22, 0.01), (0.88, 0.34, 0.02)), bump=peel_bump(55, 0.012), f0=0.04, rough=0.10)
lemon = Mat("plastic", tex=peel_tex((0.80, 0.60, 0.03), (0.72, 0.62, 0.08)), bump=peel_bump(60, 0.010), f0=0.04, rough=0.12)

def flesh_tex(pl, pw, n):
    x, z = pl[:, 0], pl[:, 2]; r = np.sqrt(x * x + z * z) / 0.62; a = np.arctan2(z, x)
    seg = np.abs(((a / (2 * np.pi) * 11) % 1) - 0.5)                        # 11 segments
    membrane = (seg > 0.46) | (r < 0.10)
    pith = (r > 0.86)
    rind = r > 0.95
    vesicle = fbm(x * 70, z * 70, oct=2)
    c = V(0.90, 0.36, 0.03)[None] * (0.75 + 0.45 * vesicle[:, None])
    c = np.where(membrane[:, None], V(0.95, 0.72, 0.40)[None], c)
    c = np.where(pith[:, None], V(0.92, 0.82, 0.60)[None], c)
    c = np.where(rind[:, None], V(0.85, 0.30, 0.02)[None], c)
    return c.astype(f32)
flesh = Mat("plastic", tex=flesh_tex, f0=0.03, rough=0.02,
            glow=lambda pl, pw, n: (V(0.10, 0.03, 0.0)[None] * np.ones((len(pl), 1))).astype(f32))

def olive_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    w = fbm(x * 0.6, z * 0.6, oct=5)
    g = 0.5 + 0.5 * np.sin((x * 3.5 + w * 9) * 3)
    c = V(0.55, 0.40, 0.22)[None] * (0.55 + 0.55 * g[:, None]) * (0.85 + 0.3 * fbm(x * 5, z * 5, oct=3)[:, None])
    return c.astype(f32)
board = Mat("plastic", tex=olive_tex, f0=0.03, rough=0.25)
def counter_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    return (V(0.30, 0.30, 0.29)[None] * (0.8 + 0.3 * fbm(x * 8, z * 8, oct=4))[:, None]).astype(f32)
counter = Mat("plastic", tex=counter_tex, f0=0.04, rough=0.08)
steel = Mat("metal", alb=(0.86, 0.86, 0.85), rough=0.04)
handle = Mat("plastic", alb=(0.04, 0.025, 0.018), f0=0.04, rough=0.15)
rivet = Mat("metal", alb=(0.85, 0.84, 0.80), rough=0.05)
def tile_tex(pl, pw, n):
    x, y = pw[:, 0], pw[:, 1]
    gx = np.abs(((x / 1.2) % 1) - 0.5) > 0.485; gy = np.abs(((y / 0.6) % 1) - 0.5) > 0.47
    c = V(0.72, 0.74, 0.70) * np.ones((len(x), 1), f32)
    return np.where((gx | gy)[:, None], V(0.45, 0.44, 0.42)[None], c).astype(f32)
tiles = Mat("plastic", tex=tile_tex, f0=0.05, rough=0.02)

TOP = 0.28                                    # board top (1 unit = 10 cm)
sc.add(Box(board, (3.0, TOP / 2, 1.9), R=rot(-6), T=(0, TOP / 2, 0)))
sc.add(Plane(counter))
sc.add(Box(tiles, (12, 4, 0.1), T=(0, 4, -6.0)))
# whole fruit
def orange_at(x, z, r, yaw=0):
    sc.add(Sphere(orange, R=rot(yaw), T=(x, TOP + r * 0.93, z), S=(r, r * 0.93, r)))
    sc.add(Sphere(Mat("plastic", alb=(0.25, 0.30, 0.08), f0=0.03, rough=0.3), T=(x, TOP + r * 1.85, z), S=(.07, .02, .07)))
orange_at(-1.15, -0.45, 0.72)
orange_at(0.35, -1.35, 0.66, 40)
def lemon_at(x, z, yaw, tilt=90):
    prof = [(0, 0), (.08, .02), (.14, .10), (.32, .30), (.46, .55), (.52, .80), (.47, 1.05), (.33, 1.30), (.15, 1.50),
            (.08, 1.58), (0, 1.60)]
    sc.add(Lathe(lemon, prof, R=rot(yaw, 0, tilt), T=(x, TOP + .50, z)))
lemon_at(1.9, -0.9, 25)
lemon_at(2.6, 0.25, -40)
# the cut orange: a hemisphere, cut face up, and the other half face down
sc.add(Lathe(orange, [(0, 0), (.30, .03), (.50, .14), (.60, .30), (.62, .40), (.62, .40)], T=(0.45, TOP, 0.75)))
sc.add(Lathe(flesh, [(.62, .40), (0, .40)], T=(0.45, TOP, 0.75)))
sc.add(Lathe(orange, [(0, 0), (.62, 0), (.60, .12), (.50, .26), (.30, .37), (0, .40)], R=rot(30), T=(-0.85, TOP, 0.95)))
# a few drops of juice on the board
for x, z, r in ((0.95, 0.35, .05), (0.1, 1.25, .035), (1.2, 0.95, .03)):
    sc.add(Sphere(Mat("glass", ior=1.34, absorb=(0.2, 0.8, 3.0)), T=(x, TOP, z), S=(r, r * 0.35, r)))
# the knife: blade tapering is faked with two boxes, handle with rivets
K = rot(-28)
def kpart(m, half, local):
    sc.add(Box(m, half, R=K, T=tuple(V(*local) @ K.T + V(1.25, TOP + half[1], 1.45))))
kpart(steel, (1.10, .008, .16), (0, 0, 0))
kpart(steel, (0.25, .008, .10), (1.25, 0, -0.04))
kpart(handle, (0.62, .06, .12), (-1.72, 0, 0.02))
for dx in (-2.05, -1.72, -1.39):
    kpart(rivet, (.03, .062, .03), (dx, 0, 0.02))

sc.rect_light((5.0, 3.5, 2.0), 1.8, 2.2, (12, 11.5, 10.5), R=rot(yaw=-20, roll=120))
def env(d):
    return np.broadcast_to(V(0.22, 0.22, 0.24), d.shape).astype(f32) * f32(0.5)
sc.env = env

sc.camera(pos=(1.8, 3.1, 5.3), look=(0.4, 0.5, -0.1), vfov=33, aperture=0.05)
sc.cam["focus"] = float(np.linalg.norm(V(0.45, 0.7, 0.75) - sc.cam["pos"]))
sc.exposure = 1.1; sc.vignette = 0.3

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "09_citrus", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
