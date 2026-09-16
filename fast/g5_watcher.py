"""GEN 5 — THE WATCHER. Built to GEN5_RULES.md.

PROMPT: "A creature on a branch at night, watching."

Read as light: at night with no sun there is only a moon and sky glow, so almost everything is
silhouette. That is a gift, not a limitation — a form half-lost in darkness is READ AS CORRECT,
which is exactly why chiaroscuro exists, and it is the honest way to paint an animal given that
this system cannot know real anatomy. So the creature is built as a shape the moonlight rims,
with two eyes catching the light, and nothing else claimed.

The branch it sits on COMPRESSES under its weight — a creature resting on something that does
not respond to it reads as pasted on.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5700)
W, H = 1380, 900
a = Art(W, H, "THE WATCHER")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

MOONX, MOONY = W * 0.74, H * 0.22
TO_MOON = (0.62, -0.78)
NIGHT_HI, NIGHT_LO = (8, 12, 26), (46, 58, 86)
MOON_C  = (226, 234, 255)
EYE_C   = (236, 206, 120)

BX, BY = W * 0.10, H * 0.62            # the branch, running left to right, sagging
def branch_y(x):
    t = G.frac(x, BX, W)
    sag = 96 * G5.env(t, 0.9)                     # its own weight
    load = 54 * math.exp(-((x - W*0.44) / 150.0) ** 2)   # the creature's weight
    return BY + sag + load

def branch_r(x):
    return 26 * (1.0 - 0.55 * G.frac(x, BX, W))

def sky_v(x, y):
    d = math.hypot((x - MOONX) / (W*0.55), (y - MOONY) / (H*0.55))
    return 0.05 + 0.10 * (1 - G.frac(y, TOPBAR, H)) + 0.34 * math.exp(-d*d*1.3)

def build():
    for y in range(TOPBAR, H, 3):
        NC = 60
        for k in range(NC):
            x0 = W*k/NC; xm = x0 + W/(2.0*NC)
            R(x0, y, W/NC+2, 4, col(sky_v(xm, y), mix(NIGHT_HI, NIGHT_LO,
                                                      G.frac(y, TOPBAR, H) ** 0.7), 0.5))
    # the moon: a small disc and a wide halo in the humid air
    for k in range(120):
        u = k/120.0
        D(MOONX, MOONY, 300*(1-u)**1.8 + 6, col(0.30 + 0.62*u*u, MOON_C, 0.35), 0.010*(u**2.3))
    D(MOONX, MOONY, 26, col(0.97, MOON_C, 0.25), 1.0)

    # far trees: shapes that only interrupt the sky glow
    for i in range(90):
        x = random.uniform(-40, W+40)
        h = random.uniform(H*0.12, H*0.38)
        base = H*0.80 + random.uniform(-20, 30)
        for _ in range(int(h*0.7)):
            yy = base - random.random()**0.7 * h
            ww = (1 - G.frac(base-yy, 0, h)) * random.uniform(8, 34)
            D(x + random.gauss(0, ww), yy, random.uniform(2, 7),
              col(0.030 + 0.02*random.random(), NIGHT_HI, 0.4), 0.55)

    # ---- THE BRANCH: a cylinder rimmed by the moon on its upper-right
    x = BX
    while x < W + 20:
        by = branch_y(x); br = branch_r(x)
        k = -br
        while k <= br:
            u = k/br
            nz = math.sqrt(max(0.0, 1-u*u))
            lit = G5.shade(u*0.8, -nz*0.8, TO_MOON, ambient=0.16)
            v = 0.020 + 0.22*lit
            D(x, by + k, 2.0, col(v, G5.temp(lit, MOON_C, NIGHT_HI), 0.45), 1.0)
            k += 1.8
        # bark, only where the moon can reach it
        if random.random() < 0.5:
            for _ in range(3):
                kk = random.uniform(-br, br)
                u = kk/br
                lit = G5.shade(u*0.8, -math.sqrt(max(0,1-u*u))*0.8, TO_MOON, ambient=0.16)
                if lit < 0.35: continue
                L(x, by+kk, x+random.uniform(6, 22), by+kk+random.gauss(0,1.4),
                  random.uniform(0.5,1.2), col(0.030 + 0.26*lit, MOON_C, 0.35))
        x += 2.0

    # ---- THE CREATURE. Mass and rim only. No anatomy is claimed that cannot be known.
    CX_, CY_ = W*0.44, branch_y(W*0.44) - 78
    PARTS = [(CX_, CY_ + 16, 66, 60),          # body
             (CX_ - 6, CY_ - 40, 40, 36),      # head
             (CX_ + 44, CY_ + 30, 26, 44)]     # haunch
    def inside(px, py):
        for (ox, oy, rx, ry) in PARTS:
            if ((px-ox)/rx)**2 + ((py-oy)/ry)**2 <= 1.0: return True
        return False
    for _ in range(46000):
        px = CX_ + random.gauss(0, 64); py = CY_ + random.gauss(0, 58)
        if not inside(px, py): continue
        # the nearest part gives the normal
        best = None; bd = 1e9
        for (ox, oy, rx, ry) in PARTS:
            d = ((px-ox)/rx)**2 + ((py-oy)/ry)**2
            if d < bd: bd = d; best = (ox, oy, rx, ry)
        ox, oy, rx, ry = best
        nx = (px-ox)/rx; ny = (py-oy)/ry
        n = math.hypot(nx, ny) or 1.0; nx/=n; ny/=n
        lit = G5.shade(nx, ny, TO_MOON, ambient=0.10)
        # fur breaks the rim into strands rather than a clean edge
        v = 0.012 + 0.30 * (lit ** 2.2)
        D(px, py, random.uniform(1.2, 3.0), col(v, G5.temp(lit, MOON_C, NIGHT_HI), 0.40), 0.55)
    # fur on the true outer boundary, lit side only — strands, never an outline
    for _ in range(9000):
        ang = random.uniform(-2.2, 0.9)
        for (ox, oy, rx, ry) in PARTS:
            px = ox + math.cos(ang)*rx; py = oy + math.sin(ang)*ry
            # occlusion test: skip any point swallowed by another part
            sw = False
            for (qx, qy, qrx, qry) in PARTS:
                if (qx,qy,qrx,qry) == (ox,oy,rx,ry): continue
                if ((px-qx)/qrx)**2 + ((py-qy)/qry)**2 < 1.04: sw = True; break
            if sw: continue
            nx, ny = math.cos(ang), math.sin(ang)
            lit = G5.shade(nx, ny, TO_MOON, ambient=0.05)
            if lit < 0.5: continue
            ln = random.uniform(3, 11)
            L(px, py, px+nx*ln, py+ny*ln, random.uniform(0.5, 1.1),
              col(0.10 + 0.42*lit, MOON_C, 0.35))
    # ears
    for s in (-1, 1):
        for _ in range(900):
            t = random.random()
            ex = CX_ - 6 + s*26 + random.gauss(0, 7)
            ey = CY_ - 40 - 24*t + random.gauss(0, 5)
            lit = G5.shade(s*0.7, -0.7, TO_MOON, ambient=0.08)
            D(ex, ey, random.uniform(1.0, 2.4), col(0.014 + 0.26*lit, MOON_C, 0.35), 0.5)
    # ---- THE EYES: two small discs that catch the moon. The whole picture rests on them.
    for s in (-1, 1):
        ex = CX_ - 6 + s*13; ey = CY_ - 44
        D(ex, ey, 7.5, col(0.05, NIGHT_HI, 0.4), 0.9)
        D(ex, ey, 5.4, col(0.74, EYE_C, 0.85), 1.0)
        D(ex + s*1.4, ey - 1.4, 1.8, col(0.97, MOON_C, 0.4), 1.0)

    # a few moths in the moonlight, so the night has something moving in it
    for _ in range(26):
        mx = random.uniform(W*0.3, W); my = random.uniform(H*0.15, H*0.6)
        D(mx, my, random.uniform(1.2, 2.6), col(0.55, MOON_C, 0.4), 0.7)

build()
OUT = "g5_watcher_gray.png" if GRAY else "g5_watcher.png"
asyncio.run(G5.paint(a, OUT, {"subject": "the_watcher",
    "prompt": "A creature on a branch at night, watching."}, gray=GRAY, focal_y=H*0.55))
