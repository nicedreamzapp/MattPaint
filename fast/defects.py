"""PHOTOGRAPHIC DEFECTS — the 'paint badly on purpose' pass.

Premise being tested: the gap between these paintings and photographs is not detail, it is
DEFECT. A photograph has lens fall-off, chromatic fringing at high-contrast edges, sensor noise
that rises in shadow, imperfect focus, dust, asymmetry. Every painting here is too clean, and
clean is what reads as rendered.

This runs AFTER a finished painting, reads the canvas back, and adds flaws. It is deliberately
separable from the loop so it can be A/B'd on its own. Vocabulary stays rect/line/dab.

Every constant here is TUNED BY EYE except the ones marked SOURCED — see the two-zone rule in
CONSTRUCTION.md. The physics being imitated is real; the magnitudes are dialled for taste.
"""
import math, random
import numpy as np
from PIL import Image


def _load(png_path):
    im = Image.open(png_path).convert("RGB")
    return np.asarray(im).astype("float32") / 255.0


def vignette(W, H, ops, strength=0.075, top_guard=0):
    """SOURCED (physics): natural lens fall-off goes as cos^4 of the angle off axis.

    v1 walked a regular 9px LATTICE and the result was a visible screen-door grid across the
    whole frame - the same failure as the beaded rim light, on a new surface. Any full-frame
    effect must be placed at RANDOM positions with varied radii, never stepped on a grid.
    v1 was also far too strong: a defect that can be seen as itself has failed. Magnitude tuned.
    """
    cx, cy = W * 0.5, H * 0.5
    maxr = math.hypot(cx, cy)
    # A low-alpha coverage wash has exactly two safe regimes: MANY TINY dabs, or FEW HUGE ones.
    # The middle - moderate radius at moderate count - clumps into visible lumps, which is what
    # v2 did (a mottled crust down both edges) and what the bokeh discs did before it.
    # Huge and faint is the cheap regime, so use that.
    n = int(W * H * 0.0016)
    for _ in range(n):
        x = random.uniform(-80, W + 80); y = random.uniform(top_guard - 40, H + 40)
        r = math.hypot(x - cx, y - cy) / maxr
        if r < 0.40: continue
        fall = ((r - 0.40) / 0.60) ** 2.3
        a = strength * fall
        if a < 0.0015: continue
        ops.append([2, x, y, 10, 11, 17, random.uniform(55, 150), round(min(0.012, a), 4)])

def shadow_noise(img, ops, top_guard=0, amount=0.038, floor=0.06):
    """SOURCED (physics): sensor read noise is roughly constant in absolute terms, so as a
    FRACTION of signal it grows as the signal falls — noise is loudest in the shadows and
    invisible in the highlights. Uniform noise over the whole frame is the wrong shape and
    reads as film grain, not as a digital photograph."""
    H, W, _ = img.shape
    lum = 0.2126*img[:,:,0] + 0.7152*img[:,:,1] + 0.0722*img[:,:,2]
    n = int(W * H * 0.0011)
    for _ in range(n):
        x = random.randrange(0, W); y = random.randrange(top_guard, H)
        v = float(lum[y, x])
        gain = (1.0 - v) ** 2.0 + floor          # loud in shadow, quiet in light
        if random.random() > gain: continue
        d = random.gauss(0, amount * gain)
        c = 200 if d > 0 else 4
        ops.append([2, x, y, c, c, c, random.uniform(0.6, 1.25),
                    round(min(0.16, abs(d) * 2.4), 4)])


def chromatic_fringe(img, ops, top_guard=0, thresh=0.14, strength=0.30):
    """SOURCED (physics): a lens focuses wavelengths at slightly different points, so a
    high-contrast edge gets a warm fringe on one side and a cool fringe on the other, growing
    with distance from the optical axis. It appears ONLY at strong edges and ONLY off-centre —
    a fringe applied everywhere reads as a filter."""
    H, W, _ = img.shape
    lum = 0.2126*img[:,:,0] + 0.7152*img[:,:,1] + 0.0722*img[:,:,2]
    gx = np.zeros_like(lum); gy = np.zeros_like(lum)
    gx[:, 1:-1] = lum[:, 2:] - lum[:, :-2]
    gy[1:-1, :] = lum[2:, :] - lum[:-2, :]
    mag = np.sqrt(gx*gx + gy*gy)
    cx, cy = W*0.5, H*0.5; maxr = math.hypot(cx, cy)
    ys, xs = np.where(mag > thresh)
    idx = list(range(len(xs)))
    random.shuffle(idx)
    for i in idx[:26000]:
        x = int(xs[i]); y = int(ys[i])
        if y < top_guard: continue
        r = math.hypot(x - cx, y - cy) / maxr
        if r < 0.22: continue                     # no fringe on the optical axis
        off = 0.6 + 1.9 * r                       # fringe widens toward the corners
        ux = (x - cx) / (maxr * max(r, 1e-6)); uy = (y - cy) / (maxr * max(r, 1e-6))
        a = min(0.34, strength * float(mag[y, x]) * r)
        ops.append([2, x + ux*off,  y + uy*off,  255, 90, 40,  1.05, round(a, 4)])
        ops.append([2, x - ux*off,  y - uy*off,  40, 110, 255, 1.05, round(a, 4)])


def focus_softness(img, ops, focal_y, W, H, top_guard=0, strength=0.16):
    """A lens has ONE plane in focus. Everything in front of and behind it is slightly soft,
    and the softness grows with distance from that plane. A render is uniformly sharp
    everywhere, which never happens optically. Magnitude tuned by eye."""
    for _ in range(int(W * H * 0.0009)):
        x = random.randrange(0, W); y = random.randrange(top_guard, H)
        d = abs(y - focal_y) / max(1.0, H * 0.5)
        if random.random() > min(1.0, d * 1.2): continue
        px = min(W-1, max(0, x + int(random.gauss(0, 1.6 + 2.2*d))))
        py = min(H-1, max(top_guard, y + int(random.gauss(0, 1.6 + 2.2*d))))
        c = img[py, px]
        ops.append([2, x, y, int(c[0]*255), int(c[1]*255), int(c[2]*255),
                    random.uniform(1.2, 2.8 + 2.0*d), round(strength * min(1.0, d), 4)])


def dust_and_flare(W, H, ops, top_guard=0, n_dust=9):
    """Sensor dust, and a faint veiling haze from light bouncing inside the lens barrel. Both
    are things a camera does to itself. Purely tuned."""
    for _ in range(n_dust):
        x = random.uniform(0, W); y = random.uniform(top_guard, H)
        r = random.uniform(2.5, 7.0)
        ops.append([2, x, y, 30, 30, 34, r, round(random.uniform(0.03, 0.07), 4)])
    # veiling glare: a broad, very faint lift, strongest where the frame is brightest
    for _ in range(1400):
        x = random.uniform(0, W); y = random.uniform(top_guard, H * 0.62)
        ops.append([2, x, y, 255, 246, 232, random.uniform(40, 130), 0.0035])


def defect_pass(png_path, W, H, top_guard=0, focal_y=None, seed=None,
                do=("vignette", "fringe", "noise", "focus", "dust")):
    """Read the finished canvas back, return the ops that make it look photographed."""
    if seed is not None: random.seed(seed)
    img = _load(png_path)
    if focal_y is None: focal_y = H * 0.62
    ops = []
    if "focus"    in do: focus_softness(img, ops, focal_y, W, H, top_guard)
    if "fringe"   in do: chromatic_fringe(img, ops, top_guard)
    if "noise"    in do: shadow_noise(img, ops, top_guard)
    if "vignette" in do: vignette(W, H, ops, top_guard=top_guard)
    if "dust"     in do: dust_and_flare(W, H, ops, top_guard)
    return ops
