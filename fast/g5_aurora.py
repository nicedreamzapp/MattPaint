"""GEN 5 — AURORA LAKE.  *** HOLDOUT — PAINTED ONCE, NEVER DIAGNOSED, NEVER ITERATED. ***

PROMPT: "Aurora over a still lake at night, the light mirrored in the water."

This subject was held out of every tuning pass all night, so that there is one landscape the
rules were never fitted to. Whatever this run produces is the answer. It does not get fixed.

Read as light: the aurora IS the light source and it is above and behind everything. A still
lake is a mirror, so the whole sky is repeated, slightly dimmer and slightly blurred, and the
shoreline is the only dark thing in frame.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN · HOLDOUT" + (" · FLAT GRAY" if GRAY else "")
random.seed(5900)
W, H = 1380, 900
a = Art(W, H, "AURORA LAKE")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

SHORE = H * 0.56                       # the waterline
NIGHT_HI, NIGHT_LO = (6, 10, 24), (22, 34, 62)
AUR_G = (74, 240, 158)
AUR_C = (58, 196, 224)
AUR_M = (176, 96, 226)
RIDGE = (10, 14, 26)

def curtain(i, x, y):
    """An aurora is vertical CURTAINS with ragged lower edges, drifting along a band. It is
    brightest where it is folded, and it fades upward, not downward."""
    base = SHORE - 40 - i * 46
    top = base - 320 - i * 60
    if y > base or y < top: return 0.0
    fold = G5.fbm(x * 0.0030 + i * 4.7, 0.5, 4)
    drift = (fold - 0.5) * 220
    band = math.exp(-(((x - (W * 0.5 + drift)) / (W * (0.34 + 0.08 * i))) ** 2) * 1.1)
    down = G.frac(y, top, base)
    ragged = G5.ridged(x * 0.010 + i * 9.1, y * 0.0016, 2, 3.0)
    v = band * (0.30 + 0.90 * ragged) * (down ** 0.7) * (1.0 - down * 0.25)
    return max(0.0, v)

def aurora_at(x, y):
    tot = 0.0; r = g = b = 0.0
    for i, c in enumerate((AUR_G, AUR_C, AUR_M)):
        v = curtain(i, x, y)
        if v <= 0: continue
        tot += v; r += c[0]*v; g += c[1]*v; b += c[2]*v
    if tot <= 0: return 0.0, NIGHT_HI
    return tot, (r/tot, g/tot, b/tot)

def build():
    for y in range(TOPBAR, H, 4):
        R(0, y, W, 5, col(0.03, NIGHT_HI, 0.5))
    # the night sky and the aurora in it
    for y in range(TOPBAR, int(SHORE)+4, 2):
        NC = 130
        for k in range(NC):
            x0 = W*k/NC; xm = x0 + W/(2.0*NC)
            amt, c = aurora_at(xm, y)
            v = 0.030 + 0.045*(1-G.frac(y,TOPBAR,SHORE)) + 0.68*min(1.0, amt)**0.75
            R(x0, y, W/NC+2, 3, col(v, mix(mix(NIGHT_HI,NIGHT_LO,G.frac(y,TOPBAR,SHORE)), c,
                                           min(0.92, amt*1.4)), 0.72))
    for _ in range(1600):
        x=random.uniform(0,W); y=random.uniform(TOPBAR,SHORE)
        amt,_c = aurora_at(x,y)
        if amt > 0.12 and random.random()<0.7: continue
        D(x,y,random.uniform(0.6,1.5), col(random.uniform(0.35,0.92),(226,232,255),0.3),
          random.uniform(0.3,0.9))

    # far shore: the only dark thing in frame, and it hides the waterline's far edge
    hz = G5.envelope(31, W, SHORE+4, H*0.10, 3)
    for x in range(0, W, 3):
        y = hz(x)
        R(x, y, 4, SHORE - y + 6, col(0.022, RIDGE, 0.5))

    # ---- THE MIRROR. A still lake repeats the sky, dimmer, and smeared vertically by the
    # faintest movement on the surface. The reflection is the subject as much as the sky is.
    for y in range(int(SHORE), H, 2):
        d = G.frac(y, SHORE, H)
        sy = SHORE - (y - SHORE) * 1.0                 # the mirrored row
        NC = 130
        for k in range(NC):
            x0 = W*k/NC; xm = x0 + W/(2.0*NC)
            smear = (G5.fbm(xm*0.004, y*0.03, 3) - 0.5) * (6 + 30*d)
            amt, c = aurora_at(xm + smear*0.6, max(TOPBAR, sy + smear))
            v = 0.026 + 0.50*min(1.0, amt)**0.8 * (1.0 - d*0.45)
            R(x0, y, W/NC+2, 3, col(v, mix(NIGHT_HI, c, min(0.85, amt*1.25)), 0.70))
    # the surface itself: long horizontal glints where the water is not quite still
    for _ in range(26000):
        y = SHORE + random.random()**0.75 * (H - SHORE)
        x = random.uniform(0, W)
        d = G.frac(y, SHORE, H)
        sy = SHORE - (y - SHORE)
        amt, c = aurora_at(x, max(TOPBAR, sy))
        if amt < 0.05: continue
        L(x, y, x + random.uniform(4, 30)*(0.5+d), y + random.gauss(0, 0.8),
          random.uniform(0.5, 1.6), col(min(0.95, 0.30 + 0.60*amt), c, 0.65))
    # the near shore, bottom edge
    for _ in range(4000):
        x = random.uniform(0,W); y = H - random.random()**1.6 * H*0.07
        D(x, y, random.uniform(2,9), col(0.020, RIDGE, 0.5), 0.5)

build()
OUT = "g5_aurora_gray.png" if GRAY else "g5_aurora.png"
asyncio.run(G5.paint(a, OUT, {"subject": "aurora_lake", "holdout": True,
    "prompt": "Aurora over a still lake at night, the light mirrored in the water."},
    gray=GRAY, focal_y=H*0.6))
