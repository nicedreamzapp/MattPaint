"""GEN 5 — DAWN RIDGES.

PROMPT: "Layered mountain ridges at dawn, receding into haze, with the sun low behind them."

Read as light: the sun is low, behind the farthest ridge, so it is a bright disc sitting in a
valley of the horizon. Everything in front of it is in silhouette, but not black — each ridge
catches a warm rim of light on the side facing the sun, and the valleys between ridges fill
with cool, hazy skylight. Distance is carried by atmospheric perspective: the far ridges are
pale, warm, and low-contrast; the near ridges are dark, cool, and sharp. The whole frame is a
stack of value bands, each one a little lighter and warmer than the one in front of it,
dissolving into the glow at the top.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = False
A.GEN = "LOCAL · QWEN 3.8 · ROUND 1"
random.seed(71)
W, H = 1380, 900
a = Art(W, H, "DAWN RIDGES")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

# ---- palette: value plan first, hue as tint ----
# sky: deep indigo at top -> warm peach at horizon
SKY_TOP = (14, 18, 42)
SKY_MID = (58, 48, 88)
SKY_LOW = (168, 108, 92)
SKY_GLOW = (244, 196, 138)
SUN_CORE = (255, 244, 214)
SUN_HALO = (252, 210, 150)

# ridge value ramp: near (dark, cool) -> far (pale, warm)
# each ridge: (value, hue, sat)
RIDGE_DEFS = [
    (0.10, (30, 34, 58), 0.30),   # nearest: dark indigo
    (0.18, (44, 42, 66), 0.30),
    (0.28, (66, 54, 74), 0.32),
    (0.40, (96, 72, 82), 0.34),
    (0.52, (132, 96, 92), 0.36),
    (0.64, (172, 128, 104), 0.38),
    (0.74, (206, 162, 122), 0.40),
    (0.82, (232, 196, 152), 0.42),
]

SUN_X = W * 0.52
SUN_Y = H * 0.50
SUN_R = 34

def ridge_top(i, x):
    """Organised ridge: a low-frequency fbm gives the overall shape, a higher-frequency
    ridged noise gives the jagged peaks. Each ridge is offset and scaled so they nest."""
    base = H * (0.42 + 0.085 * i)
    amp = H * (0.10 - 0.008 * i)
    f1 = G5.fbm(x * 0.0016 + i * 3.7, 0.5, 4)
    f2 = G5.ridged(x * 0.0042 + i * 7.3, 0.5, 3, 2.2)
    f3 = G5.fbm(x * 0.012 + i * 11.1, 0.5, 3)
    y = base + (f1 - 0.5) * amp * 1.6 + (f2 - 0.5) * amp * 0.9 + (f3 - 0.5) * amp * 0.35
    return y

def sky_col(x, y):
    """Sky gradient with a radial glow around the sun."""
    t = G.frac(y, TOPBAR, H * 0.62)
    c = mix(SKY_TOP, SKY_MID, G5.env(t, 1.0))
    c = mix(c, SKY_LOW, G.frac(y, H * 0.35, H * 0.62))
    # radial glow
    dx = (x - SUN_X) / (W * 0.55)
    dy = (y - SUN_Y) / (H * 0.45)
    d = math.sqrt(dx * dx + dy * dy)
    glow = math.exp(-d * d * 3.2)
    c = mix(c, SKY_GLOW, min(0.95, glow * 1.1))
    return c

def build():
    # ---- sky: paint in horizontal bands, 2px step ----
    for y in range(TOPBAR, H, 2):
        NC = 110
        for k in range(NC):
            x0 = W * k / NC
            xm = x0 + W / (2.0 * NC)
            c = sky_col(xm, y)
            # value from the colour
            v = (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0
            R(x0, y, W / NC + 2, 3, col(v, c, 0.55))

    # ---- sun disc and halo: dabs only (the only op with alpha) ----
    # halo: many tiny dabs over the bright field
    for _ in range(9000):
        ang = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, W * 0.30)
        x = SUN_X + math.cos(ang) * r
        y = SUN_Y + math.sin(ang) * r * 0.7
        if y < TOPBAR or y > H: continue
        fall = math.exp(-(r / (W * 0.18)) ** 2)
        if fall < 0.02: continue
        D(x, y, random.uniform(2, 7), col(0.92, SUN_HALO, 0.5), fall * 0.18)
    # core: dense dabs
    for _ in range(4000):
        ang = random.uniform(0, 2 * math.pi)
        r = random.uniform(0, SUN_R * 1.6)
        x = SUN_X + math.cos(ang) * r
        y = SUN_Y + math.sin(ang) * r * 0.85
        if y < TOPBAR: continue
        fall = math.exp(-(r / SUN_R) ** 2)
        if fall < 0.05: continue
        D(x, y, random.uniform(1.5, 4), col(0.98, SUN_CORE, 0.3), fall * 0.55)

    # ---- ridges: far to near, each a filled column from its top to the bottom ----
    for i in range(len(RIDGE_DEFS) - 1, -1, -1):
        val, hue, sat = RIDGE_DEFS[i]
        # atmospheric perspective: far ridges blend toward the sky glow
        depth = G.frac(i, 0, len(RIDGE_DEFS) - 1)
        haze = G.atmos(col(val, hue, sat), depth, col(0.85, SKY_GLOW, 0.4), 0.55)
        # fill columns: step_x sharp for near, soft for far
        step_x = 2.0 + depth * 3.0
        step_y = 3
        def colf(x, y, yt, _i=i, _val=val, _hue=hue, _sat=sat, _depth=depth):
            # light model: rim light on the sun-facing side, cool fill in shadow
            dx = (x - SUN_X) / W
            # rim: brighter near the sun's x, fading with distance
            rim = math.exp(-(dx * dx) * 8.0) * (1.0 - _depth * 0.3)
            # vertical: top of ridge catches more light
            vt = G.frac(y, yt, H)
            top_light = (1.0 - vt) * 0.3
            # noise for variation
            n = G5.fbm(x * 0.008 + _i * 5.1, y * 0.006, 3)
            v = _val + rim * 0.18 + top_light * 0.12 + (n - 0.5) * 0.06
            v = max(0.02, min(0.95, v))
            # colour: warm on lit side, cool in shadow
            warm = mix(_hue, SKY_GLOW, rim * 0.5 + top_light * 0.3)
            cool = mix(_hue, SKY_TOP, (1.0 - rim) * 0.3)
            c = mix(cool, warm, rim * 0.6 + top_light * 0.2)
            # atmospheric haze
            c = G.atmos(c, _depth, col(0.85, SKY_GLOW, 0.4), 0.5)
            return col(v, c, _sat)
        G5.fill_columns(a, 0, W, lambda x: ridge_top(i, x), H, colf,
                        step_y=step_y, step_x=step_x)

    # ---- fine texture: tiny dabs on the nearest ridge for grain ----
    for _ in range(12000):
        x = random.uniform(0, W)
        yt = ridge_top(0, x)
        y = yt + random.random() ** 1.5 * (H - yt) * 0.4
        if y > H: continue
        n = G5.fbm(x * 0.02, y * 0.02, 3)
        v = 0.08 + n * 0.08
        D(x, y, random.uniform(1, 3), col(v, (28, 30, 52), 0.3), 0.25)

    # ---- defects: a few faint birds in the sky ----
    for _ in range(5):
        bx = random.uniform(W * 0.2, W * 0.8)
        by = random.uniform(TOPBAR + 40, H * 0.35)
        s = random.uniform(3, 6)
        L(bx - s, by, bx, by + s * 0.4, 1.2, col(0.15, (20, 22, 40), 0.3), )
        L(bx, by + s * 0.4, bx + s, by, 1.2, col(0.15, (20, 22, 40), 0.3))

build()
OUT = "g5_dawn_ridges.png"
asyncio.run(G5.paint(a, OUT, {"subject": "dawn_ridges", "prompt": "Layered mountain ridges at dawn, receding into haze, with the sun low behind them.", "painter": "local-qwen3.8"},
    gray=GRAY, focal_y=H*0.6))
