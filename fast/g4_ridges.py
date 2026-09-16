"""GEN 4 — DAWN RIDGES. Rebuilt on the outside critique (see critiques/, LOOP.md).

PROMPT: "Layered mountain ridges at dawn, receding into haze, with the sun low behind them."

What changed from gen3, point by point, all three critics agreeing on most of it:

 1. NO EDGE STROKES ANYWHERE. Gen3 spent ~45% of its budget outlining things. A crest is not a
    line — it is where a sun-facing slope gets brighter than a slope facing away. Every ridge
    here emerges from shading. There is no rim pass, no outline pass, no silhouette pass.
 2. TERRAIN IS LIT, NOT FILLED. Each range carries spurs running toward the viewer, so the
    surface has real facing. Value comes from dot(surface normal, sun), not from a gradient.
 3. SILHOUETTE FROM GEOLOGICAL HIERARCHY. 3-6 enormous low-frequency masses first, then massif,
    then peak, then subsidiary ridge. High-frequency noise NEVER touches the outer silhouette.
    Test: it must read as a mountain range in FLAT GRAY (run with `gray`).
 4. DISTANCE LOSES INFORMATION, not just contrast. Sharpness, saturation, texture frequency,
    shadow depth and spur count all fall with depth. Haze alone is not depth.
 5. RANGES OCCLUDE EACH OTHER. Nearer masses bury most of the ones behind them.
 6. THE MEDIUM RECEDES. Dab radius grows and opacity falls with distance, so far terrain is not
    made of the same marks as near terrain.
 7. SKY IS LOW-FREQUENCY. Continuous rect bands, saturated gold near the sun falling to deep
    blue away from it, with only very large faint variation on top. No dab-stippled sky.
 8. THE SUN is a small high-value core plus a wide, very low-contrast bloom — not a hard disc.
 9. DEFECTS ARE ~2%, applied last and barely. Two critics said they are the last 2% of realism
    and gen3 was spending 8.5% on them while missing the first 60%.

Budget target (GPT's allocation): sky 10 / masses 20 / light+shadow 25 / distant terrain 20 /
medium structure 15 / fine texture 8 / defects 2.

usage: python3 g4_ridges.py [gray]
"""
import asyncio, math, random, sys, time, urllib.request, json
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "4TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
SEED = 4001
random.seed(SEED)
W, H = 1380, 900
a = Art(W, H, "DAWN RIDGES")
R, L, D = a.R, a.L, a.D

HOR = H * 0.70
SUNX, SUNY = W * 0.615, HOR * 0.38          # low, behind the ranges
SUN = (-0.62, -0.42)                         # direction light travels FROM, normalised-ish
_n = math.hypot(*SUN); SUN = (SUN[0]/_n, SUN[1]/_n)

# ---------------------------------------------------------------- palette
SKY_ZENITH = (28, 44, 92)
SKY_MID    = (118, 140, 178)
SKY_WARM   = (255, 176, 104)
SKY_GOLD   = (255, 214, 150)
ROCK       = (74, 78, 96)
ROCK_WARM  = (196, 150, 108)

def col(v, hue, sat=0.62):
    """value first, hue only as a tint on it. In gray mode the hue is discarded entirely,
    which is the whole point of the flat-gray test."""
    return G.gray(v) if GRAY else G.tint(v, hue, sat)

# ---------------------------------------------------------------- 3. geological hierarchy
def make_range(seed, base_y, mass_h, n_masses, massif, peak, sub):
    """Skyline built the way geology builds one: a few enormous masses, then massifs on them,
    then peaks, then subsidiary ridges. Each tier is strictly smaller and strictly lower
    frequency than the tier below it. High-frequency noise is NOT permitted here — it belongs
    on the surface, never on the outer silhouette."""
    rnd = random.Random(seed)
    masses = []
    for i in range(n_masses):
        cx = W * (i + rnd.uniform(0.15, 0.85)) / n_masses
        masses.append((cx, rnd.uniform(0.55, 1.0) * mass_h, rnd.uniform(0.34, 0.78) * W))
    # each tier is a SMALL fraction of the mass it sits on, and strictly smaller than the tier
    # above it. v1 scaled every tier to the full mass height; they summed and the skyline left
    # the top of the frame.
    mf = [(rnd.uniform(-0.1, 1.1) * W, rnd.uniform(0.10, 0.19) * mass_h,
           rnd.uniform(0.10, 0.22) * W) for _ in range(massif)]
    pk = [(rnd.uniform(-0.1, 1.1) * W, rnd.uniform(0.045, 0.095) * mass_h,
           rnd.uniform(0.035, 0.085) * W) for _ in range(peak)]
    sb = [(rnd.uniform(-0.1, 1.1) * W, rnd.uniform(0.012, 0.032) * mass_h,
           rnd.uniform(0.012, 0.030) * W) for _ in range(sub)]
    def h(x):
        # The base masses form an ENVELOPE (max), not a sum. v2 summed them, so three masses of
        # full height stacked to three times the height and the range swallowed the frame.
        # Geologically this is also right: the big masses define the silhouette, the smaller
        # tiers ride on top of whichever mass is under them.
        lift = 0.0
        for (cx, amp, wd) in masses:
            lift = max(lift, amp * math.exp(-abs((x - cx) / wd) ** 2.0))
        for group, sharp, scale in ((mf, 1.7, 1.0), (pk, 1.45, 1.0), (sb, 1.25, 1.0)):
            for (cx, amp, wd) in group:
                lift += amp * scale * math.exp(-abs((x - cx) / wd) ** sharp)
        return max(TOPBAR + 30, min(H + 40, base_y - lift))

    return h

# depth 0 = furthest. Explicit crest BANDS so the ranges layer and recede properly: the far
# ones sit high in the frame and small, the near ones sit low and large, and each one buries
# most of the one behind it. v2 let the nearest range tower over everything and hide the rest.
#            valley floor      mass amp     masses massif peak sub
_R = [
    (11, HOR * 0.60, HOR * 0.095, 3, 4,  3,  0, 0.08),
    (23, HOR * 0.72, HOR * 0.135, 3, 5,  5,  0, 0.26),
    (37, HOR * 0.84, HOR * 0.182, 4, 6,  7,  4, 0.46),
    (51, HOR * 0.98, HOR * 0.238, 3, 7,  9,  8, 0.68),
    (67, HOR * 1.15, HOR * 0.318, 3, 6, 11, 14, 1.00),
]
RANGES = [dict(h=make_range(sd, by, mh, nm, mf, pk, sb), depth=dp)
          for (sd, by, mh, nm, mf, pk, sb, dp) in _R]

def sky_value(x, y):
    """low-frequency, continuous: a vertical ramp plus a radial lift around the sun"""
    t = G.frac(y, TOPBAR, HOR)
    v = 0.20 + 0.56 * (t ** 0.72)
    dx = (x - SUNX) / (W * 0.44); dy = (y - SUNY) / (HOR * 0.44)
    return min(0.985, v + 0.40 * math.exp(-(dx*dx + dy*dy) * 0.85))

def sky_hue(x, y):
    """saturated gold close to the sun, falling off to deep blue away from it"""
    dx = (x - SUNX) / (W * 0.55); dy = (y - SUNY) / (HOR * 0.72)
    near = math.exp(-(dx*dx + dy*dy) * 0.55)
    t = G.frac(y, TOPBAR, HOR)
    base = mix(SKY_ZENITH, SKY_MID, t ** 0.85)
    return mix(base, mix(SKY_WARM, SKY_GOLD, near), min(0.92, near * 1.15))


# ---------------------------------------------------------------- 2. terrain that is LIT
def _hash2(i, j):
    h = (i * 374761393 + j * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def _vnoise(x, y):
    """smooth hashed value noise - no periodicity, so no grating"""
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    sx = fx * fx * (3 - 2 * fx); sy = fy * fy * (3 - 2 * fy)
    a = _hash2(i, j);     b = _hash2(i + 1, j)
    c = _hash2(i, j + 1); d = _hash2(i + 1, j + 1)
    return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

def spur_field(seed, n, x0, x1):
    """Spurs are the ridges that run DOWN toward the viewer off a crest. They are what gives a
    mountain a lit face and a shadow face in a side-on view. Without them a range is a filled
    band and the only way to say 'ridge' is to draw a line on it — which is exactly the trap
    gen3 fell into."""
    rnd = random.Random(seed)
    return [(rnd.uniform(x0, x1), rnd.uniform(0.55, 1.0), rnd.uniform(26, 118))
            for _ in range(n)]

def surface_facing(x, y, crest_y, spurs, roughness):
    """Approximate the surface normal's horizontal component at this point.

    Each spur pushes the surface to face away from its own axis, so one side of a spur turns
    toward the sun and the other turns away. Sum the spurs, add a little low-frequency
    roughness, and the result is a terrain that has real facing instead of a flat fill.
    Returns nx in -1..1 (negative = faces left, toward the sun)."""
    nx = 0.0
    below = max(0.0, y - crest_y)
    for (sx, amp, wd) in spurs:
        # the spur fans outward and shortens as it comes toward the viewer; without this its
        # lit side is a vertical stripe running the full height of the range (v1: light shafts)
        fan = 1.0 + below / (wd * 3.2)
        axis = sx + (sx - W * 0.5) * 0.045 * (below / max(1.0, wd))
        d = (x - axis) / (wd * fan)
        if abs(d) > 2.6: continue
        run = math.exp(-((below / (wd * 1.5 + 60.0)) ** 1.25))
        nx += -d * math.exp(-d * d * 0.9) * amp * run * 1.7
    # v1 used sin(x)+sin(y) here and it produced a visible diagonal grating across the whole
    # frame. Any periodic function in a surface normal shows up as stripes. Hashed value noise
    # at two octaves instead, and quieter.
    nx += (_vnoise(x * 0.012, y * 0.009) - 0.5) * 0.30 * roughness
    nx += (_vnoise(x * 0.043, y * 0.037) - 0.5) * 0.14 * roughness
    return max(-1.0, min(1.0, nx))

def shade(nx, depth, ambient):
    """dot(normal, sun) in the horizontal plane, plus ambient sky fill from above.
    This is the ONLY thing that makes a crest visible. No stroke is ever drawn to mark one."""
    facing = -nx                                   # nx<0 faces left = faces the sun
    diff = max(0.0, facing * -SUN[0] + 0.30)
    return ambient + (1.0 - ambient) * (diff ** 1.25)


def build():
    # ---------------- 7. SKY: low frequency and continuous. ~10% of the budget.
    for y in range(TOPBAR, int(HOR) + 4, 2):
        # one flat band per row would banner; step the hue across x in a few wide rects so the
        # gold-to-blue falloff is horizontal as well as vertical, still low frequency.
        # v1 used 10 wide columns and the block edges were visible. Narrow columns, and the
        # gradient stays low-frequency because the underlying functions are smooth.
        NC = 46
        for k in range(NC):
            x0 = W * k / NC
            xm = x0 + W / (2.0 * NC)
            R(x0, y, W / NC + 2, 3, col(sky_value(xm, y), sky_hue(xm, y), 0.66))
    # very large, very faint air variation - never a stippled sky
    for _ in range(2600):
        x = random.uniform(-150, W + 150); y = random.uniform(TOPBAR, HOR + 30)
        D(x, y, random.uniform(90, 260),
          col(sky_value(x, y) + random.uniform(-0.05, 0.05), sky_hue(x, y), 0.55), 0.008)

    # ---------------- 8. THE SUN: small core, wide low-contrast bloom. Not a disc.
    for k in range(150):
        u = k / 150.0
        D(SUNX, SUNY, 620 * (1 - u) ** 1.7 + 5,
          col(0.72 + 0.27 * u * u, mix(SKY_GOLD, (255, 252, 244), u), 0.78),
          0.0075 * (u ** 2.3))
    for _ in range(900):                     # the bloom leaks into the nearby haze
        ang = random.uniform(0, 6.2832); r = random.random() ** 0.45 * 300
        D(SUNX + math.cos(ang) * r, SUNY + math.sin(ang) * r * 0.62,
          random.uniform(16, 54), col(0.90, SKY_GOLD, 0.7), 0.012)
    D(SUNX, SUNY, 9, col(0.99, (255, 253, 248), 0.35), 1.0)

    # ---------------- 2/4/5/6. THE RANGES, far to near. Every value here comes from lighting.
    for ri, rg in enumerate(RANGES):
        h = rg["h"]; depth = rg["depth"]
        det = G.detail_for_depth(depth)
        # 4. distance loses INFORMATION, not merely contrast
        ambient   = 0.72 - 0.56 * depth          # far = almost no shadow at all
        sat       = 0.16 + 0.60 * depth          # far = desaturated
        rough     = 0.25 + 0.75 * depth          # far = smoother surface
        n_spurs   = int(3 + 26 * depth)          # far = fewer resolvable spurs
        v_hi      = 0.66 - 0.40 * depth          # far ranges sit close to the sky value
        v_lo      = 0.52 - 0.46 * depth
        step_x    = 2.0
        step_y    = 3 + int(5 * (1 - depth))     # 6. the MEDIUM itself coarsens with distance
        spurs = spur_field(700 + ri, n_spurs, -W * 0.1, W * 1.1)
        hue = mix(mix(SKY_MID, SKY_WARM, 0.35), ROCK, depth ** 0.7)

        x = 0.0
        while x < W:
            cy = h(x)
            # 5. occlusion: stop at the crest of the range in FRONT of this one
            y = cy
            bottom = H + 6
            while y < bottom:
                nx = surface_facing(x, y, cy, spurs, rough)
                s = shade(nx, depth, ambient)
                # terrain gets darker toward the base (it is turning away and in its own shadow)
                down = G.frac(y, cy, H)
                v = (v_lo + (v_hi - v_lo) * s) * (1.0 - 0.34 * down * depth)
                c = col(v, mix(hue, ROCK_WARM, min(0.55, s * 0.62 * (0.3 + depth))), sat)
                R(x, y, step_x + 1, step_y + 1, c)
                y += step_y
            x += step_x

        # medium structure: gullies, which are shadow, not drawn lines. ~15%
        if depth > 0.2:
            for _ in range(int(150 * depth)):
                gx = random.uniform(0, W); gy = h(gx)
                run = random.uniform(40, 200) * (0.3 + depth)
                slope = (h(min(W - 1, gx + 7)) - h(max(0, gx - 7))) / 14.0
                for k in range(int(run / 4)):
                    p = k / max(1.0, run / 4)
                    px = gx + slope * run * p * 0.5 + random.gauss(0, 2.2)
                    py = gy + run * p
                    if py > H: break
                    D(px, py, (1.6 + 3.4 * (1 - depth)) * random.uniform(0.7, 1.3),
                      col(max(0.03, v_lo * (0.42 + 0.25 * ambient)), hue, sat),
                      0.13 * (0.4 + 0.6 * depth) * (1 - p * 0.5))

        # 6. fine texture, ~8%, and its GRAIN SIZE recedes with depth
        if depth > 0.3:
            gr = 0.9 + 3.6 * (1 - depth)
            for _ in range(int(9000 * depth)):
                gx = random.uniform(0, W); gy = h(gx) + random.random() ** 0.6 * (H - h(gx))
                nx = surface_facing(gx, gy, h(gx), spurs, rough)
                s = shade(nx, depth, ambient)
                v = (v_lo + (v_hi - v_lo) * s) + random.uniform(-0.05, 0.05)
                D(gx, gy, gr * random.uniform(0.6, 1.5),
                  col(max(0.02, v), mix(hue, ROCK_WARM, s * 0.5), sat), 0.10)

        # 4. the haze that BURIES the range behind this one - huge and faint, never stippled
        hz = 0.60 + 0.30 * (1 - depth)
        for _ in range(int(900 * (1.15 - depth))):
            hx = random.uniform(-160, W + 160); hy = h(hx) + random.uniform(-6, 70)
            D(hx, hy, random.uniform(70, 220),
              col(hz, mix(sky_hue(hx, max(TOPBAR, hy)), SKY_GOLD, 0.25), 0.38), 0.010)


build()
OUT = "g4_ridges_gray.png" if GRAY else "g4_ridges.png"

async def run():
    n = stamp(a)
    print(f"DAWN RIDGES gen4{' [FLAT GRAY TEST]' if GRAY else ''}: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up:
        launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    tab.run_meta = {"generation": 4, "subject": "dawn_ridges",
                    "stage": "gray" if GRAY else "paint",
                    "prompt": "Layered mountain ridges at dawn, receding into haze, "
                              "with the sun low behind them."}
    t0 = time.time()
    for i in range(0, len(a.ops), 1800):
        tab.fast(a.ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.04)
    await tab.sync()
    print(f"painted in {time.time()-t0:.2f}s", flush=True)
    await tab.png(OUT)

    if not GRAY:
        # 9. defects, ~2% and barely, applied LAST. Two critics: this is the last 2% of realism.
        import defects as DF
        ops = DF.defect_pass(OUT, W, H, top_guard=TOPBAR + 2, focal_y=H * 0.80, seed=4002,
                             do=("vignette", "fringe", "noise"))
        ops = ops[:int(n * 0.02)]
        print(f"defects: {len(ops):,} strokes ({100.0*len(ops)/n:.1f}%)", flush=True)
        for i in range(0, len(ops), 1800):
            tab.fast(ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.03)
        await tab.sync()
        await tab.png(OUT)
    await br.close()

asyncio.run(run())
