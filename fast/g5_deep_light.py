"""GEN 5 — DEEP LIGHT. Built to GEN5_RULES.md from the start.

PROMPT: "A fish underwater, light falling from the surface above, caustics moving across its body."

The prompt names three things and only one of them is an object. Light falling from above and
caustics moving are both LIGHT, so this is a light painting with a fish in it, not a fish
painting with light on it. Built that way.

 - No outline anywhere. The fish is defined by where light stops.
 - Flat-gray test first (`gray`). If the water column and the fish do not read without colour,
   colour will not save them.
 - Water is the most extreme atmospheric perspective there is: everything loses contrast,
   saturation and sharpness with distance, fast, and it all shifts toward the water's own hue.
 - Caustics are LIGHT, not texture. They are cast by the wave surface above, so they fall on
   whatever faces upward, they are brightest near the surface, and they bend over the fish's
   body rather than lying flat on it.
 - Colour temperature: the shaft light is warm from above, everything out of it goes cold blue.
 - Every wash is dabs, never rects — a rect here is opaque.

FISH PROPORTIONS ARE TUNED BY EYE, NOT SOURCED. The prompt names no species and there is no
single correct fish, so these are a shape choice, not a claim about the world. Labelled per the
two-zone rule in CONSTRUCTION.md so nobody hunts for a citation that cannot exist.

usage: python3 g5_deep_light.py [gray]
"""
import asyncio, math, random, sys, time, urllib.request
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5100)
W, H = 1380, 900
a = Art(W, H, "DEEP LIGHT")
R, L, D = a.R, a.L, a.D

SURF = TOPBAR + 40                    # the water surface, just inside the top of the frame
SUNX = W * 0.36                       # the sun is up and to the left, outside the frame
TO_SUN = (-0.30, -0.954)              # light comes from ABOVE, leaning slightly left

# colour: warm where the shaft light reaches, cold everywhere else
LIGHT_C  = (255, 244, 206)
SHAL_C   = (86, 170, 186)             # water near the surface
DEEP_C   = (6, 26, 54)                # the dark below
FISH_C   = (168, 176, 186)            # a silver fish, so it can only be lit, never coloured
FISH_D   = (30, 48, 70)

def col(v, hue, sat=0.62):
    return G.gray(v) if GRAY else G.tint(v, hue, sat)

def _h2(i, j):
    h = (i * 374761393 + j * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def vnoise(x, y):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    sx = fx*fx*(3-2*fx); sy = fy*fy*(3-2*fy)
    a0=_h2(i,j); b0=_h2(i+1,j); c0=_h2(i,j+1); d0=_h2(i+1,j+1)
    t=a0+(b0-a0)*sx; b=c0+(d0-c0)*sx
    return t+(b-t)*sy

def depth_of(y):
    """0 at the surface, 1 at the bottom of the frame"""
    return G.frac(y, SURF, H)

def water_value(x, y):
    """the water column itself: bright at the surface, falling away fast with depth, plus the
    broad shaft of light coming down from the sun"""
    d = depth_of(y)
    v = 0.66 * math.exp(-d * 2.1) + 0.045
    # the shaft: a wedge widening as it descends, brightest near the surface
    sx = SUNX + (y - SURF) * -TO_SUN[0] / -TO_SUN[1] * 1.0
    half = 90 + (y - SURF) * 0.52
    across = abs(x - sx) / half
    if across < 1.6:
        v += 0.40 * math.exp(-across * across * 1.5) * math.exp(-d * 1.5)
    return min(0.98, v)

def water_hue(x, y):
    d = depth_of(y)
    base = mix(SHAL_C, DEEP_C, d ** 0.62)
    sx = SUNX + (y - SURF) * -TO_SUN[0] / -TO_SUN[1]
    half = 90 + (y - SURF) * 0.52
    warm = math.exp(-((x - sx) / half) ** 2 * 1.4) * math.exp(-d * 1.6)
    return mix(base, LIGHT_C, min(0.72, warm))


# ---------------------------------------------------------------- the fish, as a lit form
# TUNED BY EYE. No species named, no correct answer to look up. Measured in body lengths (BL).
BL   = 520.0
FX   = W * 0.26          # snout
FY   = H * 0.56          # the body axis at the snout
TILT = -0.16             # gently nose-up, swimming across the shaft

def axis(t):
    """the fish's spine: a gentle curve, nose at t=0, tail root at t=1"""
    x = FX + BL * t * math.cos(TILT)
    y = FY + BL * t * math.sin(TILT) + math.sin(t * 2.6) * BL * 0.030
    return x, y

def girth(t):
    """half-depth of the body at t — deepest just behind the head, tapering to the tail root"""
    if t < 0: return 0.0
    return BL * (0.155 * math.sin(min(1.0, t * 1.12) * math.pi) ** 0.62) * (1.0 - t * 0.42)

def body_span(x):
    """top and bottom of the fish at this x, or None"""
    best = None
    for i in range(121):
        t = i / 120.0
        ax, ay = axis(t)
        if abs(ax - x) < 4.0:
            g = girth(t)
            if g > 0:
                lo, hi = ay - g, ay + g
                best = (lo, hi) if best is None else (min(best[0], lo), max(best[1], hi))
    return best

def caustic(x, y, t_phase=0.0):
    """Caustics are the wave surface FOCUSING sunlight. They are a network of bright filaments,
    they are strongest near the surface and wash out with depth, and they lie ON whatever
    surface receives them. Built from two crossing noise fields ridged into filaments — which
    is what a caustic network actually is, not random speckle."""
    d = depth_of(y)
    s = 0.0060
    n1 = vnoise(x * s + t_phase, y * s * 0.55)
    n2 = vnoise(x * s * 1.7 + 40 - t_phase, y * s * 0.9 + 17)
    ridged = (1.0 - abs(n1 * 2 - 1)) ** 5.5 + (1.0 - abs(n2 * 2 - 1)) ** 7.0 * 0.7
    return ridged * math.exp(-d * 2.3)

def build():
    # ---- the water column. Many TINY dabs near the surface where it is bright, and the
    # gradient itself in rects because a rect here is opaque and that is exactly what a solid
    # background wants to be.
    for y in range(TOPBAR, H, 2):
        NC = 140
        for k in range(NC):
            x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
            R(x0, y, W / NC + 2, 3, col(water_value(xm, y), water_hue(xm, y), 0.70))

    # ---- the surface above, seen from below: a bright shifting ceiling
    for _ in range(9000):
        x = random.uniform(0, W)
        y = SURF + random.random() ** 2.4 * 70
        w = 0.5 + 0.5 * math.sin(x * 0.03 + math.sin(x * 0.011) * 2.0)
        D(x, y, random.uniform(2.0, 9.0),
          col(0.72 + 0.26 * w, mix(LIGHT_C, SHAL_C, 0.35), 0.55),
          0.035 * (1.0 - G.frac(y, SURF, SURF + 70)))

    # ---- the shaft of light, as VOLUME in the water between camera and fish
    for _ in range(14000):
        y = SURF + random.random() ** 0.85 * (H - SURF)
        sx = SUNX + (y - SURF) * -TO_SUN[0] / -TO_SUN[1]
        half = 90 + (y - SURF) * 0.52
        x = sx + random.gauss(0, half * 0.55)
        d = depth_of(y)
        D(x, y, random.uniform(3, 14),
          col(0.80, mix(LIGHT_C, SHAL_C, 0.25), 0.5),
          0.030 * math.exp(-d * 1.9) * math.exp(-((x - sx) / half) ** 2))

    # ---- suspended particles, drifting, lit only inside the shaft
    for _ in range(2600):
        x = random.uniform(0, W); y = random.uniform(SURF, H)
        sx = SUNX + (y - SURF) * -TO_SUN[0] / -TO_SUN[1]
        half = 90 + (y - SURF) * 0.52
        lit = math.exp(-((x - sx) / half) ** 2 * 1.2) * math.exp(-depth_of(y) * 1.7)
        if lit < 0.04: continue
        D(x, y, random.uniform(0.7, 2.2),
          col(0.55 + 0.42 * lit, LIGHT_C, 0.4), min(0.7, 0.10 + 0.6 * lit))

    # ---- THE FISH. Drawn as a lit form, never as a shape with an edge.
    # A fish is a cylinder flattened side-on: the surface normal swings from facing up along
    # the back, through facing the viewer at the lateral line, to facing down at the belly.
    # Light comes from above, so the back is lit, the belly is dark, and the silver flank
    # catches a band of reflected surface light. That gradient IS the fish.
    xs = [axis(i / 120.0)[0] for i in range(121)]
    x0, x1 = min(xs) - 10, max(xs) + 10
    x = x0
    while x < x1:
        sp = body_span(x)
        if sp:
            lo, hi = sp
            along = G.frac(x, x0, x1)
            y = lo
            while y <= hi:
                # n runs -1 (back) .. +1 (belly)
                n = max(-1.0, min(1.0, (y - (lo + hi) * 0.5) / max(1.0, (hi - lo) * 0.5)))
                nz = math.sqrt(max(0.0, 1 - n * n))          # facing the viewer
                direct = max(0.0, (-n) * -TO_SUN[1] * 0.92 + nz * 0.22)
                d = depth_of(y)
                # the silver flank mirrors the bright water above it in a narrow band
                mirror = math.exp(-((n + 0.12) ** 2) / 0.035) * 0.55
                # caustics land on the upward-facing part of the body and bend over it
                cau = caustic(x, y + n * 26) * max(0.0, -n + 0.35) * 1.5
                v = 0.10 + 0.52 * direct + mirror * 0.45 + cau * 0.55
                v *= (1.0 - 0.30 * max(0.0, n))              # the belly sits in its own shadow
                warm = min(1.0, direct * 0.9 + cau * 1.1)
                hue = mix(mix(FISH_D, FISH_C, 0.30 + 0.7 * direct), LIGHT_C, warm * 0.55)
                # everything is still seen THROUGH water: it loses contrast with depth
                v = v * (1.0 - 0.34 * d) + water_value(x, y) * 0.34 * d
                hue = mix(hue, water_hue(x, y), 0.30 * d + 0.12)
                R(x, y, 3, 4, col(max(0.02, min(0.98, v)), hue, 0.58))
                y += 3
        x += 2.0

    # fins: membranes swept between a leading and trailing edge, translucent toward the tip
    def fin(t0, t1, reach, sign, n=90, alpha=0.5):
        ax0, ay0 = axis(t0); ax1, ay1 = axis(t1)
        for i in range(n):
            u = i / (n - 1.0)
            bx = ax0 + (ax1 - ax0) * u; by = ay0 + (ay1 - ay0) * u
            env = math.sin(u * math.pi) ** 0.8
            g = girth(t0 + (t1 - t0) * u)
            steps = max(4, int(reach * env / 4))
            for k in range(steps):
                p = k / max(1.0, steps - 1)
                px = bx + reach * env * p * 0.30
                py = by + sign * (g + reach * env * p)
                d = depth_of(py)
                v = 0.24 + 0.34 * (1 - p) + caustic(px, py) * 0.30
                v = v * (1.0 - 0.34 * d) + water_value(px, py) * 0.34 * d
                D(px, py, max(0.7, 2.4 * (1 - p * 0.5)),
                  col(v, mix(FISH_C, water_hue(px, py), 0.45 + 0.4 * p), 0.5),
                  alpha * (1 - p * 0.75))
    fin(0.12, 0.44, BL * 0.14, -1, alpha=0.55)     # dorsal
    fin(0.22, 0.50, BL * 0.10, +1, alpha=0.40)     # ventral
    fin(0.16, 0.30, BL * 0.11, +1, alpha=0.45)     # pectoral

    # tail: rays sweeping from the peduncle, jittered so they never form concentric arcs.
    # v1 nested two regular loops and the result moired into rings.
    tx, ty = axis(1.0)
    for k in (-1, 1):
        for i in range(150):
            frac = i / 149.0
            spread = (0.10 + 0.95 * frac) * k
            reach = BL * 0.30 * (0.55 + 0.45 * math.sin(min(1.0, frac * 1.1) * math.pi) ** 0.6)
            reach *= random.uniform(0.92, 1.08)
            steps = int(reach / 3)
            for j in range(steps):
                p = j / max(1.0, steps - 1)
                px = tx + reach * p * 0.92 + random.gauss(0, 0.6)
                py = ty + spread * reach * p * 0.78 + random.gauss(0, 0.6)
                d = depth_of(py)
                v = 0.20 + 0.30 * (1 - frac * 0.5) + caustic(px, py) * 0.25
                v = v * (1.0 - 0.34 * d) + water_value(px, py) * 0.34 * d
                D(px, py, max(0.6, 2.2 * (1 - p * 0.3)),
                  col(v, mix(FISH_C, water_hue(px, py), 0.40 + 0.3 * p), 0.5),
                  0.42 * (1 - p * 0.55))

    # the eye: the one hard dark in the whole picture, which is what makes a fish read
    ex, ey = axis(0.055)
    D(ex, ey - girth(0.055) * 0.30, BL * 0.019, col(0.06, FISH_D, 0.5), 1.0)
    D(ex - BL * 0.004, ey - girth(0.055) * 0.34, BL * 0.006, col(0.92, LIGHT_C, 0.4), 0.9)

    # ---- caustics ON the water itself, in front of and behind the fish
    for _ in range(26000):
        x = random.uniform(0, W); y = random.uniform(SURF, H)
        c = caustic(x, y)
        if c < 0.22: continue
        D(x, y, random.uniform(1.4, 5.0),
          col(min(0.96, 0.62 + 0.36 * c), LIGHT_C, 0.45), min(0.18, 0.05 + 0.14 * c))


build()
OUT = "g5_deep_light_gray.png" if GRAY else "g5_deep_light.png"

async def run():
    n = stamp(a)
    print(f"DEEP LIGHT gen5{' [FLAT GRAY]' if GRAY else ''}: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    tab.run_meta = {"generation": 5, "subject": "deep_light",
                    "stage": "gray" if GRAY else "paint",
                    "prompt": "A fish underwater, light falling from the surface above, "
                              "caustics moving across its body."}
    t0 = time.time()
    for i in range(0, len(a.ops), 1800):
        tab.fast(a.ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.04)
    await tab.sync()
    print(f"painted in {time.time()-t0:.2f}s", flush=True)
    await tab.png(OUT)
    if not GRAY:
        import defects as DF
        ops = DF.defect_pass(OUT, W, H, top_guard=TOPBAR + 2, focal_y=H * 0.56, seed=5101,
                             do=("vignette", "fringe", "noise"))[:int(n * 0.02)]
        print(f"defects: {len(ops):,} ({100.0*len(ops)/n:.1f}%)", flush=True)
        for i in range(0, len(ops), 1800):
            tab.fast(ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.03)
        await tab.sync(); await tab.png(OUT)
    await br.close()

asyncio.run(run())
