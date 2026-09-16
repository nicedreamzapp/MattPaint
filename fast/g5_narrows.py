"""GEN 5 — THE NARROWS. Built to GEN5_RULES.md.

PROMPT: "A slot canyon, light coming down from a narrow opening far above."

Read as light: a slot canyon is almost entirely INDIRECT light. Almost nothing is hit by the
sun. What you see is sandstone bouncing light off itself, over and over, going redder and
dimmer with every bounce — which is why real slot canyons glow orange in shadow. So this is a
BOUNCE painting: direct light is a thin sliver at the top, everything else is reflected.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5500)
W, H = 1380, 900
a = Art(W, H, "THE NARROWS")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

SLIT_X = W * 0.52          # where the opening sits, far above
FLOOR  = H * 0.93

SKY_SLIT  = (232, 240, 255)      # the one piece of direct daylight, cold
BOUNCE_1  = (255, 186, 92)       # first bounce: hot orange
BOUNCE_2  = (168, 78, 44)        # second: deeper red
BOUNCE_3  = (54, 26, 26)         # third and beyond: almost nothing left
SAND      = (198, 128, 72)

def wall_x(side, y, seed):
    """the canyon walls, carved by water: smooth flowing curves, never noise. The gap narrows
    as it rises toward the opening."""
    t = G.frac(y, TOPBAR, FLOOR)
    gap = W * (0.045 + 0.30 * t ** 1.35)                 # narrow at the top, open at the floor
    swirl = (G5.fbm(y * 0.0034 + seed, seed * 3.1, 4) - 0.5) * W * 0.16
    swirl += (G5.fbm(y * 0.011 + seed, seed * 7.7, 3) - 0.5) * W * 0.045
    return SLIT_X + side * gap + swirl

def light_reaching(x, y):
    """how much light has got this far, and how many bounces it took. Depth below the slit and
    distance from the canyon's centre both cost bounces."""
    t = G.frac(y, TOPBAR, FLOOR)
    lx = wall_x(-1, y, 1.7); rx = wall_x(1, y, 4.3)
    across = abs(x - (lx + rx) * 0.5) / max(1.0, (rx - lx) * 0.5)
    down = t ** 0.85
    amt = math.exp(-down * 2.6) * math.exp(-across * across * 0.55)
    bounces = 1.0 + down * 2.6 + across * 1.4
    return amt, bounces

def bounce_col(b):
    if b < 1.6: return mix(SKY_SLIT, BOUNCE_1, G.frac(b, 0.6, 1.6))
    if b < 2.8: return mix(BOUNCE_1, BOUNCE_2, G.frac(b, 1.6, 2.8))
    return mix(BOUNCE_2, BOUNCE_3, G.frac(b, 2.8, 4.4))

def build():
    # base coat: MattPaint's canvas starts WHITE, so anything the painting fails to cover reads
    # as a hole. Always lay a ground first.
    for y in range(TOPBAR, H, 4):
        R(0, y, W, 5, col(0.05, BOUNCE_3, 0.6))
    # ---- the gap itself, seen from the bottom: the sliver of sky, blown out
    # Looking UP a slot canyon you do not see a flat wedge of sand — you see the walls
    # continuing away from you, converging, with the sliver of sky only at the very top.
    # v1 filled the gap with one value per row and it read as a pale triangle.
    for y in range(TOPBAR, H, 2):
        lx = wall_x(-1, y, 1.7); rx = wall_x(1, y, 4.3)
        t = G.frac(y, TOPBAR, FLOOR)
        NC = max(3, int((rx - lx) / 9))
        for k in range(NC):
            x = lx + (rx - lx) * k / NC
            across = abs(x - (lx+rx)*0.5) / max(1.0, (rx-lx)*0.5)
            amt, b = light_reaching(x, y)
            # the far wall up the canyon: it gets darker fast with depth, and it has its own
            # fluting, so the gap is a receding SURFACE and not a gradient
            flute = (G5.fbm(x * 0.010, y * 0.006, 3) - 0.5) * 1.6
            deep = math.exp(-t * 3.4)
            v = 0.045 + 0.80 * deep * (0.55 + 0.45 * (1 - across)) + flute * 0.05
            R(x, y, (rx - lx) / NC + 2, 3,
              col(min(0.99, max(0.02, v)), bounce_col(b * 0.75 + t * 1.1), 0.64))

    # ---- THE WALLS. Their form is water-carved flutes: long vertical swells whose lit side
    # faces the centre of the canyon, because that is where the light is coming from.
    for side, seed in ((-1, 1.7), (1, 4.3)):
        y = TOPBAR
        while y < H:
            wx = wall_x(side, y, seed)
            amt, b = light_reaching(wx, y)
            # flutes: a slow periodic swell ACROSS the wall, from noise not from a sine
            span = wx if side < 0 else (W - wx)
            steps = int(abs(span) / 3) + 1
            for i in range(steps):
                p = i / max(1.0, steps - 1)
                x = wx + side * abs(span) * p   # OUTWARD from the wall face to the
                                                #ropes frame edge. v1 had this sign inverted, so both
                                                # walls painted INTO the canyon and the outer
                                                # thirds stayed BARE WHITE CANVAS.
                flute = (G5.fbm(x * 0.012, y * 0.0055, 3) - 0.5) * 2.0
                nx = side * (0.35 + 0.65 * p) + flute * 0.55
                nn = math.hypot(nx, -0.45) or 1.0
                # light arrives from the middle of the canyon and from above
                to_light = (-side * 0.72, -0.69)
                lit = G5.shade(nx / nn, -0.45 / nn, to_light, ambient=0.26)
                a_here, b_here = light_reaching(x, y)
                v = 0.035 + 0.74 * a_here ** 0.55 * (0.30 + 0.70 * lit)
                # deeper into the wall = more bounces = redder and darker
                R(x, y, 4, 3, col(min(0.97, v), bounce_col(b_here + p * 1.2), 0.70))
            y += 3

    # ---- the water-carved grain: long horizontal strata following the flow, never vertical
    for _ in range(34000):
        y = random.uniform(TOPBAR, FLOOR)
        lx = wall_x(-1, y, 1.7); rx = wall_x(1, y, 4.3)
        if random.random() < 0.5:
            x = random.uniform(0, lx)
        else:
            x = random.uniform(rx, W)
        amt, b = light_reaching(x, y)
        band = G5.fbm(x * 0.002, y * 0.020, 3)
        v = 0.035 + 0.70 * amt ** 0.55 + (band - 0.5) * 0.14
        ln = random.uniform(8, 40)
        L(x, y, x + ln, y + random.gauss(0, 2.2), random.uniform(0.6, 1.8),
          col(max(0.02, min(0.97, v)), bounce_col(b + random.uniform(-0.2, 0.4)), 0.72))

    # ---- the floor: sand, catching whatever made it all the way down
    for y in range(int(FLOOR), H, 2):
        lx = wall_x(-1, y, 1.7); rx = wall_x(1, y, 4.3)
        amt, b = light_reaching((lx+rx)*0.5, y)
        R(0, y, W, 3, col(0.035 + 0.30 * amt ** 0.6, bounce_col(b + 0.8), 0.6))

    # ---- dust hanging in the shaft, which is the only thing that makes the light visible
    for _ in range(2200):
        y = TOPBAR + random.random() ** 1.7 * (FLOOR - TOPBAR)
        lx = wall_x(-1, y, 1.7); rx = wall_x(1, y, 4.3)
        x = random.uniform(lx, rx)
        amt, b = light_reaching(x, y)
        if amt < 0.22: continue
        D(x, y, random.uniform(0.9, 2.6), col(min(0.94, 0.50 + 0.42*amt), bounce_col(b*0.8), 0.5),
          min(0.30, 0.04 + 0.26 * amt))

build()
OUT = "g5_narrows_gray.png" if GRAY else "g5_narrows.png"
asyncio.run(G5.paint(a, OUT, {"subject": "the_narrows",
    "prompt": "A slot canyon, light coming down from a narrow opening far above."},
    gray=GRAY, focal_y=H*0.5))
