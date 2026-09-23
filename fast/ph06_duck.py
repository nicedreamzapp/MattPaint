"""06 — a rubber duck floating in a bath, window light, soap foam at the edge."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def ripple(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    # rings spreading from the duck + a slow swell
    r = np.sqrt((x - 0.1) ** 2 + (z - 0.0) ** 2) + 1e-4
    ring = np.cos(r * 38 - 1.2) * np.exp(-r * 1.4) * 0.05
    sw = (fbm(x * 1.6, z * 1.6, oct=3) - 0.5) * 0.10
    e = 0.02
    gx = (np.cos((r + e) * 38 - 1.2) * np.exp(-(r + e) * 1.4) - np.cos(r * 38 - 1.2) * np.exp(-r * 1.4)) / e * 0.05
    bx = gx * (x - 0.1) / r; bz = gx * z / r
    nx = -(bx + (fbm((x + e) * 1.6, z * 1.6, oct=3) - fbm(x * 1.6, z * 1.6, oct=3)) / e * 0.10)
    nz = -(bz + (fbm(x * 1.6, (z + e) * 1.6, oct=3) - fbm(x * 1.6, z * 1.6, oct=3)) / e * 0.10)
    return np.stack([nx, np.zeros_like(nx), nz], 1).astype(f32) * 0.35
water = Mat("glass", ior=1.333, absorb=(0.22, 0.07, 0.05), bump=ripple)
tub = Mat("plastic", alb=(0.82, 0.83, 0.82), f0=0.05, rough=0.02)
yellow = Mat("plastic", alb=(0.88, 0.58, 0.02), f0=0.04, rough=0.09)
orange = Mat("plastic", alb=(0.90, 0.22, 0.02), f0=0.04, rough=0.07)
eye = Mat("plastic", alb=(0.01, 0.01, 0.01), f0=0.06, rough=0.01)
eyew = Mat("plastic", alb=(0.85, 0.85, 0.85), f0=0.04, rough=0.05)
foam = Mat("plastic", alb=(0.88, 0.88, 0.90), f0=0.03, rough=0.05)

# the tub: floor under the water, a curved back wall and the rim
sc.add(Plane(tub, T=(0, -0.7, 0)))
sc.add(Box(tub, (6, 1.0, 0.3), T=(0, 0.1, -3.2)))            # back wall of the tub
sc.add(Box(tub, (6, 0.12, 0.6), T=(0, 1.12, -3.3)))          # rim
sc.add(Box(Mat("diffuse", alb=(0.55, 0.60, 0.62)), (8, 4, 0.1), T=(0, 3, -4.0)))   # tiled wall
water_plane = sc.add(Box(water, (6, 0.35, 5), T=(0, -0.35, 0)))

# the duck (1 unit = 10 cm), facing +x a little toward camera
D = rot(25)
def duck(part_mat, T, S, R=None):
    T = V(*T) @ D.T + V(0.1, 0, 0)
    sc.add(Sphere(part_mat, R=D if R is None else D @ R, T=tuple(T), S=S))
duck(yellow, (0, 0.10, 0), (0.56, 0.36, 0.42))                 # body
duck(yellow, (-0.44, 0.30, 0), (0.20, 0.16, 0.20), rot(0, 0, -35))   # tail
duck(yellow, (0.30, 0.54, 0), (0.27, 0.26, 0.26))              # head
duck(orange, (0.56, 0.49, 0), (0.17, 0.055, 0.13))              # beak
for s in (-1, 1):
    duck(eyew, (0.47, 0.62, s * 0.14), (0.055, 0.055, 0.04))
    duck(eye, (0.505, 0.625, s * 0.155), (0.032, 0.036, 0.022))
    duck(yellow, (-0.02, 0.20, s * 0.34), (0.30, 0.10, 0.08), rot(0, 0, -12))   # wings

# foam near the back wall
rb = np.random.default_rng(5)
for _ in range(40):
    x = rb.uniform(-3.5, 2.5); z = rb.uniform(-2.9, -2.2) + rb.normal(0, 0.1)
    r = rb.uniform(0.03, 0.11)
    sc.add(Sphere(foam, T=(x, r * 0.4, z), S=(r, r * 0.7, r)))

# light: a big frosted window up left, bright bathroom fill
sc.rect_light((-4.5, 4.5, 1.0), 2.0, 2.4, (9, 9.3, 9.8), R=rot(roll=-120))
def env(d):
    return np.broadcast_to(V(0.45, 0.46, 0.48), d.shape).astype(f32) * f32(0.35)
sc.env = env

sc.camera(pos=(2.2, 1.05, 3.4), look=(0.05, 0.25, 0.0), vfov=32, aperture=0.03)
sc.cam["focus"] = float(np.linalg.norm(V(0.3, 0.4, 0.2) - sc.cam["pos"]))
sc.exposure = 1.1; sc.vignette = 0.25; sc.bounces = 7

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "06_duck", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
