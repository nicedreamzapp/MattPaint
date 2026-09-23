"""03 — morning espresso on a marble café table, low sun, street lights out of focus behind."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def marble_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    w = fbm(x * 0.9, z * 0.9, oct=6)
    vein = np.abs(np.sin((x * 1.3 + z * 0.7 + w * 6.0) * 2.2))
    vein = np.clip(1 - vein * 6, 0, 1) ** 1.5
    fine = np.clip(1 - np.abs(np.sin((x * 2.1 - z * 1.7 + fbm(x * 3, z * 3, oct=4) * 5) * 3.1)) * 14, 0, 1)
    base = V(0.78, 0.76, 0.72)[None] * (0.94 + 0.06 * fbm(x * 4, z * 4, oct=3))[:, None]
    c = base * (1 - 0.55 * vein[:, None] - 0.25 * fine[:, None])
    return (c * V(1.0, 0.99, 0.97)[None]).astype(f32)
marble = Mat("plastic", tex=marble_tex, f0=0.04, rough=0.015)
ceramic = Mat("plastic", alb=(0.80, 0.79, 0.76), f0=0.05, rough=0.01)

def crema_tex(pl, pw, n):
    r = np.sqrt(pl[:, 0] ** 2 + pl[:, 2] ** 2); a = np.arctan2(pl[:, 2], pl[:, 0])
    swirl = fbm(pl[:, 0] * 14 + np.sin(a * 2 + r * 20) * 0.6, pl[:, 2] * 14, oct=5)
    rim = np.clip((r - 0.30) / 0.06, 0, 1)                  # darker ring where crema meets the cup
    light = V(0.46, 0.25, 0.10); dark = V(0.16, 0.07, 0.025)
    t = np.clip(swirl * 1.3 - 0.25 + rim * 0.6, 0, 1)
    c = light[None] * (1 - t[:, None]) + dark[None] * t[:, None]
    bub = fbm(pl[:, 0] * 90, pl[:, 2] * 90, oct=2)           # micro bubbles
    return (c * (0.85 + 0.3 * bub[:, None])).astype(f32)
crema = Mat("plastic", tex=crema_tex, f0=0.025, rough=0.05)
steel = Mat("metal", alb=(0.86, 0.85, 0.83), rough=0.025)

def sugar_bump(pl, pw, n):
    return (np.stack([vnoise(pw[:, 0] * 160, pw[:, 1] * 160, pw[:, 2] * 160) - 0.5 for _ in range(1)] * 3, 1) * 0.5).astype(f32)
sugar = Mat("diffuse", alb=(0.86, 0.85, 0.82), bump=sugar_bump)

# ---- cup + saucer (lathe, 1 unit = 10 cm) ----
cup_prof = [(0, 0), (.20, 0), (.22, .015), (.25, .045), (.31, .14), (.355, .30), (.37, .42), (.372, .47),
            (.365, .48), (.352, .47), (.347, .42), (.33, .30), (.285, .15), (.22, .075), (0, .07)]
saucer_prof = [(0, 0), (.30, 0), (.31, .012), (.36, .03), (.60, .06), (.66, .085), (.665, .095), (.64, .098),
               (.59, .075), (.36, .052), (.33, .045), (0, .045)]
CX, CZ = 0.0, 0.0
sc.add(Lathe(ceramic, saucer_prof, T=(CX, 0, CZ)))
sc.add(Lathe(ceramic, cup_prof, T=(CX, .045, CZ)))
sc.add(Lathe(crema, [(.338, .41), (0, .41)], T=(CX, .045, CZ)))
# handle: a smooth ring (a torus, made as a lathe of a circle) whose inner edge sits in the cup wall.
# v1 floated off the cup; v2 was a chain of beads that read as a lumpy donut.
ring = [(.09 + .027 * math.cos(math.radians(a)), .027 * math.sin(math.radians(a))) for a in range(-90, 271, 15)]
sc.add(Lathe(ceramic, ring, R=rot(0, 90, 0), T=(CX + .445, .045 + .27, CZ)))
sc.add(Sphere(ceramic, T=(CX + .338, .045 + .205, CZ), S=(.034, .032, .028)))   # lower joint: closes the gap where the cup flares in
# spoon resting on the saucer
yaw = 28
R = rot(yaw)
sc.add(Sphere(steel, R=R, T=(CX - .12, .085, CZ + .42), S=(.055, .012, .085)))
sc.add(Box(steel, (.012, .004, .19), R=R @ rot(pitch=-4), T=(CX - .12 + math.sin(math.radians(yaw)) * .26, .118, CZ + .42 + math.cos(math.radians(yaw)) * .26)))
# sugar cubes on the table
sc.add(Box(sugar, (.065, .065, .065), R=rot(22), T=(.62, .065, .55)))
sc.add(Box(sugar, (.065, .065, .065), R=rot(-12, 0, 0), T=(.78, .065, .38)))
sc.add(Plane(marble, T=(0, 0, 0), ext=(3.2, 3.2)))

# ---- light: low morning sun from the back left, open sky, distant street ----
sc.set_sun((-0.75, 0.42, -0.55), (4.4, 3.4, 2.2), angle_deg=1.2)   # v3 went cold: warm key back up
def env(d):
    y = d[:, 1]
    sky = V(0.34, 0.42, 0.60) * 0.55; hor = V(0.85, 0.66, 0.46)
    s = np.clip(y * 2.5, 0, 1)[:, None]
    c = hor[None] * (1 - s) + sky[None] * s
    street = V(0.20, 0.16, 0.12)                 # pavement and buildings below the horizon
    return np.where((y < 0.02)[:, None], street[None] * (0.6 + 0.4 * np.clip(y + 0.3, 0, 1))[:, None], c).astype(f32)
sc.env = env
rb = np.random.default_rng(7)
for _ in range(14):                              # café lights across the street
    c = [(1.0, 0.62, 0.25), (1.0, 0.78, 0.45), (0.95, 0.9, 0.8)][rb.integers(3)]
    o = sc.add(Sphere(Mat("emit", emit=tuple(np.array(c) * rb.uniform(4, 10)), nee=False),
                      T=(rb.uniform(-9, 5), rb.uniform(0.6, 2.4), rb.uniform(-16, -12)), S=.12))

sc.camera(pos=(0.75, 1.55, 1.85), look=(0.02, 0.28, 0.0), vfov=34, aperture=0.018)   # high enough to see the crema
sc.cam["focus"] = float(np.linalg.norm(V(0.1, 0.45, 0.15) - sc.cam["pos"]))
sc.exposure = 0.95; sc.vignette = 0.28

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "03_espresso", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
