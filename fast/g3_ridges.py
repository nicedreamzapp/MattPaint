"""GEN 3 - DAWN RIDGES.

PROMPT (PROMPTS.md, the only input): "Layered mountain ridges at dawn, receding into haze,
with the sun low behind them."

Written from that sentence. No reference to the gen2 script or the gen2 picture.
Order is CONSTRUCTION.md: perspective -> values -> colour -> edges -> texture -> audit.

Ablation stages, cumulative, same seed, same composition:
  base     the sentence painted with colours chosen directly, uniform scatter, uniform edges
  values   every colour derives from a written value plan instead of being picked
  edges    boundaries get an edge class by depth: far LOST, mid SOFT, near HARD
  texture  recursive self-similar masses instead of even scatter
  audit    read the canvas back, diff against the value plan, repaint where the error is worst

usage: python3 g3_ridges.py <stage>
"""
import asyncio, math, random, sys, json, time, urllib.request
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

STAGE = sys.argv[1] if len(sys.argv) > 1 else "base"
ORDER = ["base", "values", "edges", "texture", "audit"]
assert STAGE in ORDER, f"stage must be one of {ORDER}"
ON = lambda s: ORDER.index(STAGE) >= ORDER.index(s)
A.GEN = f"3RD GEN · {STAGE.upper()}"

SEED = 3001
random.seed(SEED)
W, H = 1380, 900
a = Art(W, H, "DAWN RIDGES")
R, L, D = a.R, a.L, a.D

# ---------------------------------------------------------------- 1. perspective
# "the sun low behind them" - eye level sits just above the nearest ridge line, sun just
# clearing the far ridges. Everything else is placed against these two facts.
HOR = H * 0.70                      # eye level
SUNX, SUNY = W * 0.58, HOR * 0.44   # low, just clear of the farthest crest, off centre

# ---------------------------------------------------------------- 2. the value plan
# Written before any colour exists. Backlit dawn: the sky is the light source, so the sky is
# the lightest thing in frame and every ridge is darker than the one behind it.
def plan(u, v):
    y = v * H
    if y < TOPBAR: return 0.07
    if y < HOR:
        t = (y - TOPBAR) / (HOR - TOPBAR)
        base = 0.26 + 0.56 * (t ** 0.75)
        dx = (u * W - SUNX) / (W * 0.30); dy = (y - SUNY) / (HOR * 0.30)
        return min(0.99, base + 0.36 * math.exp(-(dx * dx + dy * dy) * 0.9))
    t = (y - HOR) / (H - HOR)
    return max(0.05, 0.40 - 0.33 * (t ** 0.6))

# hue directions only - the value always comes from plan()
H_SKY_HI   = (52, 74, 128)      # cold top of the dawn sky
H_SKY_MID  = (150, 150, 180)
H_SKY_WARM = (255, 186, 128)    # the glow around the sun
H_RIDGE    = (96, 108, 150)     # cold blue rock seen against the light
H_RIM      = (255, 214, 156)

def sky_hue(t):
    return mix(H_SKY_HI, H_SKY_MID, min(1.0, t * 1.5)) if t < 0.62 else \
           mix(H_SKY_MID, H_SKY_WARM, (t - 0.62) / 0.38)

def sky_at(y):
    t = max(0.0, min(1.0, (y - TOPBAR) / (HOR - TOPBAR)))
    hue = sky_hue(t)
    if not ON("values"):
        return hue                                   # base stage: the hue IS the colour
    return G.tint(plan(0.5, y / H), hue, sat=0.60)   # value first, hue is only a tint

# ---------------------------------------------------------------- ridge silhouettes
def ridgeline(seed, y_at_mid, amp, roughness):
    """a ridge as a sum of waves - a skyline, not a triangle"""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.283) for _ in range(5)]
    fr = [0.0016, 0.0037, 0.0081, 0.019, 0.041]
    wt = [1.0, 0.52, 0.26, 0.12, 0.05]
    def f(x):
        s = 0.0
        for k in range(5):
            s += math.sin(x * fr[k] * 6.283 + ph[k]) * wt[k] * (roughness ** k)
        return y_at_mid + s * amp
    return f

# depth 0 = furthest, 1 = nearest
# amplitude and roughness both GROW toward the viewer: a far range is a soft low band,
# a near one is a big broken mass. Uniform amplitude everywhere is what made it read as a saw.
LAYERS = [
    (ridgeline(11, HOR * 0.62, 26, 0.55), 0.06),
    (ridgeline(23, HOR * 0.74, 38, 0.68), 0.22),
    (ridgeline(37, HOR * 0.88, 56, 0.82), 0.42),
    (ridgeline(51, HOR * 1.04, 76, 0.95), 0.64),
    (ridgeline(67, HOR * 1.24, 96, 1.05), 0.86),
    (ridgeline(83, HOR * 1.48, 112, 1.12), 1.00),
]

def build():
    # ---------- sky ----------
    for y in range(TOPBAR, int(HOR) + 3, 2):
        R(0, y, W, 3, sky_at(y))

    # the sun itself, low, and the scattering around it
    for k in range(120):
        u = k / 120.0
        D(SUNX, SUNY, 150 * (1 - u) + 7,
          mix(sky_at(SUNY), (255, 248, 232), 0.20 + 0.75 * u * u), 0.050 * (u ** 2.6))
    for k in range(70):
        u = k / 70.0
        D(SUNX, SUNY, 430 * (1 - u) + 40, mix(sky_at(SUNY), (255, 226, 186), 0.24),
          0.0042 * (u ** 2.2))
    D(SUNX, SUNY, 13, (255, 253, 246), 1.0)

    # ---------- ridges, far to near ----------
    prev_top = None
    for li, (f, depth) in enumerate(LAYERS):
        det = G.detail_for_depth(depth)
        vy = f(W * 0.5)
        if ON("values"):
            vtop = plan(0.5, min(0.999, max(0.0, vy) / H))
            body_v = max(0.04, vtop - 0.10 - 0.26 * depth)
            ctop = G.tint(body_v + 0.07, H_RIDGE, sat=0.55)
            cbot = G.tint(max(0.03, body_v - 0.13), H_RIDGE, sat=0.55)
        else:
            k = 1.0 - depth
            ctop = mix((36, 40, 62), (198, 202, 224), k)
            cbot = mix((14, 16, 26), (166, 174, 204), k)

        # fill the body down to the bottom edge - nearer layers cover farther ones
        x = 0.0
        while x < W:
            y = f(x)
            n = int((H + 24 - y) / 3) + 1
            for k in range(n):
                p = k / max(1, n - 1)
                R(x, y + (H + 24 - y) * p, 3, 4, mix(ctop, cbot, p ** 0.8))
            x += 3

        # ---------- 5. texture: erosion that follows the slope, self-similar ----------
        if ON("texture") and depth > 0.18:
            n_g = int(26 * det) + 4
            for _ in range(n_g):
                gx = random.uniform(0, W); gy = f(gx)
                slope = (f(min(W - 1, gx + 9)) - f(max(0, gx - 9))) / 18.0
                run = random.uniform(40, 150) * (0.4 + det)
                G.fractal_mass(a, gx + slope * run * 0.5, gy + run * 0.5,
                               6 + 6 * det, run * 0.5,
                               mix(cbot, (10, 11, 20), 0.5), (6, 7, 14),
                               levels=3, n0=7, gap=0.28, detail=det, alpha=0.17, rmax=3.2)
            G.fractal_field(a, 0, f(W * 0.5), W, min(H, f(W * 0.5) + 180),
                            mix(ctop, cbot, 0.5), mix(cbot, (8, 9, 16), 0.6),
                            n=int(26 * det) + 3, scale=22 * (0.4 + det),
                            detail=det, alpha=0.055, rmax=3.0)
        elif depth > 0.18:
            for _ in range(int(220 * (0.3 + depth))):
                gx = random.uniform(0, W); gy = f(gx)
                D(gx + random.uniform(-3, 3), gy + random.uniform(6, 110),
                  random.uniform(1.0, 2.6), mix(cbot, (10, 11, 20), 0.45), 0.16)

        # ---------- backlit rim: the sun is BEHIND, so every ridge top catches light ----------
        rim_v = 0.86 - 0.22 * (1.0 - depth)
        rim_c = G.tint(rim_v, H_RIM, sat=0.75) if ON("values") else (255, 216, 162)
        x = 0.0
        while x < W:
            y = f(x)
            d = math.hypot((x - SUNX) / (W * 0.55), (y - SUNY) / (HOR * 0.55))
            s = math.exp(-d * d * 0.75)
            step = random.uniform(0.7, 1.6)
            if s > 0.04 and random.random() > 0.22:      # break it up: never a continuous bead line
                jx = random.gauss(0, 0.9); jy = random.gauss(0, 1.1)
                D(x + jx, y + 0.6 + jy, random.uniform(0.5, 1.1) + 1.9 * s * (0.35 + depth),
                  rim_c, min(0.8, (0.10 + 0.72 * s) * random.uniform(0.55, 1.25)))
            x += step

        # ---------- 4. edges by depth ----------
        if ON("edges"):
            # An edge class is only allowed where nothing else already defines the boundary.
            # v1 drew a HARD pale line along the near crest and it read as chalk, because the
            # backlit rim ALREADY draws that silhouette. Rule: never state an edge twice.
            kind = G.edge_class(depth, focal=(depth >= 0.6))
            bg = sky_at(max(TOPBAR + 2, f(W * 0.5)))
            x = 0.0; prev = (0.0, f(0.0))
            while x < W:
                cur = (x, f(x))
                d = math.hypot((x - SUNX) / (W * 0.55), (cur[1] - SUNY) / (HOR * 0.55))
                lit = math.exp(-d * d * 0.75)
                if lit < 0.06:                       # rim light owns the lit part of the crest
                    # edge colour comes from the MASS side, never lighter than the mass, so it
                    # can only soften or lose the boundary - it can never outline it
                    ec = mix(ctop, bg, 0.30 if kind == G.LOST else 0.12)
                    G.edge(a, prev[0], prev[1], cur[0], cur[1], ec, kind,
                           w=1.0 + 1.6 * depth, bg=bg)
                prev = cur; x += 6

        # ---------- haze sitting in the valley IN FRONT of this ridge ----------
        # this is what "receding into haze" means: the separation lives between the layers
        haze_v = 0.60 + 0.26 * (1.0 - depth)
        haze_c = G.tint(haze_v, mix(H_SKY_WARM, H_SKY_MID, depth), sat=0.42) \
                 if ON("values") else mix((246, 226, 208), (206, 212, 232), depth)
        if ON("texture"):
            # haze is a MASS of many tiny low-alpha dabs, never a few big translucent discs
            for _ in range(int(26 + 22 * (1 - depth))):
                hx = random.uniform(-40, W + 40); hy = f(hx) + random.uniform(4, 58)
                G.fractal_mass(a, hx, hy, random.uniform(70, 210), random.uniform(9, 30),
                               haze_c, haze_c, levels=5, n0=11, falloff=0.62,
                               gap=0.18, detail=0.8, alpha=0.013, jitter=1.2, rmax=7.0)
        else:
            for _ in range(520):
                hx = random.uniform(0, W)
                D(hx, f(hx) + random.uniform(4, 60), random.uniform(12, 32), haze_c, 0.015)
        prev_top = f

    # a last wash of air over the whole distance, strongest at the horizon
    for _ in range(420):
        y = random.uniform(HOR * 0.55, H * 0.92)
        t = 1.0 - (y - HOR * 0.55) / (H * 0.92 - HOR * 0.55)
        D(random.uniform(0, W), y, random.uniform(30, 90),
          G.tint(0.74, H_SKY_WARM, 0.35) if ON("values") else (236, 222, 210),
          0.006 + 0.016 * t)

build()
OUT = f"g3_ridges_{STAGE}.png"

async def run():
    n = stamp(a)
    print(f"DAWN RIDGES [{STAGE}]: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up:
        launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    tab.run_meta = {"generation": 3, "subject": "dawn_ridges", "stage": STAGE,
                    "prompt": "Layered mountain ridges at dawn, receding into haze, "
                              "with the sun low behind them."}
    t0 = time.time()
    CH = 1800                    # small chunks + a real pause: this must be WATCHABLE
    for i in range(0, len(a.ops), CH):
        tab.fast(a.ops[i:i + CH]); await tab.sync(); await asyncio.sleep(0.05)
    await tab.sync()
    print(f"painted in {time.time() - t0:.2f}s", flush=True)
    await tab.png(OUT)

    cells = G.value_audit(OUT, plan, grid=26)
    mean0 = sum(abs(c["err"]) for c in cells) / len(cells)
    print(f"value error vs plan: mean {mean0:.4f}, worst {cells[0]['err']:+.3f} at {cells[0]['cell']}", flush=True)
    json.dump({"stage": STAGE, "ops": n, "mean_value_err": round(mean0, 4),
               "worst": cells[:20]}, open(f"g3_ridges_{STAGE}.audit.json", "w"), indent=1)

    if ON("audit"):
        worst = [c for c in cells if abs(c["err"]) > 0.05 and c["px"][1] > TOPBAR + 4][:80]
        fix = []
        for c in worst:
            x0, y0, x1, y1 = c["px"]; err = c["err"]
            target = (3, 4, 9) if err > 0 else (255, 240, 214)
            al = min(0.15, abs(err) * 0.32)
            for _ in range(int(34 * min(1.0, abs(err) * 5.5))):
                fix.append([2, round(random.uniform(x0, x1), 1), round(random.uniform(y0, y1), 1),
                            target[0], target[1], target[2],
                            round(random.uniform(10, 28), 1), round(al, 3)])
        print(f"audit: {len(worst)} bad cells, {len(fix):,} corrective strokes placed there", flush=True)
        tab.run_meta = dict(tab.run_meta, stage=STAGE + "+corrected",
                            base_ops=n, corrective_ops=len(fix))
        for i in range(0, len(fix), 5000):
            tab.fast(fix[i:i + 5000]); await tab.sync(); await asyncio.sleep(0.02)
        await tab.sync()
        await tab.png(f"g3_ridges_{STAGE}_corrected.png")
        after = G.value_audit(f"g3_ridges_{STAGE}_corrected.png", plan, grid=26)
        mean1 = sum(abs(c["err"]) for c in after) / len(after)
        print(f"value error: mean {mean0:.4f} -> {mean1:.4f}", flush=True)
    await br.close()

asyncio.run(run())
