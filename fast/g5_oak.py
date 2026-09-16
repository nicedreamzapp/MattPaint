"""GEN 5 — THE ACORN YEAR. Built to GEN5_RULES.md.

PROMPT: "A big oak tree heavy with acorns, standing alone in a meadow."

Read as light: a lone oak in open ground is a LIGHT TRAP. The canopy is not foliage, it is a
volume that swallows light — bright and warm on the lit outside, deep and cool inside, with
holes where the sky comes through. Those holes are the only thing that makes a canopy read as
a canopy instead of a green cloud.

This is also the painting where gen2 learned its best lesson: it got BETTER by removing 125,929
strokes, because half its dabs were below the alpha threshold where anything registers. Nothing
here is drawn below that threshold.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5400)
W, H = 1380, 900
a = Art(W, H, "THE ACORN YEAR")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

HOR = H * 0.70
GND = H * 0.78
TO_SUN = (-0.62, -0.78)               # sun high-left, late afternoon
SKY_HI, SKY_LO = (74, 118, 176), (196, 214, 226)
LEAF_LIT, LEAF_DK = (168, 186, 86), (22, 44, 34)
BARK_LIT, BARK_DK = (176, 148, 112), (34, 26, 20)
GRASS_LIT, GRASS_DK = (206, 194, 116), (62, 72, 40)
ACORN = (156, 116, 58)

TX, TY = W * 0.46, GND              # trunk base
TRUNK_H = H * 0.30
CANOPY_CX, CANOPY_CY = TX + W*0.01, GND - TRUNK_H - H*0.10
CANOPY_RX, CANOPY_RY = W * 0.30, H * 0.20

def sky_v(y): return 0.44 + 0.40 * G.frac(y, TOPBAR, HOR) ** 0.8
def sky_h(y): return mix(SKY_HI, SKY_LO, G.frac(y, TOPBAR, HOR) ** 0.9)

# An oak canopy is not one dome. It is a handful of separate LOBES, each sitting on its own
# limb, with real sky between them. v1 used a single ellipse and the tree came out as broccoli.
_rl = random.Random(77)
LOBES = []
for _i in range(9):
    _a = _rl.uniform(0, 6.2832); _r = _rl.random() ** 0.6
    LOBES.append((CANOPY_CX + math.cos(_a) * CANOPY_RX * 0.62 * _r,
                  CANOPY_CY + math.sin(_a) * CANOPY_RY * 0.70 * _r,
                  _rl.uniform(0.26, 0.52) * CANOPY_RX,
                  _rl.uniform(0.30, 0.58) * CANOPY_RY))

def canopy_density(x, y):
    """the canopy as separate lit VOLUMES with sky between them, never one silhouette"""
    best = 0.0
    for (cx, cy, rx, ry) in LOBES:
        dx = (x - cx) / rx; dy = (y - cy) / ry
        r = dx*dx + dy*dy
        if r > 1.30: continue
        best = max(best, max(0.0, 1.0 - r) ** 0.52)
    if best <= 0.0: return 0.0
    grain = G5.fbm(x * 0.0085, y * 0.011, 4)
    return max(0.0, best * (0.30 + 1.25 * grain) - 0.26)

def build():
    for y in range(TOPBAR, int(HOR) + 4, 2):
        R(0, y, W, 3, col(sky_v(y), sky_h(y), 0.55))
    # meadow: value from how much sun the ground gets, losing detail with distance
    for y in range(int(HOR), H, 2):
        d = G.frac(y, HOR, H)
        NC = 40
        for k in range(NC):
            x0 = W*k/NC; xm = x0 + W/(2.0*NC)
            v = 0.34 + 0.30 * d + 0.06 * G5.fbm(xm*0.004, y*0.02, 3)
            v = v * (0.55 + 0.45 * G.frac(y, HOR - 26, HOR + 40)) + sky_v(y) * 0.45 * (1 - G.frac(y, HOR - 26, HOR + 40))
            R(x0, y, W/NC+2, 3, col(v, mix(mix(GRASS_LIT, SKY_LO, 0.45*(1-d)), GRASS_DK, d*0.75), 0.6))

    # ---- TRUNK and limbs. A trunk is a cylinder; a limb leaves it by swelling, not by meeting.
    def limb(x0, y0, ang, ln, w, depth=0):
        if depth > 4 or ln < 14 or w < 1.6: return
        x1 = x0 + math.cos(ang)*ln; y1 = y0 + math.sin(ang)*ln
        steps = max(6, int(ln/3))
        for i in range(steps):
            t = i/steps
            cx = x0 + (x1-x0)*t; cy = y0 + (y1-y0)*t
            # junction swell, capped and confined to the first 8%, then tapered
            sw = (1.0 + 0.30 * max(0.0, 1 - t/0.08)) if t < 0.08 else ((1-t)**1.6*0.22 + 0.86)
            hw = w * sw
            k = -hw
            while k <= hw:
                u = k/max(1.0,hw)
                lit = G5.shade(u, -0.3, TO_SUN, ambient=0.30)
                inside = canopy_density(cx+k, cy)
                lit *= (1.0 - min(0.72, inside * 1.5))     # the canopy shades its own trunk
                v = 0.055 + 0.34*lit
                D(cx+k, cy, 1.7, col(v, G5.temp(lit, BARK_LIT, BARK_DK), 0.5), 1.0)
                k += 1.6
        for s in (-1, 1):
            limb(x1, y1, ang + s*random.uniform(0.34, 0.64), ln*random.uniform(0.60, 0.74),
                 w*0.66, depth+1)
        if random.random() < 0.4:
            limb(x1, y1, ang + random.gauss(0, 0.30), ln*0.55, w*0.55, depth+1)
    # the trunk itself
    for y in range(int(TY), int(TY-TRUNK_H), -2):
        t = G.frac(TY-y, 0, TRUNK_H)
        hw = W*0.036*(1-t*0.42)*(1.0 + 0.30*max(0.0,(0.12-t)/0.12))   # root flare
        k = -hw
        while k <= hw:
            u = k/hw
            lit = G5.shade(u, -0.3, TO_SUN, ambient=0.30)
            lit *= (1.0 - min(0.70, canopy_density(TX+k, y) * 1.4))
            D(TX+k, y, 1.8, col(0.055+0.34*lit, G5.temp(lit, BARK_LIT, BARK_DK), 0.5), 1.0)
            k += 1.7
    for s in (-1, 1):
        for j in range(3):
            limb(TX + s*W*0.012, TY-TRUNK_H+j*8, -1.5708 + s*random.uniform(0.25, 0.75),
                 H*0.10, W*0.020)

    # ---- THE CANOPY as a lit volume. Nothing below the visible alpha threshold.
    N = 52000
    for _ in range(N):
        x = CANOPY_CX + random.gauss(0, CANOPY_RX*0.52)
        y = CANOPY_CY + random.gauss(0, CANOPY_RY*0.52)
        dens = canopy_density(x, y)
        if dens < 0.05: continue
        # how deep inside the volume: outside is lit and warm, inside is deep and cool
        dx = (x - CANOPY_CX)/CANOPY_RX; dy = (y - CANOPY_CY)/CANOPY_RY
        nx, ny = dx, dy
        n = math.hypot(nx, ny) or 1.0
        nx /= n; ny /= n
        lit = G5.shade(nx, ny, TO_SUN, occ=min(0.68, dens*0.85), ambient=0.34)
        v = 0.055 + 0.42*lit
        rr = random.uniform(1.6, 5.2)
        al = 0.30 + 0.55*min(1.0, dens)          # never below where anything registers
        D(x, y, rr, col(v, G5.temp(lit, LEAF_LIT, LEAF_DK), 0.62), al)
    # sky holes: the thing that makes a canopy read as a canopy
    for _ in range(3000):
        x = CANOPY_CX + random.gauss(0, CANOPY_RX*0.50)
        y = CANOPY_CY + random.gauss(0, CANOPY_RY*0.50)
        dens = canopy_density(x, y)
        if not (0.06 < dens < 0.22): continue        # holes INSIDE the mass, not around it
        D(x, y, random.uniform(1.0, 3.0), col(sky_v(y) - 0.04, sky_h(y), 0.45), 0.42)

    # ---- ACORNS: heavy, clustered, each with a contact shadow on the leaf behind it
    for _ in range(420):
        x = CANOPY_CX + random.gauss(0, CANOPY_RX*0.46)
        y = CANOPY_CY + random.gauss(0, CANOPY_RY*0.46)
        if canopy_density(x, y) < 0.30: continue
        for j in range(random.randint(1, 3)):
            ax = x + random.gauss(0, 9); ay = y + random.gauss(0, 7)
            D(ax+1.4, ay+2.4, 4.2, col(0.05, LEAF_DK, 0.5), 0.55)      # contact shadow first
            D(ax, ay, 3.4, col(0.30, ACORN, 0.7), 1.0)
            D(ax-1.0, ay-1.2, 1.5, col(0.56, mix(ACORN,(255,240,210),0.5), 0.6), 0.9)

    # ---- the tree's own shadow on the meadow, cast away from the sun
    for _ in range(9000):
        t = random.random()**0.7
        sx = TX + 260*t + random.gauss(0, 60*(0.4+t))
        sy = GND + random.gauss(0, 12 + 22*t)
        if sy < HOR: continue
        soft = (1-t)**1.6
        D(sx, sy, random.uniform(5, 26)*(0.5+t), col(0.20, mix(GRASS_DK, SKY_HI, 0.35), 0.5),
          0.070*soft + 0.006)
    # near grass, only in the front strip
    for _ in range(5200):
        x = random.uniform(0, W); y = random.uniform(H*0.88, H)
        h = random.uniform(10, 34)
        lit = random.random()
        L(x, y, x+random.gauss(0,4), y-h, random.uniform(0.7,1.6),
          col(0.14+0.34*lit, G5.temp(lit, GRASS_LIT, GRASS_DK), 0.7))

build()
OUT = "g5_oak_gray.png" if GRAY else "g5_oak.png"
asyncio.run(G5.paint(a, OUT, {"subject": "the_acorn_year",
    "prompt": "A big oak tree heavy with acorns, standing alone in a meadow."},
    gray=GRAY, focal_y=H*0.55))
