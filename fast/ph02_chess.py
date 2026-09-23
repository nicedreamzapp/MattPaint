"""02 — chess endgame at a window: turned boxwood and ebony pieces on a lacquered board."""
import math, sys
import numpy as np
from pt import *

sc = Scene()

# ---- materials ----
def board_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    inside = (np.abs(x) < 4) & (np.abs(z) < 4)
    par = (np.floor(x + 4) + np.floor(z + 4)) % 2
    along = np.where(par == 0, x, z); across = np.where(par == 0, z, x)
    sq = np.floor(x + 4) * 7.3 + np.floor(z + 4) * 3.1
    ring = 0.5 + 0.5 * np.sin(across * 26 + 3 * fbm(along * 1.5 + sq, across * 6, oct=3) + sq)
    maple = V(0.58, 0.40, 0.21); maple2 = V(0.46, 0.30, 0.15)
    walnut = V(0.105, 0.050, 0.026); walnut2 = V(0.06, 0.028, 0.015)
    lt = maple[None] * (1 - ring[:, None] * 0.6) + maple2[None] * (ring[:, None] * 0.6)
    dk = walnut[None] * (1 - ring[:, None]) + walnut2[None] * ring[:, None]
    c = np.where((par == 0)[:, None], dk, lt)
    frame = V(0.075, 0.035, 0.018) * 1.0
    fr = frame[None] * (0.8 + 0.4 * fbm(x * 0.8 + z * 5, z * 0.8 + x * 5, oct=3))[:, None]
    return np.where(inside[:, None], c, fr).astype(f32)
board = Mat("plastic", tex=board_tex, f0=0.045, rough=0.035)

def table_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    g = 0.5 + 0.5 * np.sin(z * 9 + 4 * fbm(x * 0.2, z * 1.3, oct=4))
    return (V(0.20, 0.10, 0.05)[None] * (0.7 + 0.5 * g[:, None])).astype(f32)
table = Mat("plastic", tex=table_tex, f0=0.035, rough=0.12)

def ivory_tex(pl, pw, n):
    g = fbm(pw[:, 1] * 30 + pw[:, 0] * 2, pw[:, 2] * 2, oct=3)
    return (V(0.72, 0.56, 0.36)[None] * (0.9 + 0.2 * g[:, None])).astype(f32)
white = Mat("plastic", tex=ivory_tex, f0=0.045, rough=0.05)
black = Mat("plastic", alb=(0.018, 0.014, 0.012), f0=0.05, rough=0.035)

# ---- pieces (lathes, 1 unit = one square) ----
def put(objs, x, z, yaw=0):
    for o in objs:
        o.T = o.T + V(x, 0, z)
        if yaw:
            R = rot(yaw); o.R = R @ o.R; o.T = V(x, 0, z) + (o.T - V(x, 0, z)) @ R.T
        sc.add(o)

def pawn(m):
    return [Lathe(m, [(0, 0), (.33, 0), (.33, .05), (.30, .09), (.27, .12), (.21, .16), (.15, .22), (.115, .34),
                      (.10, .44), (.18, .47), (.18, .50), (.09, .53), (0, .53)]),
            Sphere(m, T=(0, .66, 0), S=.155)]
def rook(m):
    o = [Lathe(m, [(0, 0), (.38, 0), (.38, .06), (.34, .11), (.31, .15), (.24, .20), (.20, .28), (.18, .66),
                   (.25, .70), (.27, .74), (.27, .93), (0, .93)])]
    for a in range(0, 360, 90):
        c = math.radians(a + 45)
        o.append(Box(m, (.07, .07, .09), R=rot(-(a + 45)), T=(.19 * math.cos(c), 1.0, .19 * math.sin(c))))
    return o
def bishop(m):
    return [Lathe(m, [(0, 0), (.36, 0), (.36, .06), (.31, .11), (.28, .15), (.21, .20), (.15, .32), (.11, .68),
                      (.20, .72), (.20, .76), (.10, .80), (0, .80)]),
            Sphere(m, T=(0, 1.0, 0), S=(.16, .25, .16)), Sphere(m, T=(0, 1.29, 0), S=.055)]
def queen(m):
    o = [Lathe(m, [(0, 0), (.41, 0), (.41, .07), (.36, .12), (.33, .17), (.25, .22), (.18, .34), (.125, .88),
                   (.23, .93), (.23, .97), (.13, 1.01), (.15, 1.06), (.25, 1.27), (.21, 1.29), (.11, 1.31), (0, 1.34)]),
         Sphere(m, T=(0, 1.40, 0), S=.075)]
    for a in range(0, 360, 36):
        c = math.radians(a); o.append(Sphere(m, T=(.24 * math.cos(c), 1.29, .24 * math.sin(c)), S=.042))
    return o
def king(m):
    return [Lathe(m, [(0, 0), (.42, 0), (.42, .07), (.37, .12), (.34, .17), (.26, .22), (.19, .34), (.14, .95),
                      (.24, 1.00), (.24, 1.04), (.15, 1.08), (.17, 1.12), (.23, 1.31), (.24, 1.38), (.19, 1.44), (0, 1.44)]),
            Box(m, (.045, .17, .045), T=(0, 1.61, 0)), Box(m, (.13, .045, .045), T=(0, 1.64, 0))]

S = lambda f, r: (f - 3.5, 3.5 - r)        # file 0..7 (a..h), rank 0..7 from white's side
put(queen(white), *S(3, 4)); put(king(white), *S(5, 1), yaw=20); put(pawn(white), *S(1, 3)); put(pawn(white), *S(6, 2))
put(rook(white), *S(0, 1), yaw=10)
put(king(black), *S(2, 6), yaw=35); put(rook(black), *S(4, 7), yaw=5); put(bishop(black), *S(6, 5))
put(pawn(black), *S(1, 5)); put(pawn(black), *S(5, 5)); put(pawn(black), *S(7, 6))

sc.add(Box(board, (4.5, .15, 4.5), T=(0, -.15, 0)))
sc.add(Plane(table, T=(0, -.3, 0)))

# ---- light: a tall window to the left, warm room fill, a lamp far behind for bokeh ----
sc.rect_light((-11, 4.5, -1), 3.2, 4.5, (7.0, 7.3, 7.9), R=rot(roll=-90))
sc.sphere_light((9, 6, -18), 0.9, (60, 38, 18))
def env(d):
    y = d[:, 1]
    return (V(0.05, 0.04, 0.032)[None] * (0.6 + 0.6 * np.clip(y + 0.4, 0, 1))[:, None]).astype(f32)
sc.env = env

sc.camera(pos=(2.9, 1.25, 7.6), look=(-0.2, 0.75, 0.3), vfov=30, focus=None, aperture=0.075)
sc.cam["focus"] = float(np.linalg.norm(V(-0.5, 0.9, -0.5) - sc.cam["pos"]))   # the white queen
sc.exposure = 1.25; sc.vignette = 0.35

if __name__ == "__main__":
    if "--time" in sys.argv: print("s/spp", timing(sc)); sys.exit()
    run(sc, "02_chess", spp=int(sys.argv[1]) if len(sys.argv) > 1 else None)
