"""GEN 5 — THE GLASS CHOIR. Built to GEN5_RULES.md.

PROMPT: "The inside of a cathedral, light coming through stained glass."

Read as light: the windows ARE the light sources and they are coloured. Everything else in the
building is stone that has been reached by coloured light — which means the architecture is not
drawn, it is revealed. Shafts hang in the dusty air; pools of colour lie on the floor and climb
the opposite piers. A cathedral interior is very dark, and that darkness is what makes the glass
read as glass rather than as decoration.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5600)
W, H = 1380, 900
a = Art(W, H, "THE GLASS CHOIR")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

FLOOR = H * 0.88
VP_X, VP_Y = W * 0.50, H * 0.52        # one-point perspective, eye level
STONE = (96, 88, 76)
STONE_D = (18, 17, 16)

# Each window has its OWN small palette with a DOMINANT hue — a window is red, or blue, not a
# fruit salad. Panes are large fields, because real stained glass is lead-lined fields of
# colour, not confetti.
PALETTES = [
    [(206, 44, 36), (226, 92, 40), (238, 178, 52), (92, 22, 26)],      # a red window
    [(30, 66, 178), (46, 116, 206), (150, 196, 232), (18, 34, 92)],     # a blue window
    [(206, 44, 36), (236, 186, 46), (24, 122, 92), (110, 26, 30)],      # red / gold
    [(30, 66, 178), (24, 132, 92), (236, 186, 46), (176, 54, 156)],     # the rose: mixed
]
def glass_col(i, u, v):
    pal = PALETTES[i % len(PALETTES)]
    n = G5.vnoise(u * 3.1 + i * 13, v * 4.0)           # LARGE fields, not speckle
    return pal[int(n * (len(pal) - 0.001))]

# Light that has passed through a whole window and crossed a room is MIXED — it arrives as ONE
# tint, not as a mosaic. v1 tinted the stone and the shafts with individual pane colours and the
# entire cathedral came out as coloured noise. Only the GLASS shows separate panes.
def window_tint(i):
    """the DOMINANT hue, not the average. Averaging saturated colours gives mud, which is
    exactly what v2 produced: a grey cathedral lit by grey light."""
    pal = PALETTES[i % len(PALETTES)]
    counts = [0] * len(pal)
    for u in range(14):
        for v in range(14):
            n = G5.vnoise(u * 0.28 + i * 13, v * 0.31)
            counts[int(n * (len(pal) - 0.001))] += 1
    dom = pal[counts.index(max(counts))]
    # push it a little further from grey, because light that reaches a wall is still coloured
    m = (dom[0] + dom[1] + dom[2]) / 3.0
    return tuple(min(255, m + (c - m) * 1.45) for c in dom)

# the windows: tall lancets high in the wall on the left, and a rose high right
WINDOWS = []
for k in range(3):
    WINDOWS.append(dict(kind="lancet", x=W*(0.07 + 0.105*k), y=H*0.16,
                        w=W*0.052, h=H*0.34, i=k))
WINDOWS.append(dict(kind="rose", x=W*0.86, y=H*0.26, w=W*0.16, h=W*0.16, i=7))
for _w in WINDOWS: _w["tint"] = window_tint(_w["i"])

def win_amount(win, x, y):
    if win["kind"] == "lancet":
        dx = (x - win["x"]) / (win["w"] * 0.5); dy = (y - win["y"]) / (win["h"] * 0.5)
        if abs(dx) > 1 or abs(dy) > 1: return 0.0, 0.0, 0.0
        # pointed arch: the top tapers
        if dy < -0.35 and abs(dx) > (1.0 - (abs(dy) - 0.35) / 0.65): return 0.0, 0.0, 0.0
        return 1.0, (dx + 1) * 0.5, (dy + 1) * 0.5
    d = math.hypot(x - win["x"], y - win["y"]) / (win["w"] * 0.5)
    if d > 1: return 0.0, 0.0, 0.0
    ang = math.atan2(y - win["y"], x - win["x"])
    return 1.0, (ang / 6.2832 + 0.5), d

def build():
    # base coat: the canvas starts white, and an unpainted hole would read as a blown window
    for y in range(TOPBAR, H, 4):
        R(0, y, W, 5, col(0.035, STONE_D, 0.5))

    # ---- the stone, lit ONLY by what the windows throw at it
    for y in range(TOPBAR, H, 3):
        NC = 96
        for k in range(NC):
            x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
            amt = 0.0; r = g = b = 0.0
            for win in WINDOWS:
                dist = math.hypot(xm - win["x"], (y - win["y"]) * 0.8) / (W * 0.55)
                v = 1.0 / (1.0 + dist * dist * 9.0)
                c = win["tint"]
                amt += v; r += c[0]*v; g += c[1]*v; b += c[2]*v
            if amt <= 0: continue
            c = (r/amt, g/amt, b/amt)
            # perspective: the vault recedes, so value falls toward the vanishing point
            dep = 1.0 - min(1.0, math.hypot(xm - VP_X, y - VP_Y) / (W * 0.62))
            v = 0.035 + 0.30 * min(1.0, amt) ** 0.7 * (0.45 + 0.55 * dep)
            R(x0, y, W/NC + 2, 4, col(v, mix(STONE, c, min(0.90, amt * 1.5)), 0.72))

    # ---- piers and arches: revealed by the light grazing them, never outlined
    for k in range(6):
        px = W * (0.10 + 0.16 * k)
        pw = W * 0.030 * (0.6 + 0.4 * abs(px - VP_X) / (W*0.5))
        y = TOPBAR + 20
        while y < FLOOR:
            hw = pw * 0.5 * (1.0 + 0.22 * max(0.0, (y - FLOOR + 90) / 90))
            kk = -hw
            while kk <= hw:
                u = kk / max(1.0, hw)
                amt = 0.0; r = g = b = 0.0
                for win in WINDOWS:
                    to = (win["x"] - (px+kk), win["y"] - y)
                    n = math.hypot(*to) or 1.0
                    lit = max(0.0, u * (to[0]/n) * -1.0 + 0.30)
                    dist = n / (W * 0.55)
                    v = lit / (1.0 + dist*dist*7.0)
                    c = win["tint"]
                    amt += v; r += c[0]*v; g += c[1]*v; b += c[2]*v
                if amt > 0:
                    c = (r/amt, g/amt, b/amt)
                    R(px+kk, y, 3, 4, col(0.030 + 0.44*min(1.0, amt)**0.65,
                                          mix(STONE, c, min(0.75, amt)), 0.58))
                kk += 2.6
            y += 3

    # ---- THE WINDOWS themselves: the brightest thing by a long way, in small saturated panes
    for win in WINDOWS:
        n = 26000 if win["kind"] == "lancet" else 34000
        for _ in range(n):
            if win["kind"] == "lancet":
                x = win["x"] + random.uniform(-1, 1) * win["w"] * 0.5
                y = win["y"] + random.uniform(-1, 1) * win["h"] * 0.5
            else:
                ang = random.uniform(0, 6.2832); rr = math.sqrt(random.random())
                x = win["x"] + math.cos(ang) * rr * win["w"] * 0.5
                y = win["y"] + math.sin(ang) * rr * win["w"] * 0.5
            ok, u, v = win_amount(win, x, y)
            if ok <= 0: continue
            c = glass_col(win["i"], u * 2.4, v * 2.4)
            # leading between panes: dark, thin, and it is what makes glass read as glass
            lead = G5.vnoise(u * 3.1 + win["i"] * 13, v * 4.0)
            if 0.485 < lead < 0.515:
                D(x, y, random.uniform(1.0, 2.2), col(0.04, STONE_D, 0.4), 0.85); continue
            D(x, y, random.uniform(1.8, 4.2), col(0.58 + 0.34*random.random(), c, 0.92), 0.95)

    # ---- the shafts: coloured light hanging in the dusty air of the nave
    for win in WINDOWS:
        for _ in range(9000):
            p = random.random() ** 0.7
            x = win["x"] + (VP_X - win["x"]) * p * 1.15 + random.gauss(0, 10 + 26*p)
            y = win["y"] + (FLOOR - win["y"]) * p * 1.02 + random.gauss(0, 8 + 20*p)
            if y > H or x < -50 or x > W + 50: continue
            c = win["tint"]
            fall = (1 - p) ** 1.5
            D(x, y, random.uniform(2, 9) * (0.6 + 1.2*p), col(0.58 + 0.30*fall, c, 0.88),
              min(0.042, 0.006 + 0.040 * fall))

    # ---- the pools of colour the windows throw onto the floor
    for y in range(int(FLOOR), H, 2):
        NC = 90
        for k in range(NC):
            x0 = W*k/NC; xm = x0 + W/(2.0*NC)
            amt = 0.0; r = g = b = 0.0
            for win in WINDOWS:
                cx = win["x"] + (VP_X - win["x"]) * 1.30
                d = math.hypot(xm - cx, (y - FLOOR - 40) * 2.2) / (W * 0.26)
                v = math.exp(-d*d*1.5)
                c = win["tint"]
                amt += v; r += c[0]*v; g += c[1]*v; b += c[2]*v
            base = 0.030 + 0.03 * G.frac(y, FLOOR, H)
            if amt > 0.02:
                c = (r/amt, g/amt, b/amt)
                R(x0, y, W/NC+2, 3, col(base + 0.52*min(1.0, amt)**0.7,
                                        mix(STONE, c, min(0.85, amt*1.2)), 0.68))
            else:
                R(x0, y, W/NC+2, 3, col(base, STONE_D, 0.5))

build()
OUT = "g5_choir_gray.png" if GRAY else "g5_choir.png"
asyncio.run(G5.paint(a, OUT, {"subject": "the_glass_choir",
    "prompt": "The inside of a cathedral, light coming through stained glass."},
    gray=GRAY, focal_y=H*0.55))
