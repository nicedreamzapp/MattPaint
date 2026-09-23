"""04 — three pillar candles on an old oak table at night, a brass holder, a wine glass."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def oak_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    g = 0.5 + 0.5 * np.sin(z * 14 + 5 * fbm(x * 0.35, z * 2.2, oct=5))
    knots = fbm(x * 0.7 + 9, z * 0.7, oct=4)
    c = V(0.16, 0.085, 0.040)[None] * (0.65 + 0.55 * g[:, None]) * (0.8 + 0.4 * knots[:, None])
    return c.astype(f32)
oak = Mat("plastic", tex=oak_tex, f0=0.03, rough=0.10)

FL = V(1.0, 0.55, 0.18)
def wax_glow_for(top):
    def g(pl, pw, n):                      # light scattered through the wax near the flame
        dist = np.clip(top - pl[:, 1], 0, None)
        return (FL[None] * (1.1 * np.exp(-dist * 14.0))[:, None]).astype(f32)   # v1 glowed like a lamp shade
    return g
def wax(top):
    return Mat("diffuse", alb=(0.80, 0.72, 0.58), glow=wax_glow_for(top))

brass = Mat("metal", alb=(0.90, 0.68, 0.36), rough=0.08)
glass = Mat("glass", ior=1.5, rough=0.0, absorb=(0.02, 0.02, 0.02))
wine = Mat("glass", ior=1.34, absorb=(2.2, 9.0, 7.0))

def candle(x, z, r, h, holder=False):
    y0 = 0.0
    if holder:
        sc.add(Lathe(brass, [(0, 0), (r * 1.9, 0), (r * 1.95, .03), (r * 1.7, .06), (r * 1.25, .09), (r * 1.2, .16),
                             (r * 1.35, .19), (r * 1.3, .20), (0, .20)], T=(x, 0, z)))
        y0 = .20
    top = h
    # pillar with a melted cup at the top and a soft lip
    prof = [(0, 0), (r, 0), (r, h - .02), (r * .97, h), (r * .88, h - .004), (r * .6, h - .03), (0, h - .035)]
    sc.add(Lathe(wax(h - .03), prof, T=(x, y0, z)))
    sc.add(Box(Mat("diffuse", alb=(0.02, 0.015, 0.01)), (.006, .03, .006), T=(x, y0 + h - .005, z)))
    # flame: bright inner teardrop (light) + dim blue base
    sc.sphere_light((x, y0 + h + .075, z), .028, tuple(FL * 110), S=(.022, .058, .022))
    return y0 + h

candle(-0.35, -0.05, 0.16, 0.95)
candle(0.12, -0.35, 0.14, 0.62)
candle(0.46, 0.10, 0.11, 0.42, holder=True)
# a glass of red wine in front
gx, gz = -0.72, 0.52
bowl = [(0, 0), (.20, 0), (.20, .012), (.03, .03), (.022, .30), (.05, .34), (.17, .44), (.20, .56), (.18, .72),
        (.172, .72), (.19, .56), (.16, .445), (.045, .35), (0, .345)]
sc.add(Lathe(glass, bowl, T=(gx, 0, gz)))
sc.add(Lathe(wine, [(0, .352), (.05, .356), (.155, .45), (.18, .52), (0, .52)], T=(gx, 0, gz)))
sc.add(Plane(oak))

def env(d):
    return np.broadcast_to(V(0.004, 0.003, 0.0025), d.shape).astype(f32)
sc.env = env
rb = np.random.default_rng(3)
for _ in range(12):                         # other candles deep in the room
    sc.add(Sphere(Mat("emit", emit=tuple(FL * rb.uniform(3, 9)), nee=False),
                  T=(rb.uniform(-6, 5), rb.uniform(0.3, 1.8), rb.uniform(-12, -8)), S=.05))

sc.camera(pos=(0.35, 0.72, 2.9), look=(-0.12, 0.52, 0.0), vfov=36, aperture=0.03)
sc.cam["focus"] = float(np.linalg.norm(V(-0.35, 0.7, 0.1) - sc.cam["pos"]))
sc.exposure = 1.7; sc.vignette = 0.4; sc.bloom = 1.3

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "04_candles", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
