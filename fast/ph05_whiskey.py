"""05 — a glass of whiskey on a walnut bar, backlit, the bottle out of focus behind."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def bar_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    g = 0.5 + 0.5 * np.sin(z * 22 + 6 * fbm(x * 0.25, z * 2.5, oct=5))
    plank = np.floor(z / 0.9)
    tone = 0.85 + 0.3 * vnoise(plank * 3.1, plank * 1.7)
    c = V(0.085, 0.040, 0.020)[None] * (0.6 + 0.6 * g[:, None]) * tone[:, None]
    seam = (np.abs(z / 0.9 - np.round(z / 0.9)) < 0.006)
    return np.where(seam[:, None], c * 0.3, c).astype(f32)
bar = Mat("plastic", tex=bar_tex, f0=0.05, rough=0.03)

glass = Mat("glass", ior=1.52, absorb=(0.05, 0.03, 0.04))
whisky = Mat("glass", ior=1.36, absorb=(0.9, 2.6, 7.5))
bottle_glass = Mat("glass", ior=1.5, absorb=(0.3, 0.3, 0.3))
cork = Mat("diffuse", alb=(0.45, 0.30, 0.16))
label = Mat("diffuse", alb=(0.62, 0.55, 0.40))

# rocks glass (1 unit = 10 cm): heavy base, straight walls, thin rim
sc.add(Lathe(glass, [(0, 0), (.40, 0), (.41, .01), (.42, .85), (.405, .86), (.39, .85), (.38, .16),
                     (.36, .12), (0, .115)], T=(0, 0, 0)))
sc.add(Lathe(whisky, [(0, .118), (.355, .122), (.374, .16), (.376, .40), (0, .40)], T=(0, 0, 0)))
# ice: two cubes floating in the whisky, one poking above it; slightly irregular, cloudy cores
def ice_bump(pl, pw, n):
    e = 0.01; f = lambda x, y, z: fbm(x * 9, y * 9, z * 9, oct=3)
    x, y, z = pl[:, 0], pl[:, 1], pl[:, 2]
    return (-np.stack([f(x + e, y, z) - f(x, y, z), f(x, y + e, z) - f(x, y, z), f(x, y, z + e) - f(x, y, z)], 1) / e * 0.012).astype(f32)
ice = Mat("glass", ior=1.31, absorb=(0.04, 0.03, 0.02), rough=0.02, bump=ice_bump)
cloud = Mat("diffuse", alb=(0.75, 0.78, 0.80))
for (x, y, z), R in (((-.15, .33, -.06), rot(20, 8, -6)), ((.155, .42, .06), rot(-17, -14, 22))):
    sc.add(Box(ice, (.125, .125, .125), R=R, T=(x, y, z)))
    sc.add(Sphere(cloud, R=R, T=(x, y, z), S=(.045, .03, .05)))
# bottle behind, left
bx, bz = -1.15, -2.4
sc.add(Lathe(bottle_glass, [(0, 0), (.48, 0), (.50, .04), (.50, 1.9), (.44, 2.1), (.18, 2.35), (.16, 2.9),
                            (.13, 2.9), (.13, 2.35), (.41, 2.1), (.46, 1.9), (.46, .08), (0, .07)], T=(bx, 0, bz)))
sc.add(Lathe(whisky, [(0, .08), (.455, .085), (.455, 1.35), (0, 1.35)], T=(bx, 0, bz)))
sc.add(Lathe(cork, [(0, 2.85), (.14, 2.85), (.15, 3.1), (0, 3.1)], T=(bx, 0, bz)))
sc.add(Lathe(label, [(0, .55), (.505, .55), (.505, 1.25), (0, 1.25)], T=(bx, 0, bz)))
sc.add(Plane(bar))

# light: a warm spot overhead-behind (rim light through the whisky), soft fill from the front
sc.rect_light((0.6, 3.6, -2.2), 0.9, 0.6, (26, 17, 9), R=rot(pitch=180 - 35))
sc.rect_light((1.8, 2.2, 3.5), 1.2, 1.2, (0.55, 0.62, 0.75), R=rot(pitch=180 + 50))
def env(d):
    y = d[:, 1]
    return (V(0.012, 0.008, 0.006)[None] * (1 + np.clip(y, 0, 1)[:, None])).astype(f32)
sc.env = env
rb = np.random.default_rng(12)
for _ in range(16):                               # the back bar: bottles lit from below, far away
    c = [(1.0, 0.6, 0.25), (1.0, 0.75, 0.4), (0.9, 0.5, 0.3)][rb.integers(3)]
    sc.add(Sphere(Mat("emit", emit=tuple(np.array(c) * rb.uniform(2, 6)), nee=False),
                  T=(rb.uniform(-6, 6), rb.uniform(0.5, 3.0), rb.uniform(-11, -8)), S=.09))

sc.camera(pos=(0.35, 0.62, 2.6), look=(-0.1, 0.42, 0.0), vfov=32, aperture=0.035)
sc.cam["focus"] = float(np.linalg.norm(V(0, 0.45, 0.3) - sc.cam["pos"]))
sc.exposure = 1.5; sc.vignette = 0.38; sc.bounces = 8

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "05_whiskey", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
