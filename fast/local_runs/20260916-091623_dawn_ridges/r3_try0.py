"""GEN 5 — DAWN RIDGES.

PROMPT: "Layered mountain ridges at dawn, receding into haze, with the sun low behind them."

Read as light: the sun is LOW and BEHIND the ridges, so the ridges are backlit. The sky is
brightest near the horizon behind the peaks and falls off upward. Each ridge is a dark mass
against the brighter sky behind it; the nearest ridge is darkest and the farthest is nearly
lost in the haze. The sun's glow is a warm pool low in the sky, and the haze is warm near the
sun and cool in the upper sky. Distance loses information: far ridges are lighter, less
saturated, and their texture is smoothed out.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = False
A.GEN = "LOCAL · QWEN 3.8 · ROUND 3"
random.seed(42)
W, H = 1380, 900
a = Art(W, H, "DAWN RIDGES")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

# --- Palette: value plan first, then hue as tint ---
# Sky: warm near horizon, cool at top
SKY_TOP = (38, 52, 88)       # cool blue-gray, value ~0.20
SKY_MID = (120, 100, 110)    # mauve, value ~0.45
SKY_LOW = (210, 160, 120)    # warm peach, value ~0.75
SKY_GLOW = (255, 210, 150)   # sun glow, value ~0.90

# Ridge colours: dark masses, warm-lit edges
RIDGE_DARK = (28, 24, 38)    # nearest, value ~0.10
RIDGE_MID  = (52, 48, 62)    # mid, value ~0.20
RIDGE_FAR  = (90, 82, 98)    # far, value ~0.35
RIDGE_HAZE = (140, 128, 140) # farthest, value ~0.50

# Sun position: low, slightly left of center
SUN_X = W * 0.38
SUN_Y = H * 0.52
SUN_R = W * 0.18

def sky_col(x, y):
    """Sky colour: warm near horizon and near sun, cool at top."""
    t = G.frac(y, TOPBAR, H * 0.65)
    base = mix(SKY_TOP, SKY_MID, t)
    t2 = G.frac(y, H * 0.45, H * 0.65)
    base = mix(base, SKY_LOW, t2 * 0.8)
    # Sun glow
    dx = x - SUN_X
    dy = y - SUN_Y
    dist = math.sqrt(dx * dx + dy * dy)
    glow = math.exp(-(dist / SUN_R) ** 2 * 1.5)
    base = mix(base, SKY_GLOW, min(0.95, glow * 1.2))
    return base

def ridge_top(i, x):
    """Top edge of ridge i. Each ridge is a noisy mountain silhouette.
    i=0 is nearest (lowest on canvas), i=4 is farthest (highest)."""
    base_y = H * (0.82 - i * 0.10)
    # Use fbm for natural mountain shape
    n = G5.fbm(x * 0.002 + i * 7.3, i * 3.1, 4)
    n2 = G5.fbm(x * 0.008 + i * 13.7, i * 5.9, 3)
    ridge = (n * 0.6 + n2 * 0.4)
    # Sharper peaks: use ridged for the main shape
    r = G5.ridged(x * 0.003 + i * 11.1, i * 2.3, 3, 2.5)
    h = base_y - (r * 0.5 + ridge * 0.5) * H * (0.12 + i * 0.03)
    return h

def ridge_col(i, x, y, yt):
    """Colour for ridge i at (x,y). Backlit: darker overall, warm where sun glow hits."""
    # Base value decreases with distance (farther = lighter due to haze)
    base_val = 0.08 + i * 0.08
    # Sun glow effect on the ridge
    dx = x - SUN_X
    dy = y - SUN_Y
    dist = math.sqrt(dx * dx + dy * dy)
    glow = math.exp(-(dist / (SUN_R * 1.5)) ** 2 * 1.2)
    # Warm tint from sun
    warm = mix(RIDGE_DARK, (180, 120, 80), glow * 0.5)
    # Haze: farther ridges blend toward haze colour
    haze_t = i / 4.0
    c = mix(warm, RIDGE_HAZE, haze_t * 0.6)
    # Value adjustment
    v = base_val + glow * 0.15
    return col(v, c, 0.4 + haze_t * 0.2)

def build():
    # --- Sky: paint in horizontal strips ---
    for y in range(TOPBAR, H, 3):
        NC = 100
        for k in range(NC):
            x0 = W * k / NC
            xm = x0 + W / (2.0 * NC)
            c = sky_col(xm, y)
            R(x0, y, W / NC + 2, 4, c)

    # --- Sun glow: add extra dabs near the sun ---
    for _ in range(3000):
        x = SUN_X + random.gauss(0, SUN_R * 0.6)
        y = SUN_Y + random.gauss(0, SUN_R * 0.4)
        if y < TOPBAR or y > H: continue
        dx = x - SUN_X
        dy = y - SUN_Y
        dist = math.sqrt(dx * dx + dy * dy)
        glow = math.exp(-(dist / SUN_R) ** 2 * 2.0)
        if glow < 0.05: continue
        D(x, y, random.uniform(3, 12), col(0.85 + glow * 0.1, SKY_GLOW, 0.3),
          glow * 0.4)

    # --- Ridges: far to near ---
    for i in range(4, -1, -1):
        # Find the top of this ridge across the canvas
        tops = []
        for x in range(0, W, 4):
            tops.append(ridge_top(i, x))
        min_top = min(tops)
        max_top = max(tops)
        # Fill from top of ridge down to bottom
        for x in range(0, W, 3):
            yt = ridge_top(i, x)
            # Fill down to bottom of canvas
            for y in range(int(yt), H, 3):
                c = ridge_col(i, x, y, yt)
                R(x, y, 4, 4, c)
        # Add subtle texture to the ridge face
        for _ in range(2000):
            x = random.uniform(0, W)
            yt = ridge_top(i, x)
            y = yt + random.random() ** 0.5 * (H - yt)
            if y > H: continue
            # Slight variation
            dx = x - SUN_X
            dy = y - SUN_Y
            dist = math.sqrt(dx * dx + dy * dy)
            glow = math.exp(-(dist / (SUN_R * 1.5)) ** 2 * 1.2)
            v = 0.08 + i * 0.08 + glow * 0.12 + random.uniform(-0.02, 0.02)
            c = col(max(0.02, v), mix(RIDGE_DARK, (160, 110, 70), glow * 0.4), 0.35)
            D(x, y, random.uniform(2, 6), c, 0.3)

    # --- Atmospheric haze between ridges: warm near sun, cool elsewhere ---
    for _ in range(8000):
        x = random.uniform(0, W)
        y = random.uniform(H * 0.35, H * 0.85)
        dx = x - SUN_X
        dy = y - SUN_Y
        dist = math.sqrt(dx * dx + dy * dy)
        glow = math.exp(-(dist / (SUN_R * 2.0)) ** 2 * 1.0)
        # Haze colour: warm near sun, cool blue elsewhere
        haze_c = mix((100, 120, 160), (220, 180, 140), glow)
        alpha = 0.02 + glow * 0.04
        D(x, y, random.uniform(8, 25), col(0.5 + glow * 0.3, haze_c, 0.2), alpha)

    # --- Fine texture on nearest ridge: small dabs for rock detail ---
    for _ in range(15000):
        x = random.uniform(0, W)
        yt = ridge_top(0, x)
        y = yt + random.random() ** 0.6 * (H - yt)
        if y > H: continue
        # Only on the nearest ridge
        dx = x - SUN_X
        dy = y - SUN_Y
        dist = math.sqrt(dx * dx + dy * dy)
        glow = math.exp(-(dist / (SUN_R * 1.5)) ** 2 * 1.2)
        v = 0.06 + glow * 0.10 + random.uniform(-0.015, 0.015)
        c = col(max(0.02, v), mix(RIDGE_DARK, (140, 90, 60), glow * 0.3), 0.3)
        D(x, y, random.uniform(1, 3), c, 0.25)

    # --- Defects: barely visible, ~2% ---
    for _ in range(200):
        x = random.uniform(0, W)
        y = random.uniform(TOPBAR, H)
        D(x, y, random.uniform(1, 3), col(0.05, (20, 18, 25), 0.2), 0.02)

build()
OUT = sys.argv[1]
asyncio.run(G5.paint(a, OUT, {"subject": "dawn_ridges", "prompt": "Layered mountain ridges at dawn, receding into haze, with the sun low behind them.", "painter": "local-qwen3.8"},
    gray=GRAY, focal_y=H*0.6))
