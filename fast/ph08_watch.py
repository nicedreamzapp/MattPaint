"""08 — an old gold pocket watch and a spill of coins on dark green velvet, one warm spotlight."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

def velvet_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    crush = fbm(x * 1.2, z * 1.2, oct=5)
    return (V(0.020, 0.075, 0.045)[None] * (0.55 + 0.9 * crush[:, None])).astype(f32)
def velvet_bump(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]; e = 0.02
    h = lambda a, b: fbm(a * 1.2, b * 1.2, oct=5)
    return np.stack([-(h(x + e, z) - h(x, z)) / e * 0.25, np.zeros_like(x), -(h(x, z + e) - h(x, z)) / e * 0.25], 1).astype(f32)
velvet = Mat("diffuse", tex=velvet_tex, bump=velvet_bump)

gold = Mat("metal", alb=(0.95, 0.72, 0.36), rough=0.09)
gold_worn = Mat("metal", alb=(0.90, 0.66, 0.32), rough=0.16)
silver = Mat("metal", alb=(0.90, 0.89, 0.86), rough=0.14)
copper = Mat("metal", alb=(0.92, 0.55, 0.40), rough=0.18)
crystal = Mat("glass", ior=1.5)

def dial_tex(pl, pw, n):
    x, z = pl[:, 0], pl[:, 2]; r = np.sqrt(x * x + z * z); a = np.arctan2(z, x)
    c = np.broadcast_to(V(0.80, 0.76, 0.66), pl.shape).copy()
    ticks = (np.abs(((a / (2 * np.pi) * 60) + 0.5) % 1 - 0.5) < 0.09) & (r > 0.78) & (r < 0.86)
    hours = (np.abs(((a / (2 * np.pi) * 12) + 0.5) % 1 - 0.5) < 0.05) & (r > 0.66) & (r < 0.86)
    ring = (np.abs(r - 0.88) < 0.012) | (np.abs(r - 0.76) < 0.006)
    sub = (np.hypot(x, z - 0.42) < 0.17) & (np.abs(np.hypot(x, z - 0.42) - 0.16) < 0.01)
    ink = ticks | hours | ring | sub
    c[ink] = (0.03, 0.03, 0.03)
    age = fbm(x * 4, z * 4, oct=3)
    return (c * (0.9 + 0.12 * age[:, None])).astype(f32)
dial = Mat("plastic", tex=dial_tex, f0=0.04, rough=0.2)

# watch (1 unit = 2 cm), lying flat, tilted a touch on its chain
WX, WZ = 0.0, 0.0
sc.add(Lathe(gold, [(0, 0), (1.0, 0), (1.08, .08), (1.12, .22), (1.10, .34), (1.04, .40), (.98, .40), (0, .40)], T=(WX, 0, WZ)))
sc.add(Lathe(dial, [(.98, .402), (0, .402)], T=(WX, 0, WZ)))
sc.add(Lathe(crystal, [(0, .41), (.985, .41), (.97, .47), (.80, .55), (0, .58)], T=(WX, 0, WZ)))
# hands (blued steel) and the crown/bow at 12 o'clock (toward -z)
blue = Mat("metal", alb=(0.10, 0.14, 0.30), rough=0.05)
sc.add(Box(blue, (.03, .006, .50), R=rot(-50), T=(WX + .19, .412, WZ - .23)))
sc.add(Box(blue, (.028, .006, .35), R=rot(75), T=(WX - .17, .418, WZ + .05)))
sc.add(Sphere(gold, T=(WX, .42, WZ), S=(.06, .02, .06)))
sc.add(Lathe(gold_worn, [(0, 0), (.17, 0), (.17, .22), (0, .22)], R=rot(0, 90, 0), T=(WX, .20, WZ - 1.08)))
sc.add(Lathe(gold_worn, [(0, 0), (.13, 0), (.14, .18), (0, .18)], R=rot(0, 90, 0), T=(WX, .20, WZ - 1.30)))
for i in range(16):                                   # the bow: a ring of beads
    a = math.radians(-180 + 180 * i / 15)
    sc.add(Sphere(gold_worn, T=(WX + .28 * math.cos(a), .20, WZ - 1.52 + .28 * math.sin(a)), S=.06))
# the chain curling away: small links alternating orientation
pts = []
for i in range(46):
    t = i / 45
    x = WX - 0.2 * math.sin(t * 5.5) - t * 2.4; z = WZ - 1.85 - t * 2.2 + 0.6 * math.sin(t * 3.1)
    pts.append((x, z))
for i, (x, z) in enumerate(pts):
    if i + 1 < len(pts):
        dx, dz = pts[i + 1][0] - x, pts[i + 1][1] - z
    yaw = -math.degrees(math.atan2(dz, dx))
    sc.add(Sphere(gold_worn, R=rot(yaw, 0, 90 if i % 2 else 0), T=(x, .05, z), S=(.09, .045, .03)))

# coins: a short stack and a few loose ones, some on edge-ish tilts
def coin_bump(R, seed):
    """struck-coin relief: raised rim, a worn embossed head in the middle, beaded ring, reeded edge.
    v2 coins were blank discs that read as poker chips"""
    def b(pl, pw, n):
        x, y, z = pl[:, 0], pl[:, 1], pl[:, 2]
        rr = np.sqrt(x * x + z * z) + 1e-6; r = rr / R; a = np.arctan2(z, x)
        top = np.abs(n[:, 1]) > 0.5
        def hgt(x, z):
            rq = np.sqrt(x * x + z * z) / R; aq = np.arctan2(z, x)
            rim = np.clip((rq - 0.86) * 12, 0, 1)
            beads = (np.abs(rq - 0.80) < 0.025) * (0.5 + 0.5 * np.cos(aq * 64))
            head = np.clip(1 - ((x / R + 0.05) ** 2 / 0.20 + (z / R - 0.02) ** 2 / 0.30), 0, 1) ** 0.5
            head = head * (0.7 + 0.6 * fbm(x * 9 + seed, z * 9, oct=3))
            letters = (np.abs(rq - 0.70) < 0.04) * (fbm(aq * 18 + seed, rq * 3, oct=2) > 0.5)
            return rim * 0.6 + beads * 0.3 + head * 0.5 + letters * 0.35
        e = 0.004
        gx = (hgt(x + e, z) - hgt(x - e, z)) / (2 * e); gz = (hgt(x, z + e) - hgt(x, z - e)) / (2 * e)
        k = 0.012
        top_b = np.stack([-gx * k, np.zeros_like(x), -gz * k], 1)
        reed = np.cos(a * 180) * 0.25                                  # reeded edge
        side_b = np.stack([-np.sin(a) * reed, np.zeros_like(x), np.cos(a) * reed], 1)
        return np.where(top[:, None], top_b, side_b).astype(f32)
    return b
_cn = [0]
def coin(m, x, z, y=0.0, r=.62, h=.07, tilt=0.0, yaw=0.0):
    _cn[0] += 1
    mm = Mat(m.kind, alb=tuple(m.alb), rough=m.rough, bump=coin_bump(r, _cn[0] * 3.7))
    sc.add(Lathe(mm, [(0, 0), (r, 0), (r, h), (0, h)], R=rot(yaw, tilt, 0), T=(x, y, z)))
for k in range(7):
    coin(gold, 2.15 + 0.03 * math.sin(k * 2.1), -0.55 + 0.03 * math.cos(k * 1.7), y=k * .072, yaw=k * 17)
coin(gold_worn, 1.45, 1.05, tilt=4, yaw=30)
coin(silver, 2.55, 0.95, r=.70, h=.08, yaw=10)
coin(copper, 0.95, 1.95, r=.52, tilt=3)
coin(gold, 3.35, 0.10, r=.62, tilt=-3)
coin(silver, -1.60, 1.30, r=.70, h=.08, tilt=2)

sc.add(Plane(velvet))
# one warm spotlight above, dim cool bounce from the room
sc.rect_light((1.5, 9.0, 3.0), 0.8, 0.8, (95, 72, 45), R=rot(pitch=180 + 18))
# a big soft studio panel up front-right: flat metal is a mirror, and v1's coins mirrored a black
# room and came out as black discs
# placed where the coins' mirror direction actually points (behind the table, up), not in front
sc.rect_light((-2.5, 5.5, -8.5), 5.0, 3.0, (2.2, 2.0, 1.7), R=rot(pitch=120))
def env(d):
    y = np.clip(d[:, 1], 0, 1)
    return (V(0.05, 0.05, 0.055)[None] * (0.4 + 1.6 * y[:, None])).astype(f32)
sc.env = env

sc.camera(pos=(3.2, 3.4, 6.2), look=(0.6, 0.2, 0.0), vfov=30, aperture=0.06)
sc.cam["focus"] = float(np.linalg.norm(V(0.2, 0.45, 0.2) - sc.cam["pos"]))
sc.exposure = 1.3; sc.vignette = 0.42; sc.bounces = 6

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "08_watch", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
