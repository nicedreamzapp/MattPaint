"""GEN 5 — NIGHT RUN. Built to GEN5_RULES.md.

PROMPT: "A car on a wet road at night, its lights broken and stretched in the reflections."

Read as light: at night there is no ambient. Everything visible is either a SOURCE or something
a source reached. The car is not an object with headlights attached — it is two sources, and
the picture is what they light. Wet asphalt is a mirror with texture, so every source is
repeated downward, stretched by the road's roughness and broken by its ripples.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5300)
W, H = 1380, 900
a = Art(W, H, "NIGHT RUN")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

HOR  = H * 0.44                       # the road's vanishing line
ROAD = H * 0.52                       # where the wet surface starts being readable
CARX, CARY = W * 0.40, H * 0.60       # the car, three-quarter on, coming toward us
CARW = W * 0.26

NIGHT   = (10, 14, 26)
SKYGLOW = (52, 58, 88)
HEAD    = (255, 246, 214)             # headlights: near white
TAIL    = (255, 58, 40)
SODIUM  = (255, 172, 84)              # street lights along the road
WET     = (26, 32, 48)

# every light in the scene, as (x, y, radius, colour, strength)
LIGHTS = [
    (CARX - CARW*0.34, CARY - 6, 34, HEAD,   1.00),
    (CARX + CARW*0.34, CARY - 6, 34, HEAD,   1.00),
    (CARX - CARW*0.30, CARY + 26, 12, HEAD,  0.30),
    (CARX + CARW*0.30, CARY + 26, 12, HEAD,  0.30),
]
for i in range(7):                     # street lights receding up the road
    t = i / 6.0
    y = HOR + 8 + (H - HOR) * (t ** 2.1) * 0.55
    x = W * (0.72 - 0.26 * (1 - t) ** 1.4) + 120 * t
    LIGHTS.append((x, y - 130 * (1 - t) - 20, 16 + 30 * t, SODIUM, 0.50 + 0.5 * t))
LIGHTS.append((W * 0.80, HOR + 30, 22, TAIL, 0.45))   # a tail light far up the road

def lit_at(x, y):
    """how much light reaches this point, and what colour. No ambient: this is all there is."""
    tot = 0.0; r = 0.0; g = 0.0; b = 0.0
    for (lx, ly, rad, c, s) in LIGHTS:
        d = math.hypot(x - lx, (y - ly) * 1.35)
        v = s * (rad * rad) / (d * d + rad * rad * 0.9)
        if v < 0.004: continue
        tot += v; r += c[0] * v; g += c[1] * v; b += c[2] * v
    if tot <= 0: return 0.0, NIGHT
    return tot, (min(255, r / tot), min(255, g / tot), min(255, b / tot))

def road_ripple(x, y):
    """the surface the reflections are broken by: long low swells plus fine chop"""
    return (G5.fbm(x * 0.004, y * 0.02, 3) - 0.5) * 2.2 + (G5.vnoise(x * 0.05, y * 0.12) - 0.5) * 0.7

def build():
    # ---- the night. Not black: a city's sky glow, dimmest overhead.
    for y in range(TOPBAR, int(HOR) + 4, 2):
        t = G.frac(y, TOPBAR, HOR)
        R(0, y, W, 3, col(0.035 + 0.075 * t ** 1.6, mix(NIGHT, SKYGLOW, t ** 1.3), 0.5))

    # ---- the wet road. Value comes ONLY from what light reaches it.
    for y in range(int(HOR), H, 2):
        d = G.frac(y, HOR, H)
        NC = 150
        for k in range(NC):
            x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
            amt, c = lit_at(xm, y)
            v = 0.02 + 0.30 * min(1.0, amt) ** 0.55
            R(x0, y, W / NC + 2, 3, col(v, mix(WET, c, min(0.85, amt * 0.8)), 0.62))

    # ---- THE REFLECTIONS. A wet road mirrors every source downward, and the road's ripples
    # break each reflection into a stretched, interrupted column. This is the whole subject.
    for (lx, ly, rad, c, s) in LIGHTS:
        if ly > H: continue
        reach = (H - ly) * (0.60 + 0.85 * s)
        n = int(3200 * s + 900)
        for _ in range(n):
            p = random.random() ** 0.55
            y = ly + 16 + reach * p
            if y > H: continue
            # A wet-road reflection is a NEARLY VERTICAL streak. v1 let it fan out by 2.6x the
            # source radius and the result read as a smoke plume. It widens only slightly, and
            # what breaks it is the ripple running ACROSS the road, which chops it into
            # horizontal bands rather than smearing it sideways.
            spread = rad * (0.22 + 0.55 * p)
            band = G5.fbm(lx * 0.002, y * 0.045, 3)
            if band < 0.42: continue                  # the horizontal breaks
            x = lx + (band - 0.5) * spread * 1.1 + random.gauss(0, spread * 0.42)
            fall = (1 - p) ** 1.35
            D(x, y, random.uniform(1.2, 3.4) * (0.7 + 0.9 * p),
              col(min(0.97, 0.26 + 0.68 * fall * s), c, 0.55),
              min(0.60, (0.06 + 0.52 * fall) * s))

    # ---- the sources themselves: a small blown core and a wide bloom in the wet air
    for (lx, ly, rad, c, s) in LIGHTS:
        for k in range(70):
            u = k / 70.0
            D(lx, ly, rad * 4.6 * (1 - u) ** 1.7 + 2,
              col(0.55 + 0.44 * u * u, c, 0.5), 0.030 * s * (u ** 2.1))
        D(lx, ly, rad * 0.30, col(0.99, mix(c, (255,255,255), 0.5), 0.3), 1.0)

    # ---- THE CAR. Never an outline: it is the shape that BLOCKS the glow behind it, plus the
    # few places its own lights graze its own bodywork.
    body = [(-0.50, 0.10), (-0.46, -0.10), (-0.34, -0.20), (-0.16, -0.30), (0.16, -0.30),
            (0.34, -0.20), (0.46, -0.10), (0.50, 0.10), (0.44, 0.22), (-0.44, 0.22)]
    ys_top = {}
    for i in range(len(body)):
        x1, y1 = body[i]; x2, y2 = body[(i + 1) % len(body)]
        steps = 90
        for k in range(steps):
            t = k / steps
            px = CARX + CARW * (x1 + (x2 - x1) * t)
            py = CARY + CARW * 0.62 * (y1 + (y2 - y1) * t)
            key = int(px)
            lo, hi = ys_top.get(key, (1e9, -1e9))
            ys_top[key] = (min(lo, py), max(hi, py))
    for px, (lo, hi) in ys_top.items():
        y = lo
        while y <= hi:
            u = G.frac(y, lo, hi)
            # the body is dark; only the top surfaces catch the sky glow and the flanks catch
            # a little of the car's own light bouncing off the road
            sky = (1 - u) ** 2.2 * 0.22
            amt, c = lit_at(px, y + 40)
            bounce = min(0.30, amt * 0.16) * u
            v = 0.055 + sky * 1.5 + bounce * 1.8
            R(px, y, 2, 3, col(v, mix(NIGHT, mix(SKYGLOW, c, 0.5), min(0.8, sky*3 + bounce*2)), 0.5))
            y += 2
    # windscreen: a darker void that still catches one streak of sky
    for _ in range(1400):
        wx = CARX + random.uniform(-CARW*0.30, CARW*0.30)
        wy = CARY + CARW*0.62*random.uniform(-0.29, -0.14)
        D(wx, wy, random.uniform(1.5, 5.0), col(0.045 + 0.10*random.random(), SKYGLOW, 0.4), 0.30)

    # ---- rain in the air, visible only where a light reaches it
    for _ in range(3400):
        x = random.uniform(0, W); y = random.uniform(TOPBAR, H)
        amt, c = lit_at(x, y)
        if amt < 0.16: continue
        ln = random.uniform(6, 26)
        L(x, y, x + random.gauss(0, 2.2), y + ln, random.uniform(0.4, 0.9),
          col(min(0.80, 0.22 + 0.45 * min(1.0, amt)), c, 0.45))

build()
OUT = "g5_night_run_gray.png" if GRAY else "g5_night_run.png"
asyncio.run(G5.paint(a, OUT, {"subject": "night_run",
    "prompt": "A car on a wet road at night, its lights broken and stretched in the reflections."},
    gray=GRAY, focal_y=H*0.62))
