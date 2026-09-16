"""GEN 3 technique library.

Everything here is a technique the gen3 doctrine actually calls for and that I can honestly
implement in a procedural script. Anything I could not implement is named in RELEASED below
rather than faked.

Ordering discipline (CONSTRUCTION.md): construction -> values -> colour -> edges -> texture.
Vocabulary stays closed at rect / line / dab, replay-identical.
"""
import math, random
from art import Art, mix, TOPBAR

RELEASED = """
- Error-map placement against a TARGET: a from-scratch painting has no target image, so the honest
  version is a self-diff against the value plan (see value_audit). Implemented in that weaker form.
- Human approval between construction and paint: a script cannot wait on Matt's eye mid-run.
  Instead construction renders as its own gray pass that gets looked at before the colour script
  is written.
- Numeric realism scoring: no reference to score against on original work. Not implemented.
"""

# ---------------------------------------------------------------- values
# Rule 2: assign each plane a value before colour exists. These are the only values allowed;
# a painting that reads wrong in gray will read wrong in colour.
V = {"sky_top": 0.78, "sky_horizon": 0.92, "far": 0.66, "mid": 0.45, "near": 0.28,
     "mass": 0.18, "accent": 0.96, "shadow": 0.10}

def gray(v):
    """a planned value as a paintable neutral"""
    g = int(max(0, min(255, round(v * 255))))
    return (g, g, g)

def tint(v, hue, sat=0.5):
    """give a planned value a colour without moving the value.
    hue is an (r,g,b) direction; the result keeps luminance v."""
    h = [c / 255.0 for c in hue]
    hl = 0.2126 * h[0] + 0.7152 * h[1] + 0.0722 * h[2] or 1e-6
    out = [min(1.0, c * (v / hl)) for c in h]
    out = [(1 - sat) * v + sat * c for c in out]
    return tuple(int(max(0, min(255, round(c * 255)))) for c in out)

# ---------------------------------------------------------------- safe fractions
def frac(v, v0, v1):
    """Normalised position of v between v0 and v1, CLAMPED to [0,1].

    Use this for every 0..1 ramp instead of dividing by hand. `int(H*0.28)` lands a hair BELOW
    H*0.28 (900*0.28 is 252.00000000000003), so a loop starting at the int produces a fraction
    like -4e-17, and in Python a negative base with a fractional exponent returns a COMPLEX
    number rather than raising. The failure then surfaces hundreds of lines away as
    "'<' not supported between instances of 'complex' and 'float'". Clamp at the source.
    """
    span = v1 - v0
    if span == 0: return 0.0
    return max(0.0, min(1.0, (v - v0) / span))

# ---------------------------------------------------------------- scale / depth
def detail_for_depth(depth, near=1.0, far=0.0):
    """Rule 6: detail frequency falls with distance. Returns a 0..1 multiplier for how much
    texture a thing at this depth is allowed. depth 0 = far plane, 1 = nearest."""
    d = max(0.0, min(1.0, depth))
    return far + (near - far) * (d ** 2.2)

def atmos(col, depth, sky, strength=1.0):
    """far = lighter, bluer, lower contrast. depth 1 = near (untouched), 0 = far (in the haze)"""
    t = (1.0 - max(0.0, min(1.0, depth))) ** 1.3 * strength
    return mix(col, sky, min(0.92, t))

# ---------------------------------------------------------------- edges
# Rule 3: hard at focus, soft with distance, LOST where value difference vanishes.
HARD, SOFT, LOST = "hard", "soft", "lost"

def edge_class(depth, in_shadow=False, focal=False):
    if focal and not in_shadow: return HARD
    if in_shadow or depth < 0.25: return LOST
    return SOFT

def edge(art, x1, y1, x2, y2, col, kind=SOFT, w=2.0, bg=None):
    """draw a boundary at the requested edge class. LOST needs the background to dissolve into."""
    if kind == HARD:
        art.L(x1, y1, x2, y2, w, col); return
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 2.2))
    for i in range(n):
        p = i / (n - 1)
        x = x1 + (x2 - x1) * p; y = y1 + (y2 - y1) * p
        if kind == SOFT:
            art.D(x + random.gauss(0, w * 0.5), y + random.gauss(0, w * 0.5), w * 1.3, col, 0.32)
        else:  # LOST: fade the edge colour into the background and drop out in patches
            if random.random() < 0.45: continue
            c = mix(col, bg or col, random.uniform(0.55, 0.95))
            art.D(x + random.gauss(0, w), y + random.gauss(0, w), w * 1.6, c, 0.16)

# ---------------------------------------------------------------- recursive texture
# Rule 8 + the fractal answer: natural texture is self-similar across scales, NOT uniform
# scatter. Place large masses, subdivide into smaller versions at reduced amplitude, 3-4 levels.
# TUNED BY EYE, not derived. falloff, levels, n0, gap and jitter have no correct value to look
# up - anything in the neighbourhood produces plausible texture. Do not go looking for a
# citation for these. See the two-zone rule in CONSTRUCTION.md.
def fractal_mass(art, cx, cy, rx, ry, col, shade=(0, 0, 0), levels=4, n0=14,
                 falloff=0.52, gap=0.16, detail=1.0, alpha=1.0, jitter=0.9, rmax=None):
    """Self-similar clumped mass: foliage, rock, cloud, fur, moss. The mush fix.
    detail (from detail_for_depth) prunes the deepest levels for far-away things."""
    lv = max(1, int(round(levels * (0.45 + 0.55 * detail))))
    def sub(x, y, sx, sy, d, amp):
        n = max(2, int(n0 * (falloff ** d) * (0.5 + 0.5 * detail)))
        for _ in range(n):
            a = random.uniform(0, 6.2832); r = random.random() ** 0.55
            px = x + math.cos(a) * sx * r * jitter
            py = y + math.sin(a) * sy * r * jitter
            rr = (sx + sy) * 0.5 * (falloff ** d) * random.uniform(0.55, 1.15)
            if d >= lv - 1:
                if random.random() < gap: continue
                c = mix(col, shade, random.uniform(0, 0.55) * amp)
                r_draw = rr * 0.9
                # A low-alpha dab bigger than a few px reads as a bokeh disc, not as texture.
                # rmax is the cap that keeps a soft mass soft instead of beaded.
                if rmax is not None: r_draw = min(r_draw, rmax)
                art.D(px, py, max(0.6, r_draw), c, alpha)
            else:
                sub(px, py, sx * falloff, sy * falloff, d + 1, amp * 0.86)
    sub(cx, cy, rx, ry, 0, 1.0)

def fractal_branch(art, x, y, ang, length, wid, col, shade=(0, 0, 0), depth=0, maxd=6,
                   ratio=0.72, spread=0.52, leaf=None, detail=1.0):
    """Recursive splits, fixed angle range, diameter ratio at each junction.
    Correct-looking trees without anatomy knowledge, cheap in ops."""
    if depth > maxd * (0.5 + 0.5 * detail) or length < 3 or wid < 0.5:
        if leaf: leaf(x, y, length)
        return
    x2 = x + math.cos(ang) * length; y2 = y + math.sin(ang) * length
    steps = max(2, int(length / 5))
    for i in range(steps):
        p = i / steps
        # junction swell, capped and confined to the first 8% then tapered (TRICKS)
        sw = 1.0 + 0.32 * max(0.0, 1 - p / 0.08) if p < 0.08 else (1 - p) ** 1.75 * 0.25 + 0.85
        art.D(x + (x2 - x) * p, y + (y2 - y) * p, max(0.6, wid * sw),
              mix(col, shade, 0.25 + 0.35 * p), 1.0)
    for k in (-1, 1):
        a = ang + k * random.uniform(spread * 0.45, spread) + random.gauss(0, 0.07)
        fractal_branch(art, x2, y2, a, length * ratio * random.uniform(0.85, 1.1),
                       wid * ratio, col, shade, depth + 1, maxd, ratio, spread, leaf, detail)
    if random.random() < 0.30:   # a third, weaker split so it is not a binary lattice
        a = ang + random.gauss(0, spread * 0.5)
        fractal_branch(art, x2, y2, a, length * ratio * 0.7, wid * ratio * 0.8,
                       col, shade, depth + 1, maxd, ratio, spread, leaf, detail)

def fractal_field(art, x0, y0, x1, y1, col, shade, n=90, scale=40, detail=1.0, alpha=1.0, rmax=None):
    """a band of self-similar texture: rock face, bark grain, distant hedgerow, water chop"""
    for _ in range(int(n * (0.4 + 0.6 * detail))):
        x = random.uniform(x0, x1); y = random.uniform(y0, y1)
        s = scale * random.uniform(0.5, 1.5)
        fractal_mass(art, x, y, s, s * random.uniform(0.4, 0.8), col, shade,
                     levels=3, n0=8, detail=detail, alpha=alpha, rmax=rmax)

# ---------------------------------------------------------------- occlusion
def visible(pt, parts, skip=None, slack=1.06):
    """Rule 4: is this point on the TRUE outer boundary, or swallowed by another part?"""
    x, y = pt
    for q in parts:
        if q is skip or q == skip: continue
        ox, oy, orx, ory = q
        if ((x - ox) / orx) ** 2 + ((y - oy) / ory) ** 2 < slack:
            return False
    return True

# ---------------------------------------------------------------- value audit
def value_audit(png_path, plan, grid=24):
    """The honest version of error-map placement: render, read the canvas back, and compare
    actual luminance against the value PLAN, cell by cell. Returns the worst cells so the next
    batch of strokes goes where the error is, not spread evenly.
    plan(u, v) -> intended 0..1 value for normalised canvas position."""
    from PIL import Image
    import numpy as np
    im = Image.open(png_path).convert("L")
    a = np.asarray(im).astype("float32") / 255.0
    H, W = a.shape
    out = []
    for gy in range(grid):
        for gx in range(grid):
            y0, y1 = int(gy * H / grid), int((gy + 1) * H / grid)
            x0, x1 = int(gx * W / grid), int((gx + 1) * W / grid)
            got = float(a[y0:y1, x0:x1].mean())
            want = plan((gx + 0.5) / grid, (gy + 0.5) / grid)
            out.append({"cell": (gx, gy), "px": (x0, y0, x1, y1),
                        "got": round(got, 4), "want": round(want, 4),
                        "err": round(got - want, 4)})
    out.sort(key=lambda c: -abs(c["err"]))
    return out
