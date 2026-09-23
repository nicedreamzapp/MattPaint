"""11 — a stack of pancakes with butter, maple syrup and blueberries, Sunday-morning window light."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def cake_tex(pl, pw, n):
    y = pl[:, 1]; r = np.sqrt(pl[:, 0] ** 2 + pl[:, 2] ** 2)
    face = np.abs(n[:, 1]) > 0.6                           # the browned top / bottom faces
    spots = fbm(pl[:, 0] * 9, pl[:, 2] * 9, oct=5)
    brown = V(0.42, 0.17, 0.04)[None] * (0.55 + 0.7 * spots[:, None])
    edge = V(0.78, 0.55, 0.25)[None] * (0.85 + 0.25 * fbm(pl[:, 0] * 25, y * 60, pl[:, 2] * 25, oct=3)[:, None])
    return np.where(face[:, None], brown, edge).astype(f32)
def cake_bump(pl, pw, n):
    e = 0.02; f = lambda x, z: fbm(x * 7, z * 7, oct=4)
    x, z = pl[:, 0], pl[:, 2]
    return np.stack([-(f(x + e, z) - f(x, z)) / e * 0.05, np.zeros_like(x), -(f(x, z + e) - f(x, z)) / e * 0.05], 1).astype(f32)
cake = Mat("diffuse", tex=cake_tex, bump=cake_bump)
syrup = Mat("glass", ior=1.45, absorb=(0.9, 2.2, 6.0))
butter = Mat("plastic", alb=(0.90, 0.78, 0.40), f0=0.04, rough=0.12,
             glow=lambda pl, pw, n: np.broadcast_to(V(0.05, 0.035, 0.005), pl.shape).astype(f32))
berry = Mat("plastic", alb=(0.07, 0.08, 0.20), f0=0.035, rough=0.35)
plate = Mat("plastic", alb=(0.80, 0.80, 0.78), f0=0.05, rough=0.02)
steel = Mat("metal", alb=(0.86, 0.86, 0.85), rough=0.05)

def table_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    g = 0.5 + 0.5 * np.sin(x * 5 + 3 * fbm(x * 0.2, z * 0.9, oct=4))
    plank = np.abs(((z / 2.6) % 1) - 0.5) > 0.495
    c = V(0.55, 0.52, 0.47)[None] * (0.8 + 0.25 * g[:, None])      # whitewashed pine
    return np.where(plank[:, None], c * 0.4, c).astype(f32)
table = Mat("plastic", tex=table_tex, f0=0.03, rough=0.35)

# plate (1 unit = 5 cm)
sc.add(Lathe(plate, [(0, 0), (1.6, 0), (1.7, .05), (2.45, .18), (2.6, .30), (2.55, .33), (2.4, .24), (1.7, .14),
                     (0, .14)]))
# stack: six pancakes, each slightly off-centre and a bit domed
y = 0.14
rb = np.random.default_rng(9)
for i in range(6):
    h = 0.24 + rb.uniform(-0.02, 0.03); r = 1.55 + rb.uniform(-0.06, 0.06)
    ox, oz = rb.normal(0, 0.05), rb.normal(0, 0.05)
    sc.add(Lathe(cake, [(0, 0), (r - .12, 0), (r - .02, .04), (r, .12), (r - .03, h - .04), (r - .14, h), (0, h + .02)],
                 T=(ox, y, oz)))
    y += h - 0.01
TOPY = y
# syrup: a glossy sheet over the top and runs down the side
sc.add(Lathe(syrup, [(0, 0), (1.25, 0), (1.32, .03), (1.20, .06), (0, .07)], T=(0, TOPY, 0)))
for a, L in ((20, 0.9), (75, 0.55), (140, 1.2), (205, 0.7), (300, 1.0)):
    c = math.radians(a); x = 1.50 * math.cos(c); z = 1.50 * math.sin(c)
    sc.add(Sphere(syrup, R=rot(-a), T=(x, TOPY - L / 2 + 0.05, z), S=(.06, L / 2 + .04, .11)))
    sc.add(Sphere(syrup, T=(x * 1.02, TOPY - L + 0.02, z * 1.02), S=.08))
# pool of syrup on the plate
sc.add(Lathe(syrup, [(0, 0), (2.05, 0), (2.1, .02), (1.95, .04), (0, .045)], T=(0.1, .14, 0.05)))
# butter pat, softening at the corners
sc.add(Box(butter, (.34, .12, .30), R=rot(22), T=(0.1, TOPY + .17, -0.05)))
sc.add(Sphere(butter, R=rot(22), T=(0.1, TOPY + .06, -0.05), S=(.42, .05, .38)))
# blueberries on top and scattered
def berry_at(x, yy, z, r=.17):
    sc.add(Sphere(berry, T=(x, yy + r * 0.92, z), S=(r, r * 0.92, r)))
    sc.add(Sphere(Mat("diffuse", alb=(0.03, 0.03, 0.05)), T=(x, yy + r * 1.78, z), S=(.05, .015, .05)))
for x, z in ((0.85, 0.55), (-0.7, 0.75), (-0.55, -0.7), (0.65, -0.75), (-0.95, -0.05)):
    berry_at(x, TOPY + 0.06, z)
for x, z in ((2.2, 1.5), (2.55, 1.25), (-2.5, 1.9), (3.1, -0.4)):
    berry_at(x, 0.0, z, .16)
# fork resting on the plate edge
F = rot(-35)
def fpart(m, half, local, y0):
    sc.add(Box(m, half, R=F, T=tuple(V(*local) @ F.T + V(1.2, y0, 1.9))))
fpart(steel, (1.6, .025, .11), (1.0, 0, 0), 0.30)
for k in (-.09, -.03, .03, .09):
    fpart(steel, (.45, .02, .018), (-0.95, 0, k), 0.27)
fpart(steel, (.15, .022, .12), (-0.55, 0, 0), 0.28)
sc.add(Plane(table))

sc.rect_light((-7.0, 6.0, -3.0), 3.0, 3.0, (8.5, 8.3, 7.8), R=rot(yaw=30, roll=-120))
def env(d):
    y = d[:, 1]
    return (V(0.30, 0.30, 0.32)[None] * (0.6 + 0.4 * np.clip(y + 0.3, 0, 1))[:, None]).astype(f32)
sc.env = env

sc.camera(pos=(3.6, 3.4, 8.2), look=(0.1, 0.9, 0.0), vfov=33, aperture=0.08)
sc.cam["focus"] = float(np.linalg.norm(V(0.3, 1.4, 1.2) - sc.cam["pos"]))
sc.exposure = 1.05; sc.vignette = 0.28; sc.bounces = 7

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "11_pancakes", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
