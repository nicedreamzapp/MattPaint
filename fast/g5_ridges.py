"""GEN 5 — DAWN RIDGES. Rebuilt on the gen4 critique (critiques/2026-09-14_gen4_*.txt).

PROMPT: "Layered mountain ridges at dawn, receding into haze, with the sun low behind them."

Both critics converged on one diagnosis of gen4:

    "You deleted the outline pass and then starved the nearest terrain of every other cue that
     used to fake form."

Gen4's nearest range was a black cutout with vertical streaks that read as RAIN. Deleting the
crutch was right; building the thing it propped up is this generation's whole job.

WHAT CHANGED
 1. FACETED TERRAIN. Each mass is broken into large low-frequency PLANES with their own surface
    normals, softly blended. Brightness is N·L per plane. Some planes catch the sun at 20-40%
    value instead of 2%. This replaces gen4's spur field entirely.
 2. THE VERTICAL STREAKS ARE GONE. No shafts on the mountain. If light beams are wanted they
    belong in the AIR between camera and ridge, never as texture on rock.
 3. FULL LIGHTING MODEL, not Lambertian: direct sun + sky fill + bounce off lit ground − ambient
    occlusion. A shadowed face still receives skylight; a crease is dark because it is occluded.
 4. COLOUR TEMPERATURE CARRIES THE LIGHT. Lit planes go warm, shadowed planes go COOL from
    skylight. Gen4 was one brown-grey family with a value ramp, which reads as tinted, not lit.
 5. ASYMMETRIC SILHOUETTE with medium-frequency structure — massif, shoulder, secondary summit,
    saddle. Gen4 removed high-frequency noise correctly and lost the structure with it.
 6. RANGES INTERSECT rather than stacking as clean nested sheets. Gen4's depth hierarchy
    succeeded and then became legible AS hierarchy.
 7. SKY WASH TUNED AGAINST THE BRIGHTEST GROUND. A large faint dab is far more visible over a
    bright sky than over dark rock, so sky variation is drawn as wide stretched rects.
 8. THE SUN IS DIFFUSED, not a clean disc with graphic-object clarity.
 9. NO MORE TEXTURE than gen4. Both critics: the problem is incorrect information, not
    insufficient information.

usage: python3 g5_ridges.py [gray]
"""
import asyncio, math, random, sys, time, urllib.request
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5001)
W, H = 1380, 900
a = Art(W, H, "DAWN RIDGES")
R, L, D = a.R, a.L, a.D

HOR = H * 0.70
SUNX, SUNY = W * 0.615, HOR * 0.36
# TO_SUN is the direction FROM a surface TOWARD the sun: left and slightly up, because the sun
# is low and behind the ranges. A plane is lit when its normal points along this vector.
# v1 had this inverted and every lit face was the one pointing AWAY from the sun, which is why
# the whole near range stayed black no matter how the facets were tuned.
TO_SUN = (-0.93, -0.36)
_n = math.hypot(*TO_SUN); TO_SUN = (TO_SUN[0]/_n, TO_SUN[1]/_n)

# ---- 4. colour temperature does the work, not just value
SUN_COL   = (255, 196, 132)               # low dawn sun: warm
SKY_COL   = (138, 170, 214)               # skylight filling the shadows: COOL
BOUNCE    = (208, 158, 116)               # warm light bouncing off lit ground
SKY_ZEN   = (26, 42, 88)
SKY_MID   = (122, 146, 186)
SKY_WARM  = (255, 178, 108)
SKY_GOLD  = (255, 218, 156)

def col(v, hue, sat=0.62):
    return G.gray(v) if GRAY else G.tint(v, hue, sat)

def _hash2(i, j):
    h = (i * 374761393 + j * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

def vnoise(x, y):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    sx = fx*fx*(3-2*fx); sy = fy*fy*(3-2*fy)
    a0 = _hash2(i, j); b0 = _hash2(i+1, j)
    c0 = _hash2(i, j+1); d0 = _hash2(i+1, j+1)
    top = a0 + (b0-a0)*sx; bot = c0 + (d0-c0)*sx
    return top + (bot-top)*sy


# ---------------------------------------------------------------- 5. asymmetric silhouette
def make_range(seed, base_y, amp, n_mass):
    """Masses are ASYMMETRIC — one flank steeper than the other, which is what real ranges do
    and what gen4's cosine humps did not. Medium-frequency structure (shoulder, secondary
    summit, saddle) is built in as named tiers, not as noise."""
    rnd = random.Random(seed)
    masses = []
    for i in range(n_mass):
        cx = W * (i + rnd.uniform(0.10, 0.90)) / n_mass
        steep_left = rnd.random() < 0.5
        masses.append(dict(cx=cx, amp=rnd.uniform(0.62, 1.0) * amp,
                           wl=rnd.uniform(0.16, 0.42) * W * (0.55 if steep_left else 1.0),
                           wr=rnd.uniform(0.16, 0.42) * W * (1.0 if steep_left else 0.55)))
    # medium-frequency STRUCTURE, deliberately placed, not random noise
    shoulders = [(rnd.uniform(0, W), rnd.uniform(0.16, 0.30) * amp,
                  rnd.uniform(0.07, 0.15) * W) for _ in range(4)]
    seconds   = [(rnd.uniform(0, W), rnd.uniform(0.22, 0.40) * amp,
                  rnd.uniform(0.035, 0.075) * W) for _ in range(3)]
    saddles   = [(rnd.uniform(0, W), rnd.uniform(0.10, 0.24) * amp,
                  rnd.uniform(0.04, 0.09) * W) for _ in range(3)]
    def h(x):
        lift = 0.0
        for m in masses:                               # envelope, never a sum
            d = x - m["cx"]
            w = m["wl"] if d < 0 else m["wr"]
            lift = max(lift, m["amp"] * math.exp(-abs(d / w) ** 1.85))
        for (cx, aa, ww) in shoulders:
            lift += aa * math.exp(-abs((x - cx) / ww) ** 1.6)
        for (cx, aa, ww) in seconds:
            lift += aa * math.exp(-abs((x - cx) / ww) ** 1.35)
        for (cx, aa, ww) in saddles:                   # saddles CUT DOWN into the skyline
            lift -= aa * math.exp(-abs((x - cx) / ww) ** 1.5)
        return max(TOPBAR + 34, min(H + 40, base_y - lift))
    return h

# 6. ranges INTERSECT. Gen4's were clean nested sheets, and the hierarchy became legible as
# hierarchy. Overlapping crest bands let a nearer ridge cut across a farther one.
_R = [
    (11, HOR * 0.62, HOR * 0.13, 3, 0.08),
    (23, HOR * 0.76, HOR * 0.20, 3, 0.26),
    (37, HOR * 0.86, HOR * 0.27, 4, 0.46),
    (51, HOR * 0.99, HOR * 0.33, 3, 0.68),
    (67, HOR * 1.14, HOR * 0.40, 4, 1.00),
]
RANGES = [dict(h=make_range(sd, by, am, nm), depth=dp) for (sd, by, am, nm, dp) in _R]


# ---------------------------------------------------------------- 1. TERRAIN FROM DRAINAGE
# Randomly oriented facets produced shattered glass, not a mountain. A real mountain's planes
# are ORGANISED, and what organises them is water: major ridges divide the mass into basins,
# each ridge descends toward the viewer, and the ground on either side of a ridge tilts AWAY
# from its crest into the valleys beside it. So the faces alternate lit / shadow all along the
# range. That alternation is the thing a photograph of mountains is full of and gen4 had none of.
def drainage(seed, n, base_h):
    """major ridges descending from the skyline, each dividing two basins"""
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x0 = rnd.uniform(-W * 0.08, W * 1.08)
        out.append(dict(x0=x0,
                        lean=rnd.uniform(-0.42, 0.42),      # how it leans coming toward us
                        fan=rnd.uniform(0.020, 0.075),      # how fast the basins widen
                        width=rnd.uniform(46, 150),         # basin half-width at the crest
                        steep=rnd.uniform(0.55, 1.0),       # how hard the flanks tilt
                        run=rnd.uniform(120, 420),          # how far it descends before dying
                        top=base_h(x0)))
    return out

def terrain_normal(x, y, ridges, jitter=0.0):
    """Which ridge's basin is this point in, and which way does the ground tilt here?

    The ground tilts AWAY from the nearest ridge axis, toward the valley. Left of a ridge the
    surface faces left; right of it, right. That single rule produces alternating lit and
    shadow planes with definite breaks along the ridge crests and along the valley floors."""
    best = None; bestd = 1e9
    for r in ridges:
        below = max(0.0, y - r["top"])
        axis = r["x0"] + r["lean"] * below
        half = r["width"] + r["fan"] * below * 6.0
        d = abs(x - axis) / max(12.0, half)
        if d < bestd: bestd = d; best = (r, x - axis, half, below)
    if best is None: return 0.0, -1.0
    r, off, half, below = best
    u = max(-1.6, min(1.6, off / max(12.0, half)))          # -1 valley left, 0 crest, +1 right
    # A spur ENDS. v1 let every ridge run to the bottom of the frame and the range came out as
    # organ pipes. The flank tilt decays as the ridge descends and dies into the valley floor,
    # so the planes close instead of striping downward forever.
    die = math.exp(-(below / r["run"]) ** 1.6)
    tilt = math.sin(u * 1.9) * math.exp(-abs(u) * 0.55) * r["steep"] * die
    nx = tilt
    ny = -math.sqrt(max(0.04, 1.0 - tilt * tilt)) * (0.55 + 0.45 * math.exp(-abs(u)))
    if jitter:
        nx += (vnoise(x * 0.021, y * 0.018) - 0.5) * jitter
        ny += (vnoise(x * 0.024 + 90, y * 0.020 + 40) - 0.5) * jitter * 0.45
    n = math.hypot(nx, ny) or 1.0
    return nx / n, ny / n


# ---------------------------------------------------------------- 3. the real lighting model
def light(nx, ny, x, y, crest_y, depth):
    """direct sun + sky fill + bounce off lit ground − ambient occlusion.

    Gen4 used bare N·L and a shadowed plane simply went black. A face turned away from the sun
    still receives light from the whole bright sky; a crease is dark because it is OCCLUDED,
    which has nothing to do with its normal."""
    direct = max(0.0, nx * TO_SUN[0] + ny * TO_SUN[1])
    sky    = max(0.0, -ny) * 0.5 + 0.5            # how much of the sky dome this plane sees
    down   = G.frac(y, crest_y, H)
    # occlusion: deep in the mass, and in the troughs between planes
    occ = 0.42 * (down ** 1.5) + 0.22 * max(0.0, 0.5 - abs(nx)) * down
    # bounce: lit ground throws warm light back up into shadowed faces low on the mountain
    bounce = max(0.0, 1.0 - direct) * down * 0.30
    return direct, sky, bounce, min(0.78, occ)


def sky_value(x, y):
    t = G.frac(y, TOPBAR, HOR)
    v = 0.22 + 0.55 * (t ** 0.70)
    dx = (x - SUNX) / (W * 0.46); dy = (y - SUNY) / (HOR * 0.46)
    return min(0.985, v + 0.38 * math.exp(-(dx*dx + dy*dy) * 0.80))

def sky_hue(x, y):
    dx = (x - SUNX) / (W * 0.58); dy = (y - SUNY) / (HOR * 0.78)
    near = math.exp(-(dx*dx + dy*dy) * 0.52)
    base = mix(SKY_ZEN, SKY_MID, G.frac(y, TOPBAR, HOR) ** 0.82)
    return mix(base, mix(SKY_WARM, SKY_GOLD, near), min(0.92, near * 1.12))


def build():
    # ---- 7. SKY. Variation drawn as WIDE STRETCHED RECTS, not dabs. A large faint dab is far
    # more visible over a bright sky than over dark rock, and gen4's sky showed its dab radius.
    for y in range(TOPBAR, int(HOR) + 6, 2):
        NC = 52
        for k in range(NC):
            x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
            R(x0, y, W / NC + 2, 3, col(sky_value(xm, y), sky_hue(xm, y), 0.66))
    # sky variation: MANY TINY, because a large faint dab is visible over a bright field and
    # invisible over dark rock. Same wash, opposite regime, chosen by what it sits on.
    for _ in range(26000):
        x = random.uniform(-40, W + 40); y = random.uniform(TOPBAR, HOR + 16)
        D(x, y, random.uniform(2.0, 6.5),
          col(sky_value(x, y) + random.uniform(-0.05, 0.05), sky_hue(x, y), 0.55), 0.030)

    # ---- 8. THE SUN: diffused into the air, no clean disc with graphic-object clarity
    for k in range(190):
        u = k / 190.0
        D(SUNX + random.gauss(0, 3), SUNY + random.gauss(0, 2.4),
          700 * (1 - u) ** 1.75 + 9,
          col(0.70 + 0.29 * u * u, mix(SKY_GOLD, (255, 250, 240), u), 0.74),
          0.0068 * (u ** 2.2))
    for _ in range(1600):
        ang = random.uniform(0, 6.2832); r = random.random() ** 0.40 * 210
        D(SUNX + math.cos(ang) * r * 1.25, SUNY + math.sin(ang) * r * 0.66,
          random.uniform(14, 46), col(0.93, SKY_GOLD, 0.68), 0.016)

    # ---- THE RANGES
    for ri, rg in enumerate(RANGES):
        h = rg["h"]; depth = rg["depth"]
        det = G.detail_for_depth(depth)
        crest_mid = h(W * 0.5)
        ridges = drainage(900 + ri, int(6 + 14 * depth), h)
        jit    = 0.10 + 0.34 * depth
        sat    = 0.18 + 0.56 * depth
        # 2/3. how strongly each light term shows, by distance
        I_sun  = 0.20 + 0.16 * depth        # lit planes reach ~40%, never blow out
        I_sky  = 0.26 - 0.16 * depth
        I_bnc  = 0.05 + 0.13 * depth
        floor  = 0.28 - 0.22 * depth        # backlit: the near range sits DARK
        step_y = 3 + int(4 * (1 - depth))
        x = 0.0
        while x < W:
            cy = h(x)
            y = cy
            while y < H + 6:
                nx, ny = terrain_normal(x, y, ridges, jit)
                direct, sky, bounce, occ = light(nx, ny, x, y, cy, depth)
                v = floor + I_sun * (direct ** 1.15) + I_sky * sky * 0.5 + I_bnc * bounce
                v *= (1.0 - occ * (0.45 + 0.35 * depth))
                # 4. colour temperature: lit runs WARM, shadow runs COOL from skylight
                warmth = min(1.0, direct * 1.25)
                hue = mix(mix(SKY_COL, BOUNCE, bounce * 2.4), SUN_COL, warmth)
                hue = mix(hue, mix(SKY_MID, SKY_WARM, 0.3), (1.0 - depth) * 0.55)
                R(x, y, 3, step_y + 1, col(max(0.02, v), hue, sat))
                y += step_y
            x += 2.0

        # grain ON the planes — albedo, never vertical streaks. 2. no shafts on the mountain.
        if depth > 0.25:
            gr = 0.9 + 3.2 * (1 - depth)
            for _ in range(int(7000 * depth)):
                gx = random.uniform(0, W)
                cy = h(gx)
                gy = cy + random.random() ** 0.55 * (H - cy)
                nx, ny = terrain_normal(gx, gy, ridges, jit)
                direct, sky, bounce, occ = light(nx, ny, gx, gy, cy, depth)
                v = floor + I_sun * (direct ** 1.15) + I_sky * sky * 0.5 + I_bnc * bounce
                v *= (1.0 - occ * 0.6)
                warmth = min(1.0, direct * 1.25)
                hue = mix(SKY_COL, SUN_COL, warmth)
                D(gx, gy, gr * random.uniform(0.55, 1.5),
                  col(max(0.02, v + random.uniform(-0.05, 0.05)), hue, sat), 0.11)

        # the haze that buries the range behind this one
        hz = 0.60 + 0.28 * (1 - depth)
        # haze over the crest sits on BOTH sky and rock, so it uses the tiny regime too
        for _ in range(int(5200 * (1.15 - depth))):
            hx = random.uniform(-120, W + 120); hy = h(hx) + random.uniform(-10, 70)
            D(hx, hy, random.uniform(3.0, 11.0),
              col(hz, mix(sky_hue(hx, max(TOPBAR, hy)), SKY_GOLD, 0.22), 0.36), 0.026)


build()
OUT = "g5_ridges_gray.png" if GRAY else "g5_ridges.png"

async def run():
    n = stamp(a)
    print(f"DAWN RIDGES gen5{' [FLAT GRAY]' if GRAY else ''}: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    tab.run_meta = {"generation": 5, "subject": "dawn_ridges",
                    "stage": "gray" if GRAY else "paint"}
    t0 = time.time()
    for i in range(0, len(a.ops), 1800):
        tab.fast(a.ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.04)
    await tab.sync()
    print(f"painted in {time.time()-t0:.2f}s", flush=True)
    await tab.png(OUT)
    if not GRAY:
        import defects as DF
        ops = DF.defect_pass(OUT, W, H, top_guard=TOPBAR + 2, focal_y=H * 0.80, seed=5002,
                             do=("vignette", "fringe", "noise"))[:int(n * 0.02)]
        print(f"defects: {len(ops):,} ({100.0*len(ops)/n:.1f}%)", flush=True)
        for i in range(0, len(ops), 1800):
            tab.fast(ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.03)
        await tab.sync(); await tab.png(OUT)
    await br.close()

asyncio.run(run())
