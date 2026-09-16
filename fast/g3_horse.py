"""GEN 3 - MORNING FIELD.

PROMPT (PROMPTS.md, the only input): "A horse standing in an open field in early morning light."

This is the CONSTRUCTION test. Two stages, and the first one has no lighting in it at all:

  construct  flat gray shapes only. Skeleton, joints, attachment points, silhouette.
             No light, no colour, no texture. This is the only thing diagnosed at this stage.
  paint      the approved construction, painted. Values -> colour -> texture.

Everything is measured in HEAD LENGTHS, because that is how the proportion actually gets checked.
usage: python3 g3_horse.py <stage>
"""
import asyncio, math, random, sys, json, time, urllib.request
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

STAGE = sys.argv[1] if len(sys.argv) > 1 else "construct"
assert STAGE in ("construct", "paint")
A.GEN = f"3RD GEN · {STAGE.upper()}"
SEED = 3002
random.seed(SEED)
W, Hh = 1380, 900
a = Art(W, Hh, "MORNING FIELD")
R, L, D = a.R, a.L, a.D

HOR = Hh * 0.62                      # eye level - a standing viewer, so above the horse's back
GND = Hh * 0.80                      # where the horse's hooves meet the ground

# ---------------------------------------------------------------- proportion, in head lengths
# SOURCED, not invented. Standard artist head-length system (see CONSTRUCTION.md for citations):
#   height at withers      ~3.00 HL      (v1-v5 used 2.50 - confabulated, too short by a sixth)
#   body length, no tail   ~3.67 HL      (v1-v5 was roughly square - too short by a third)
#   leg length             ~= body depth back-to-belly, so each is half the height
#   head                   ~= as long as the shoulder; neck not much longer than the head
#   foreleg, side view     a near-VERTICAL COLUMN from the elbow down
#   hind leg, side view    a Z: femur down-and-FORWARD to the stifle, tibia down-and-BACK to
#                          the hock, then a vertical cannon. v1-v5 drew both legs as gentle
#                          diagonals, which is neither shape.
HEAD = 150.0
def hl(n): return n * HEAD

CX = W * 0.55                        # centre of the BODY, not of the whole animal
TOPLINE = GND - hl(3.00)             # withers
ELBOW_Y = GND - hl(1.50)             # half the height: the leg/body split
SHOULDER_X = CX - hl(1.83)           # point of shoulder  \  3.67 HL apart
BUTTOCK_X  = CX + hl(1.83)           # point of buttock   /

J = {}
J["withers"]  = (CX - hl(1.35), TOPLINE)
J["croup"]    = (CX + hl(1.30), TOPLINE + hl(0.04))
J["shoulder"] = (SHOULDER_X, TOPLINE + hl(0.95))
# --- foreleg: one vertical column. Every joint shares an x.
FORE_X = CX - hl(1.45)
J["elbow"]     = (FORE_X, ELBOW_Y)
J["knee"]      = (FORE_X, GND - hl(0.70))
J["f_fetlock"] = (FORE_X, GND - hl(0.20))
J["f_hoof"]    = (FORE_X, GND)
# --- hind leg: the Z
J["hip"]       = (CX + hl(1.42), TOPLINE + hl(0.50))
J["stifle"]    = (CX + hl(1.02), GND - hl(1.34))    # down and FORWARD, low, near the belly
J["hock"]      = (CX + hl(1.56), GND - hl(0.84))    # down and BACK, higher than the knee
J["r_fetlock"] = (CX + hl(1.58), GND - hl(0.20))    # then vertical
J["r_hoof"]    = (CX + hl(1.58), GND)
# --- head and neck. Neck ~1.15 HL from withers; head exactly 1 HL, poll to muzzle.
J["poll"]     = (CX - hl(2.16), TOPLINE - hl(0.81))
J["muzzle"]   = (CX - hl(3.03), TOPLINE - hl(0.31))
J["throat"]   = (CX - hl(2.05), TOPLINE - hl(0.18))

# ONE continuous silhouette. The elbow and the stifle sit ON the bottom profile, so the limbs
# below them grow out of the outline instead of being stuck on top of it - which is what made
# the legs read as separate objects in every earlier pass.
TOP = [
    (CX - hl(3.10), TOPLINE - hl(0.26)),   # nose
    (CX - hl(2.78), TOPLINE - hl(0.56)),   # bridge
    (CX - hl(2.30), TOPLINE - hl(0.86)),   # poll
    (CX - hl(1.95), TOPLINE - hl(0.70)),   # crest
    (CX - hl(1.60), TOPLINE - hl(0.34)),   # crest falling to the withers
    (CX - hl(1.35), TOPLINE),              # withers
    (CX - hl(0.55), TOPLINE + hl(0.10)),   # back, slightly dipped
    (CX + hl(0.60), TOPLINE + hl(0.06)),   # loin
    (CX + hl(1.30), TOPLINE + hl(0.04)),   # croup
    (CX + hl(1.68), TOPLINE + hl(0.34)),   # top of the buttock
    (BUTTOCK_X,     TOPLINE + hl(0.78)),   # rearmost point
]
BOT = [
    (CX - hl(3.10), TOPLINE - hl(0.26)),   # nose (shared)
    (CX - hl(2.86), TOPLINE - hl(0.10)),   # muzzle underside
    (CX - hl(2.36), TOPLINE - hl(0.22)),   # jaw
    (CX - hl(2.02), TOPLINE + hl(0.16)),   # throat latch
    (CX - hl(1.90), TOPLINE + hl(0.62)),   # base of the neck running into the chest
    (SHOULDER_X,    TOPLINE + hl(1.02)),   # point of shoulder - forward-most of the body
    (FORE_X - hl(0.02), ELBOW_Y),          # ELBOW: on the outline, the foreleg grows from here
    (CX - hl(0.90), ELBOW_Y + hl(0.05)),   # girth
    (CX - hl(0.10), ELBOW_Y - hl(0.04)),   # belly
    (CX + hl(0.70), ELBOW_Y - hl(0.20)),   # belly rising into the flank
    (J["stifle"][0], J["stifle"][1]),      # STIFLE: on the outline, the gaskin grows from here
    (CX + hl(1.44), TOPLINE + hl(2.10)),   # back of the gaskin
    (BUTTOCK_X,     TOPLINE + hl(0.78)),   # rearmost point (shared)
]

def _spline(pts, t):
    """Catmull-Rom through the profile points, so the outline is a curve not a chain of facets"""
    n = len(pts) - 1
    u = max(0.0, min(0.9999, t)) * n
    i = int(u); f = u - i
    p0 = pts[max(0, i-1)]; p1 = pts[i]; p2 = pts[min(n, i+1)]; p3 = pts[min(n, i+2)]
    def c(a, b, cc, d):
        return 0.5*((2*b) + (-a+cc)*f + (2*a-5*b+4*cc-d)*f*f + (-a+3*b-3*cc+d)*f*f*f)
    return (c(p0[0],p1[0],p2[0],p3[0]), c(p0[1],p1[1],p2[1],p3[1]))

def profile_curve(pts, n=260):
    return [_spline(pts, i/(n-1)) for i in range(n)]

def body_span(x):
    """top and bottom of the silhouette at this x, or None if x is outside the body"""
    top = profile_curve.cache_top; bot = profile_curve.cache_bot
    def at(curve):
        best = None
        for (px, py) in curve:
            d = abs(px - x)
            if best is None or d < best[0]: best = (d, py)
        return best
    a1 = at(top); a2 = at(bot)
    if a1 is None or a2 is None or a1[0] > 6 or a2[0] > 6: return None
    return (min(a1[1], a2[1]), max(a1[1], a2[1]))

def limb(p0, p1, w0, w1, col, n=None):
    n = n or max(6, int(math.hypot(p1[0]-p0[0], p1[1]-p0[1]) / 3))
    for i in range(n + 1):
        t = i / n
        D(p0[0] + (p1[0]-p0[0])*t, p0[1] + (p1[1]-p0[1])*t, max(0.8, w0 + (w1-w0)*t), col, 1.0)

def ellipse(cx, cy, rx, ry, col, step=3):
    yy = -ry
    while yy <= ry:
        span = rx * math.sqrt(max(0.0, 1 - (yy/ry)**2))
        R(cx - span, cy + yy, span*2, step + 1, col)
        yy += step

GRAY_BODY = G.gray(0.42)
GRAY_LIMB = G.gray(0.34)
GRAY_GND  = G.gray(0.66)
GRAY_SKY  = G.gray(0.86)

def horse(body, limbc):
    """the construction itself. Same call draws the gray block-in and the painted underform."""
    # far-side legs first, darker, so the near pair reads in front
    limb((J["shoulder"][0]+hl(0.07), J["shoulder"][1]), (J["knee"][0]+hl(0.09), J["knee"][1]),
         hl(0.16), hl(0.07), limbc)
    limb((J["knee"][0]+hl(0.09), J["knee"][1]), (J["f_hoof"][0]+hl(0.10), J["f_hoof"][1]),
         hl(0.07), hl(0.05), limbc)
    limb((J["hip"][0]-hl(0.04), J["hip"][1]), (J["hock"][0]-hl(0.06), J["hock"][1]),
         hl(0.22), hl(0.08), limbc)
    limb((J["hock"][0]-hl(0.06), J["hock"][1]), (J["r_hoof"][0]-hl(0.05), J["r_hoof"][1]),
         hl(0.08), hl(0.05), limbc)
    # ONE mass: fill between the top and bottom profile curves. Head, neck, barrel and
    # hindquarter are the same silhouette, so nothing can read as stuck on.
    tc = profile_curve(TOP, 320); bc = profile_curve(BOT, 320)
    xs = [p[0] for p in tc + bc]
    x = min(xs); xmax = max(xs); step = 2.0
    while x <= xmax:
        ys_t = [p[1] for p in tc if abs(p[0] - x) < 10]
        ys_b = [p[1] for p in bc if abs(p[0] - x) < 10]
        if ys_t and ys_b:
            yt = min(ys_t); yb = max(ys_b)
            if yb > yt: R(x, yt, step + 1, yb - yt, body)
        x += step

    # near-side legs, on top
    limb(J["shoulder"], J["elbow"], hl(0.26), hl(0.16), body)
    limb(J["elbow"], J["knee"], hl(0.15), hl(0.075), limbc)
    limb(J["knee"], J["f_fetlock"], hl(0.072), hl(0.055), limbc)
    limb(J["f_fetlock"], J["f_hoof"], hl(0.058), hl(0.062), limbc)
    limb(J["hip"], J["stifle"], hl(0.30), hl(0.16), body)
    limb(J["stifle"], J["hock"], hl(0.16), hl(0.085), limbc)
    limb(J["hock"], J["r_fetlock"], hl(0.080), hl(0.052), limbc)
    limb(J["r_fetlock"], J["r_hoof"], hl(0.055), hl(0.060), limbc)
    # tail hangs from the point of buttock, not the croup: a short thick dock, then a narrow
    # skirt. Drawn from the rearmost profile point so it cannot float clear of the body.
    tx, ty = CX + hl(1.10), TOPLINE + hl(0.40)
    for i in range(44):
        t = i / 43.0
        w = hl(0.085) * (1 - t) ** 0.6 + hl(0.020)
        D(tx + hl(0.10) * t + math.sin(t * 2.4) * hl(0.03), ty + hl(1.26) * t, w, limbc, 1.0)

def build_construct():
    """flat gray only. If it does not read here, no amount of light will save it."""
    for y in range(TOPBAR, int(HOR), 3): R(0, y, W, 4, GRAY_SKY)
    for y in range(int(HOR), Hh, 3):     R(0, y, W, 4, GRAY_GND)
    L(0, GND, W, GND, 1.0, G.gray(0.52))                       # the ground plane the hooves meet
    horse(GRAY_BODY, GRAY_LIMB)
    # joint markers + a head-length ruler, so proportion is checked as numbers not vibes
    for k, (x, y) in J.items():
        D(x, y, 5.0, G.gray(0.08), 1.0); D(x, y, 2.2, G.gray(0.95), 1.0)
    for i in range(4):
        R(W*0.04 + i*HEAD, Hh*0.93, HEAD-4, 7, G.gray(0.20 if i % 2 else 0.80))

if STAGE == "construct":
    build_construct()
# ---------------------------------------------------------------- the paint stage
# Values first, then hue as a tint on the value, then texture. Light is early morning: low,
# warm, coming from the left and slightly in front, so the head and chest are lit and the
# hindquarter falls away into shadow. One light, one direction, stated once.
LX, LY = -W * 0.35, TOPLINE - hl(0.70)          # low sun, off the left edge
SKY_HI, SKY_LO = (86, 118, 170), (246, 214, 178)
GRASS_FAR, GRASS_NEAR = (178, 176, 130), (86, 92, 52)
COAT = (112, 74, 48)                             # bay
WARM = (255, 208, 150)
COOL = (64, 74, 104)

def plan_v(u, v):
    y = v * Hh
    if y < TOPBAR: return 0.07
    if y < HOR:
        t = (y - TOPBAR) / (HOR - TOPBAR)
        return 0.40 + 0.46 * (t ** 0.8)
    t = (y - HOR) / (Hh - HOR)
    return 0.62 - 0.34 * (t ** 0.75)

def light_at(x, y):
    """diffuse term from the single low sun, 0..1"""
    dx = LX - x; dy = LY - y
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n

_last = [0]
_split = []
def _mark(name):
    _split.append((name, len(a.ops) - _last[0])); _last[0] = len(a.ops)

def build_paint():
    _mark("sky")
    # ---- sky
    for y in range(TOPBAR, int(HOR) + 3, 2):
        t = (y - TOPBAR) / (HOR - TOPBAR)
        R(0, y, W, 3, G.tint(plan_v(0.5, y / Hh), mix(SKY_HI, SKY_LO, t ** 1.2), sat=0.62))
    # low sun glow off frame left
    for k in range(80):
        u = k / 80.0
        D(W * 0.02, TOPLINE - hl(0.55), 520 * (1 - u) + 30,
          mix(G.tint(0.86, SKY_LO, 0.5), (255, 244, 220), 0.3 + 0.6 * u * u), 0.010 * (u ** 2.0))
    _mark("field")
    # ---- field: detail frequency falls with distance (Rule 6)
    for y in range(int(HOR), Hh, 2):
        d = (y - HOR) / (Hh - HOR)
        R(0, y, W, 3, G.tint(plan_v(0.5, y / Hh), mix(GRASS_FAR, GRASS_NEAR, d ** 0.7), sat=0.70))
    for band in range(9):
        d = band / 8.0
        y0 = HOR + (Hh - HOR) * (d ** 1.35)
        det = G.detail_for_depth(d)
        gcol = G.tint(plan_v(0.5, y0 / Hh) - 0.06, mix(GRASS_FAR, GRASS_NEAR, d ** 0.7), 0.72)
        gsh  = G.tint(max(0.05, plan_v(0.5, y0 / Hh) - 0.24), mix(GRASS_FAR, GRASS_NEAR, d), 0.6)
        G.fractal_field(a, -40, y0, W + 40, y0 + (Hh - HOR) * 0.14,
                        gcol, gsh, n=int(40 + 120 * det), scale=6 + 26 * det,
                        detail=det, alpha=0.34, rmax=1.4 + 3.0 * det)
    # a few near grass blades, only in the front third
    for _ in range(900):
        x = random.uniform(0, W); y = random.uniform(Hh * 0.88, Hh)
        h = random.uniform(8, 30)
        L(x, y, x + random.gauss(0, 4), y - h, random.uniform(0.7, 1.6),
          G.tint(random.uniform(0.22, 0.44), GRASS_NEAR, 0.8))

    _mark("shadow")
    # ---- cast shadow. The sun is low and off to the LEFT, so the shadow is long and lies to
    # the RIGHT. v1 drew a symmetric blob under the belly, which reads as a sticker and says
    # nothing about where the light is. A cast shadow is the second statement of the light.
    SH_LEN = hl(5.2)                                   # a low sun throws a very long shadow
    for _ in range(11000):
        t = random.random() ** 0.55
        px = J["f_hoof"][0] + hl(0.10) + SH_LEN * t + random.gauss(0, hl(0.30) * (0.35 + 1.3*t))
        py = GND + random.gauss(0, hl(0.035) + hl(0.075) * t)
        soft = (1.0 - t) ** 2.1                        # dissolves fast as it runs away
        al = 0.038 * soft + 0.004
        D(px, py, random.uniform(6, 30) * (0.45 + 1.4 * t),
          G.tint(0.26 - 0.10 * soft, COOL, 0.45), al)

    # the contact points themselves: the only truly dark, truly hard part of the shadow
    for (hx, hy) in (J["f_hoof"], J["r_hoof"]):
        for _ in range(500):
            r = random.random() ** 2.2
            D(hx + random.gauss(0, hl(0.10)) + hl(0.10) * r,
              hy + random.gauss(0, hl(0.022)),
              random.uniform(2, 9), G.tint(0.11, COOL, 0.55), 0.10 * (1 - r))

    _mark("horse body")
    # ---- the horse: same construction, now with value + form + texture
    tc = profile_curve(TOP, 340); bc = profile_curve(BOT, 340)
    xs = [p[0] for p in tc + bc]
    xlo, xhi = min(xs), max(xs)
    global xlo_g, xhi_g
    xlo_g, xhi_g = xlo, xhi

    # ---- form, occlusion and the anatomical creases -------------------------------------
    # v1 shaded the body as one smooth cylinder and it read as a plastic toy. A horse reads as
    # a horse because of a handful of specific darks that are NOT about the light direction:
    # the groove behind the shoulder blade, the flank crease in front of the stifle, the shadow
    # the barrel throws down onto the belly and the inside of the legs. Those are occlusion.
    # Light says which side is bright. Occlusion says which parts are buried. Both, or neither.

    # (x, y, radius, strength) - a crease darkens everything within its radius
    CREASES = [
        (CX - hl(0.46), TOPLINE + hl(0.66), hl(0.30), 0.55),   # behind the shoulder blade
        (CX + hl(0.56), TOPLINE + hl(1.02), hl(0.34), 0.48),   # flank, in front of the stifle
        (CX - hl(0.92), TOPLINE + hl(0.30), hl(0.26), 0.42),   # neck into the chest
        (CX - hl(1.34), TOPLINE - hl(0.22), hl(0.17), 0.38),   # under the jaw / throat
        (CX + hl(0.92), TOPLINE + hl(0.52), hl(0.22), 0.30),   # point of buttock into the thigh
    ]
    # masses that bulge toward the viewer and so catch the light first
    BULGES = [
        (CX - hl(0.60), TOPLINE + hl(0.56), hl(0.40), 0.55),   # shoulder
        (CX + hl(0.74), TOPLINE + hl(0.58), hl(0.46), 0.60),   # hindquarter
        (CX - hl(1.20), TOPLINE - hl(0.50), hl(0.22), 0.35),   # cheek
    ]

    def occlusion(x, y, yt, yb):
        """0 = wide open to the sky, 1 = buried. Independent of where the sun is."""
        depth = G.frac(y, yt, yb)                      # low in the body = more enclosed
        o = 0.30 * (depth ** 1.6)
        # the barrel throws its own shadow down onto the belly and the inner legs
        if depth > 0.62:
            o += 0.40 * ((depth - 0.62) / 0.38) ** 1.2
        for (cx, cy, r, k) in CREASES:
            d = math.hypot(x - cx, y - cy) / r
            if d < 1.0:
                o += k * (1.0 - d) ** 1.8
        return max(0.0, min(0.92, o))

    def shade_at(x, y, yt, yb):
        """diffuse from the one low sun, then the bulges, then occlusion takes it away again"""
        m = (yt + yb) * 0.5; half = max(1.0, (yb - yt) * 0.5)
        n = max(-1.0, min(1.0, (y - m) / half))        # -1 top of the mass, +1 underside
        nz = math.sqrt(max(0.0, 1 - n * n))            # facing the viewer
        along = G.frac(x, xlo_g, xhi_g)
        front = (1.0 - along) ** 0.8                   # the head end is nearest the sun
        diff = nz * 0.30 + (-n) * 0.26 + front * 0.58
        for (bx, by, br, bk) in BULGES:                # a mass turned toward the light
            d = math.hypot(x - bx, y - by) / br
            if d < 1.0: diff += bk * (1.0 - d) ** 1.5 * 0.42
        lit = max(0.0, min(1.0, 0.06 + 0.94 * diff))
        return lit * (1.0 - occlusion(x, y, yt, yb))

    body_cells = []
    body_cells = []
    x = xlo
    while x <= xhi:
        ys_t = [p[1] for p in tc if abs(p[0] - x) < 10]
        ys_b = [p[1] for p in bc if abs(p[0] - x) < 10]
        if ys_t and ys_b:
            yt = min(ys_t); yb = max(ys_b)
            if yb > yt:
                body_cells.append((x, yt, yb))
                y = yt
                while y <= yb:
                    sh = shade_at(x, y, yt, yb)
                    v = 0.10 + 0.40 * sh
                    c = G.tint(v, mix(COOL, mix(COAT, WARM, sh * 0.55), 0.25 + 0.65 * sh), 0.72)
                    R(x, y, 3, 4, c)
                    y += 3
        x += 2.0

    # legs, painted with the same light
    def plimb(p0, p1, w0, w1, lit):
        """A lit cylinder is not a gradient. Across its width it goes: highlight, terminator,
        CORE SHADOW (darkest, and NOT at the edge), then reflected light off the ground lifting
        the far edge back up. v1 put the darkest value at the edge, which is why the legs read
        as flat cones. The bounce is what makes a leg look round."""
        n = max(8, int(math.hypot(p1[0]-p0[0], p1[1]-p0[1]) / 2))
        for i in range(n + 1):
            t = i / n
            cx = p0[0] + (p1[0]-p0[0])*t; cy = p0[1] + (p1[1]-p0[1])*t
            w = w0 + (w1-w0)*t
            # the top of a leg is tucked under the barrel; the bottom is out in the open
            tuck = (1.0 - t) ** 1.4
            ground = G.frac(cy, GND - hl(0.9), GND)     # how close to the ground we are
            k = -w
            while k <= w:
                nn = k / max(1.0, w)                    # -1 lit edge, +1 far edge
                body = math.sqrt(max(0.0, 1 - nn*nn))   # roundness
                key   = math.exp(-((nn + 0.45) ** 2) / 0.24) * 0.95      # the lit band
                core  = math.exp(-((nn - 0.52) ** 2) / 0.10) * 0.55      # core shadow
                bounce= max(0.0, (nn - 0.66) / 0.34) ** 1.6 * 0.30 * (0.35 + 0.65*ground)
                # do NOT multiply by roundness here - key and core already describe the turn,
                # and multiplying again drove every leg to black in v2.
                sh = 0.30 + key * 0.62 + bounce - core
                sh = max(0.0, min(1.0, sh)) * lit * (1.0 - 0.20 * tuck)
                v = 0.13 + 0.34 * sh                     # a leg is DARKER than the barrel,
                v *= (0.86 + 0.14 * body)                # not a different colour of animal
                # the bounce off a sunlit field comes back GREEN, not warm like the sun
                hue = mix(COOL, mix(COAT, WARM, sh*0.5), 0.18 + 0.72*sh)
                if bounce > 0.04: hue = mix(hue, (120, 128, 74), min(0.35, bounce * 1.1))
                D(cx + k, cy, 1.6, G.tint(v, hue, 0.72), 1.0)
                k += 1.5
    for (p0, p1, w0, w1, lit) in [
        ((J["elbow"][0]+hl(0.07), J["elbow"][1]), (J["knee"][0]+hl(0.09), J["knee"][1]), hl(0.115), hl(0.065), 0.52),
        ((J["knee"][0]+hl(0.09), J["knee"][1]), (J["f_hoof"][0]+hl(0.10), J["f_hoof"][1]), hl(0.065), hl(0.048), 0.52),
        ((J["stifle"][0]-hl(0.04), J["stifle"][1]-hl(0.22)), (J["hock"][0]-hl(0.06), J["hock"][1]), hl(0.19), hl(0.075), 0.46),
        ((J["hock"][0]-hl(0.06), J["hock"][1]), (J["r_hoof"][0]-hl(0.05), J["r_hoof"][1]), hl(0.075), hl(0.048), 0.46),
        ((J["elbow"][0], J["elbow"][1]-hl(0.18)), J["knee"], hl(0.17), hl(0.072), 1.0),
        (J["knee"], J["f_fetlock"], hl(0.069), hl(0.052), 1.0),
        (J["f_fetlock"], J["f_hoof"], hl(0.056), hl(0.060), 1.0),
        ((J["stifle"][0], J["stifle"][1]-hl(0.26)), J["hock"], hl(0.22), hl(0.082), 0.92),
        (J["hock"], J["r_fetlock"], hl(0.078), hl(0.050), 0.92),
        (J["r_fetlock"], J["r_hoof"], hl(0.053), hl(0.058), 0.92),
    ]:
        plimb(p0, p1, w0, w1, lit)

    _mark("coat")
    # ---- coat. v1 scattered fractal blobs and nothing registered at this scale. A horse coat
    # is SHORT HAIR LYING IN A DIRECTION: roughly along the barrel, radiating out over the
    # hindquarter, down the shoulder. And it is only visible in the MID tones - blown out in
    # the light, swallowed in the shadow. Texture that ignores the value band reads as dirt.
    def hair_dir(x, y):
        """which way the coat lies at this point"""
        hx, hy = CX + hl(0.74), TOPLINE + hl(0.58)          # hindquarter whorl
        d = math.hypot(x - hx, y - hy)
        if d < hl(0.52):                                     # radiating off the hindquarter
            return math.atan2(y - hy, x - hx) + 1.4
        sx, sy = CX - hl(0.60), TOPLINE + hl(0.56)           # shoulder: hair runs down and back
        if math.hypot(x - sx, y - sy) < hl(0.44):
            return 1.05
        if x < CX - hl(0.80):                                # neck: along the crest line
            return -0.42
        return 0.10                                          # barrel: along the animal
    for (x, yt, yb) in body_cells:
        for _ in range(3):
            y = random.uniform(yt, yb)
            sh = shade_at(x, y, yt, yb)
            band = math.exp(-((sh - 0.46) ** 2) / 0.052)     # mid-tones only
            if band < 0.12: continue
            ang = hair_dir(x, y) + random.gauss(0, 0.20)
            ln = random.uniform(4.0, 11.0)
            dark = random.random() < 0.5
            v = 0.10 + 0.40 * sh + (-0.055 if dark else 0.055)
            c = G.tint(max(0.03, v), mix(COAT, WARM, sh * 0.6), 0.72)
            L(x, y, x + math.cos(ang) * ln, y + math.sin(ang) * ln,
              random.uniform(0.6, 1.3), c)

    _mark("mane+tail")
    # ---- mane and tail. Both were sprays of separate dabs and read as flung dirt. Hair has
    # MASS first and strands second: lay a solid dark body of hair, then draw strands only at
    # its edges where individual hairs actually separate against the light.
    def hair_mass(root, direction, n_strands, length, spread, col_dark, col_lit,
                  curl=0.0, taper=0.45):
        """Hair is neither a filled band nor a spray of dots. It is MANY STRANDS, dense enough
        that they merge in the middle and separate at the edges. Drawing a solid band gives a
        hard painted stripe (the tail came out a rectangle); drawing loose dabs gives flung
        dirt. Dense strands give both behaviours from one construction, which is what hair
        actually is. root(t)->(x,y) along the hair line, direction(t)->angle it falls."""
        for i in range(n_strands):
            t = random.random()
            rx, ry = root(t)
            ang = direction(t) + random.gauss(0, spread)
            ln = length * random.uniform(0.45, 1.0) ** 0.7
            # each strand starts a little off the line, which is what breaks the edge up
            rx += random.gauss(0, 2.2); ry += random.gauss(0, 2.2)
            steps = max(6, int(ln / 2.6))
            lit = random.random() ** 1.6
            for k in range(steps):
                u = k / (steps - 1.0)
                a = ang + curl * u * u
                D(rx + math.cos(a) * ln * u + math.sin(u * 5.0 + i) * 1.1,
                  ry + math.sin(a) * ln * u,
                  max(0.55, 1.45 * (1 - u * taper)),
                  mix(col_dark, col_lit, lit * (1 - u * 0.45)), 1.0)

    MANE_D = G.tint(0.065, mix((34, 24, 17), COOL, 0.25), 0.55)
    MANE_L = G.tint(0.34, mix((92, 66, 40), WARM, 0.40), 0.70)
    # the mane lies along the crest, falling to the near side
    def mane_root(t):
        x, y = _spline(TOP, 0.150 + 0.345 * t)
        return (x + hl(0.010), y + hl(0.020))
    hair_mass(mane_root, lambda t: 1.44 + 0.30 * math.sin(t * 2.6), 520,
              hl(0.30), 0.20, MANE_D, MANE_L, curl=0.22, taper=0.5)
    # forelock falls forward between the ears
    hair_mass(lambda t: _spline(TOP, 0.145 + 0.02 * t), lambda t: 2.35, 90,
              hl(0.22), 0.26, MANE_D, MANE_L, curl=0.30)

    # tail: same construction, rooted at the buttock, long and swinging slightly back
    tx, ty = CX + hl(1.11), TOPLINE + hl(0.40)
    hair_mass(lambda t: (tx + hl(0.02) * t, ty + hl(0.10) * t),
              lambda t: 1.40 + 0.16 * math.sin(t * 3.0), 760,
              hl(1.30), 0.10, MANE_D, MANE_L, curl=0.16, taper=0.38)

    _mark("edges")
    # ---- the silhouette edge. The sun is low and to the LEFT, so the left-and-upward facing
    # boundary takes a warm rim and the right-facing boundary is LOST into the field behind it.
    # An even outline all the way round is the single strongest tell of illustration.
    for (x, yt, yb) in body_cells:
        along = G.frac(x, xlo_g, xhi_g)
        face = (1.0 - along) ** 0.7                         # front of the animal faces the sun
        if face > 0.22:
            for _ in range(2):
                D(x + random.gauss(0, 0.7), yt + random.uniform(0.2, 2.2),
                  random.uniform(0.6, 1.7),
                  G.tint(0.62 + 0.26 * face, WARM, 0.82),
                  min(0.62, (0.06 + 0.60 * face) * random.uniform(0.5, 1.2)))
        else:
            # lost edge: let the rear of the animal dissolve into the field
            bgv = plan_v(0.5, yt / Hh) - 0.10
            for _ in range(3):
                D(x + random.gauss(0, 2.2), yt + random.gauss(0, 2.4), random.uniform(2.5, 6.0),
                  G.tint(max(0.05, bgv), mix(GRASS_FAR, COOL, 0.45), 0.5), 0.035)
    # the strongest light of all lands on the face, the front of the chest and the near foreleg
    for i in range(300):
        t = i / 299.0
        px, py = _spline(BOT, 0.015 + 0.33 * t)
        D(px + random.gauss(0, 0.6), py, random.uniform(0.9, 2.4),
          G.tint(0.88, WARM, 0.88), random.uniform(0.22, 0.62))

    # eye, placed off the construction: below the poll, a third of the way to the muzzle
    ex = J["poll"][0] - hl(0.30); ey = J["poll"][1] + hl(0.30)
    D(ex, ey, hl(0.045), G.tint(0.06, COOL, 0.4), 1.0)
    D(ex - hl(0.012), ey - hl(0.012), hl(0.013), (255, 246, 226), 0.9)

if STAGE == "paint":
    build_paint()
    _mark("eye/misc")
    tot = sum(n for _, n in _split[1:]) or 1
    print("--- where the strokes went ---")
    for nm, n in _split[1:]:
        print(f"  {nm:12} {n:>8,}  {100.0*n/tot:5.1f}%")
    print(f"  {'TOTAL':12} {tot:>8,}")
OUT = f"g3_horse_{STAGE}.png"

async def run():
    n = stamp(a)
    print(f"MORNING FIELD [{STAGE}]: {n:,} strokes", flush=True)
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto("https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time())))
    await tab.measure_canvas(); await tab.resize_canvas(W, Hh)
    tab.run_meta = {"generation": 3, "subject": "morning_field", "stage": STAGE,
                    "head_len_px": HEAD,
                    "prompt": "A horse standing in an open field in early morning light."}
    t0 = time.time()
    CH = 1800
    for i in range(0, len(a.ops), CH):
        tab.fast(a.ops[i:i+CH]); await tab.sync(); await asyncio.sleep(0.05)
    await tab.sync()
    print(f"painted in {time.time()-t0:.2f}s", flush=True)
    await tab.png(OUT)
    await br.close()

asyncio.run(run())
