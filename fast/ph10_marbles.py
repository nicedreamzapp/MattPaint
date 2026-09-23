"""10 — glass marbles spilled on old floorboards in a shaft of late sun."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def floor_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    plank = np.floor(x / 2.2)
    zz = z + vnoise(plank * 7.1, plank) * 9
    g = 0.5 + 0.5 * np.sin(zz * 6 + 5 * fbm(x * 0.8 + plank * 3, zz * 0.25, oct=5))
    tone = 0.75 + 0.5 * vnoise(plank * 3.3, 0.5)
    c = V(0.42, 0.27, 0.15)[None] * (0.65 + 0.45 * g[:, None]) * tone[:, None]
    seam = np.abs(x / 2.2 - np.round(x / 2.2)) < 0.012
    end = np.abs(((zz / 11.0) % 1) - 0.5) > 0.4985
    scuff = fbm(x * 3, z * 3, oct=4)
    c = c * (0.85 + 0.25 * scuff[:, None])
    return np.where((seam | end)[:, None], c * 0.25, c).astype(f32)
floor = Mat("plastic", tex=floor_tex, f0=0.035, rough=0.14)
wall = Mat("diffuse", alb=(0.62, 0.58, 0.52))

clear = [Mat("glass", ior=1.5, absorb=a) for a in
         ((0.05, 0.6, 1.4), (1.6, 0.4, 0.1), (0.1, 0.1, 0.05), (1.2, 1.1, 0.1), (0.8, 0.1, 1.0), (1.4, 1.6, 0.2))]
core_cols = [(0.85, 0.12, 0.05), (0.05, 0.25, 0.80), (0.90, 0.65, 0.05), (0.85, 0.85, 0.85), (0.05, 0.55, 0.20), (0.90, 0.35, 0.05)]

rb = np.random.default_rng(21)
spots = []
def free(x, z, r):
    return all(math.hypot(x - a, z - b) > r + c + 0.02 for a, b, c in spots)
tries = 0
while len(spots) < 17 and tries < 5000:
    tries += 1
    r = rb.choice([0.8, 0.8, 0.8, 1.25]) if len(spots) else 1.25
    x = rb.normal(0.2, 2.4); z = rb.normal(-0.5, 2.0)
    if free(x, z, r): spots.append((x, z, r))
for i, (x, z, r) in enumerate(spots):
    g = clear[i % len(clear)]
    sc.add(Sphere(g, T=(x, r, z), S=r))
    # the twisted colored vane inside ("cat's eye"): thin ellipsoids in the glass
    col = Mat("plastic", alb=core_cols[i % len(core_cols)], f0=0.04, rough=0.2)
    for k in range(2):
        sc.add(Sphere(col, R=rot(rb.uniform(0, 180), 90, 60 * k + rb.uniform(-10, 10)),
                      T=(x, r, z), S=(r * 0.62, r * 0.05, r * 0.24)))
sc.add(Plane(floor))
sc.add(Box(wall, (30, 12, 0.3), T=(0, 12, -14)))
# skirting board
sc.add(Box(Mat("plastic", alb=(0.75, 0.73, 0.68), f0=0.04, rough=0.2), (30, 0.9, 0.2), T=(0, 0.9, -13.6)))

# late sun low through a window on the right, blue fill from the room
sc.set_sun((0.85, 0.30, -0.25), (5.0, 3.5, 2.0), angle_deg=0.9)
def env(d):
    y = d[:, 1]
    return (V(0.10, 0.12, 0.16)[None] * (0.7 + 0.3 * np.clip(y + 0.5, 0, 1))[:, None]).astype(f32)
sc.env = env
# the window frame shadow: two posts blocking part of the sun
sc.add(Box(wall, (0.4, 20, 0.4), T=(40, 14, -14)))
sc.add(Box(wall, (0.4, 20, 0.4), T=(40, 14, 3)))

sc.camera(pos=(-3.0, 3.3, 11.0), look=(0.3, 0.6, -0.5), vfov=34, aperture=0.12)
sc.cam["focus"] = float(np.linalg.norm(V(0.2, 1.0, 0.8) - sc.cam["pos"]))
sc.exposure = 0.95; sc.vignette = 0.35; sc.bounces = 8

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "10_marbles", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None, budget=90)
