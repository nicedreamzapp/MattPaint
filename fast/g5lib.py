"""GEN 5 shared machinery. Everything GEN5_RULES.md demands, in one place, so each subject is a
short script about ITS OWN light rather than a rediscovery of the same lessons.

Nothing in here draws an outline. There is no edge, rim or silhouette function, on purpose.
"""
import math, random, asyncio, time, urllib.request, os, json
from pathlib import Path
import art as A
from art import Art, mix, TOPBAR, stamp
import g3lib as G

# ---------------------------------------------------------------- value first
class Paint:
    def __init__(self, art, gray=False):
        self.a = art; self.gray = gray
    def col(self, v, hue, sat=0.62):
        v = max(0.0, min(1.0, v))
        return G.gray(v) if self.gray else G.tint(v, hue, sat)

# ---------------------------------------------------------------- safe math
def frac(v, v0, v1):
    """CLAMPED 0..1 ramp. Use this for every normalised position. Hand-dividing lets the value
    go slightly negative at a boundary, and a negative base with a fractional exponent returns
    a COMPLEX number in Python rather than raising — which then surfaces hundreds of lines away
    as a type error inside mix(). Cost this project two separate debugging detours."""
    span = v1 - v0
    if span == 0: return 0.0
    return max(0.0, min(1.0, (v - v0) / span))

def env(t, power=0.55):
    """0 at both ends, 1 in the middle — the shape almost every falloff wants. Clamped, so it
    can never hand a negative base to a fractional power."""
    return math.sin(max(0.0, min(1.0, t)) * math.pi) ** power

# ---------------------------------------------------------------- noise, never periodic
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

def fbm(x, y, oct=4, lac=2.03, gain=0.5):
    v = 0.0; amp = 1.0; norm = 0.0
    for _ in range(oct):
        v += vnoise(x, y) * amp; norm += amp
        x *= lac; y *= lac; amp *= gain
    return v / norm

def ridged(x, y, oct=3, sharp=5.0):
    """filaments, not blobs — for caustics, cracks, veins, lightning, wet reflections"""
    v = 0.0; amp = 1.0; norm = 0.0
    for _ in range(oct):
        n = vnoise(x, y)
        v += ((1.0 - abs(n * 2 - 1)) ** sharp) * amp
        norm += amp; x *= 2.07; y *= 2.07; amp *= 0.55
    return v / norm

# ---------------------------------------------------------------- the lighting model
def shade(nx, ny, to_sun, occ=0.0, ambient=0.30, bounce=0.0):
    """direct + sky fill + bounce − occlusion. Never bare N·L: a shadowed face still receives
    skylight, and a crease is dark because it is OCCLUDED, not because of its normal."""
    direct = max(0.0, nx * to_sun[0] + ny * to_sun[1])
    sky = (max(0.0, -ny) * 0.5 + 0.5) * ambient
    return max(0.0, (direct + sky + bounce) * (1.0 - occ))

def temp(lit, warm, cool, bounce_col=None, bounce=0.0):
    """colour temperature carries the light: lit runs warm, shadow runs cool from skylight"""
    c = mix(cool, warm, max(0.0, min(1.0, lit)))
    if bounce_col is not None and bounce > 0:
        c = mix(c, bounce_col, min(0.5, bounce))
    return c

# ---------------------------------------------------------------- washes: two safe regimes
def wash_tiny(art, n, xr, yr, colf, alpha=0.03, rmin=1.8, rmax=6.5):
    """MANY TINY — for washes sitting on a BRIGHT field, where a big faint dab shows itself"""
    for _ in range(n):
        x = random.uniform(*xr); y = random.uniform(*yr)
        art.D(x, y, random.uniform(rmin, rmax), colf(x, y), alpha)

def wash_huge(art, n, xr, yr, colf, alpha=0.010, rmin=60, rmax=170):
    """FEW HUGE — the cheap regime, correct over DARK ground"""
    for _ in range(n):
        x = random.uniform(*xr); y = random.uniform(*yr)
        art.D(x, y, random.uniform(rmin, rmax), colf(x, y), alpha)

# ---------------------------------------------------------------- filling a field
def fill_columns(art, x0, x1, top_of, bottom, colf, step_y=3, step_x=2.0):
    """Walk columns and fill from a top curve down. step_x must suit the SHARPEST feature in
    the field, not the average — a high-gradient feature quantises into visible bars."""
    x = x0
    while x < x1:
        yt = top_of(x)
        y = yt
        while y < bottom:
            art.R(x, y, step_x + 1, step_y + 1, colf(x, y, yt))
            y += step_y
        x += step_x

# ---------------------------------------------------------------- hierarchy, not noise
def envelope(seed, W, base_y, amp, n_mass, tiers=((4, 0.17, 0.10, 0.22, 1.6),
                                                  (3, 0.085, 0.035, 0.075, 1.4),
                                                  (3, -0.16, 0.04, 0.09, 1.5))):
    """A skyline built as geology builds one: a few enormous ASYMMETRIC masses forming an
    envelope (max, never a sum), then named smaller tiers riding on them. Negative amplitude
    tiers cut saddles DOWN into the line. High-frequency noise never touches this."""
    rnd = random.Random(seed)
    masses = []
    for i in range(n_mass):
        cx = W * (i + rnd.uniform(0.10, 0.90)) / n_mass
        steep_left = rnd.random() < 0.5
        masses.append((cx, rnd.uniform(0.62, 1.0) * amp,
                       rnd.uniform(0.16, 0.42) * W * (0.55 if steep_left else 1.0),
                       rnd.uniform(0.16, 0.42) * W * (1.0 if steep_left else 0.55)))
    extra = []
    for (n, a_lo, w_lo, w_hi, sharp) in tiers:
        for _ in range(n):
            extra.append((rnd.uniform(0, W), a_lo * amp * rnd.uniform(0.7, 1.3),
                          rnd.uniform(w_lo, w_hi) * W, sharp))
    def h(x):
        lift = 0.0
        for (cx, am, wl, wr) in masses:
            d = x - cx; w = wl if d < 0 else wr
            lift = max(lift, am * math.exp(-abs(d / w) ** 1.85))
        for (cx, am, w, sharp) in extra:
            lift += am * math.exp(-abs((x - cx) / w) ** sharp)
        return base_y - lift
    return h

# ---------------------------------------------------------------- terrain organised by water
def drainage(seed, n, W, top_of):
    rnd = random.Random(seed)
    return [dict(x0=rnd.uniform(-W*0.08, W*1.08), lean=rnd.uniform(-0.42, 0.42),
                 fan=rnd.uniform(0.020, 0.075), width=rnd.uniform(46, 150),
                 steep=rnd.uniform(0.55, 1.0), run=rnd.uniform(120, 420),
                 top=top_of(rnd.uniform(-W*0.08, W*1.08))) for _ in range(n)]

def terrain_normal(x, y, ridges, jitter=0.0):
    """Ground tilts AWAY from the nearest ridge crest into the valleys beside it, and the tilt
    dies as the ridge descends. Alternating lit/shadow planes with definite breaks."""
    best = None; bestd = 1e9
    for r in ridges:
        below = max(0.0, y - r["top"])
        axis = r["x0"] + r["lean"] * below
        half = r["width"] + r["fan"] * below * 6.0
        d = abs(x - axis) / max(12.0, half)
        if d < bestd: bestd = d; best = (r, x - axis, half, below)
    if best is None: return 0.0, -1.0
    r, off, half, below = best
    u = max(-1.6, min(1.6, off / max(12.0, half)))
    die = math.exp(-(below / r["run"]) ** 1.6)
    tilt = math.sin(u * 1.9) * math.exp(-abs(u) * 0.55) * r["steep"] * die
    nx = tilt
    ny = -math.sqrt(max(0.04, 1.0 - tilt*tilt)) * (0.55 + 0.45 * math.exp(-abs(u)))
    if jitter:
        nx += (vnoise(x*0.021, y*0.018) - 0.5) * jitter
        ny += (vnoise(x*0.024+90, y*0.020+40) - 0.5) * jitter * 0.45
    n = math.hypot(nx, ny) or 1.0
    return nx/n, ny/n

# ---------------------------------------------------------------- the runner
async def open_canvas(W, H):
    """The MattPaint window, at Matt's size, with a blank W x H canvas shown whole. -> (br, tab)"""
    from engine import Browser, launch_brave
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up:
        try:
            _w = json.loads(Path(__file__).with_name("paint_window.json").read_text())
            launch_brave(9231, pos=(_w["left"], _w["top"]), size=(_w["width"], _w["height"]))
        except Exception:
            launch_brave(9231, size=(1560, 1010))
        await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    # Matt, 2026-09-18: the paint window is ALWAYS this size and spot (paint_window.json, the one he
    # set by hand, about a third of the screen). Never full screen, never whatever size it launched at.
    prefs = Path(__file__).with_name("paint_window.json")
    try:
        want = json.loads(prefs.read_text())
        w = await br.call("Browser.getWindowForTarget", {"targetId": tab.target_id})
        if w["bounds"].get("windowState") != "normal" or any(w["bounds"][k] != v for k, v in want.items()):
            await br.call("Browser.setWindowBounds", {"windowId": w["windowId"], "bounds": {"windowState": "normal"}})
            await br.call("Browser.setWindowBounds", {"windowId": w["windowId"], "bounds": want})
            await asyncio.sleep(0.3)
    except Exception as e:
        print(f"could not place the paint window ({e})", flush=True)
    from engine import paint_url
    await tab.goto(paint_url())
    await tab.measure_canvas(); await tab.resize_canvas(W, H)
    # Matt, 2026-09-18: whatever size he drags the window to, show the WHOLE picture inside it,
    # re-zooming live on every resize (fit_canvas only fit once, so a bigger window kept a tiny picture).
    await tab.eval("""(() => {
        window.__mpFit = () => {
            const c = document.getElementById('main-canvas');
            const box = document.getElementById('canvas-container').getBoundingClientRect();
            const room = Math.min(window.innerHeight, box.bottom) - box.top;
            let z = Math.min(1, (box.width - 24) / c.width, (room - 24) / c.height);
            z = Math.max(0.1, Math.floor(z * 40) / 40);
            const s = document.getElementById('status-zoom-slider');
            if (Math.abs(s.value - z * 100) > 0.5) { s.value = z * 100; s.dispatchEvent(new Event('input', {bubbles: true})); }
        };
        if (!window.__mpFitOn) { window.__mpFitOn = 1; addEventListener('resize', () => requestAnimationFrame(window.__mpFit)); }
        window.__mpFit();
    })()""", ret=False)
    return br, tab


async def paint(art, out, meta, gray=False, defect_frac=0.02, focal_y=None):
    n = stamp(art)
    print(f"{art.title} gen5{' [FLAT GRAY]' if gray else ''}: {n:,} strokes", flush=True)
    if os.environ.get("PAINT_PREFLIGHT"):
        # 2026-09-16, local loop: build the op list and stop — no browser. Catches crashes, empty
        # paintings and runaway op counts before anything opens on Matt's screen.
        xs = [o[1] for o in art.ops]; ys = [o[2] for o in art.ops]
        json.dumps(art.ops)   # 2026-09-18: numpy numbers passed preflight, then crashed the real paint
        print(f"PREFLIGHT ops={len(art.ops)} x={min(xs, default=0):.0f}..{max(xs, default=0):.0f} "
              f"y={min(ys, default=0):.0f}..{max(ys, default=0):.0f}", flush=True)
        return
    br, tab = await open_canvas(art.W, art.H)
    tab.run_meta = dict(meta, generation=5, stage="gray" if gray else "paint")
    t0 = time.time()
    # Matt, 2026-09-18: a whole painting landed in under 3 seconds, too fast to watch it being
    # built. Spread it over ~PAINT_SECONDS (default 30) so every picture paints in front of him.
    secs = float(os.environ.get("PAINT_SECONDS", "30"))
    chunks = max(1, (len(art.ops) + 1799) // 1800)
    for i in range(0, len(art.ops), 1800):
        tab.fast(art.ops[i:i+1800]); await tab.sync(); await asyncio.sleep(max(0.04, secs / chunks))
    await tab.sync()
    # Finishing pass — bloom, colour grade, grain — Photoshop-style compositing after Robbie
    # Tilton's Compositor (https://robbietilton.com/compositor). Recipe key "finish"; off in gray.
    fin = dict(bloom=0.35, grain=0.02, contrast=0.3)
    fin.update((meta.get("recipe") or {}).get("finish") or {})
    if not gray and any(float(fin.get(k) or 0) > 0 for k in ("bloom", "grade", "grain", "contrast")):
        from art import TOPBAR as _TB
        fin["top"] = _TB + 2
        for k in ("shadows", "highlights"):
            v = fin.get(k)
            if isinstance(v, str) and v.startswith("#") and len(v) == 7:
                fin[k] = [int(v[i:i + 2], 16) for i in (1, 3, 5)]
        await tab.eval(f"window.__mpFinish && window.__mpFinish({json.dumps(fin)})", ret=False)
        await tab.sync()
    print(f"painted in {time.time()-t0:.2f}s", flush=True)
    await tab.png(out)
    if not gray and defect_frac:
        import defects as DF
        ops = DF.defect_pass(out, art.W, art.H, top_guard=TOPBAR+2,
                             focal_y=focal_y or art.H*0.7, seed=9001,
                             do=("vignette", "fringe", "noise"))[:int(n*defect_frac)]
        print(f"defects: {len(ops):,} ({100.0*len(ops)/n:.1f}%)", flush=True)
        for i in range(0, len(ops), 1800):
            tab.fast(ops[i:i+1800]); await tab.sync(); await asyncio.sleep(0.03)
        await tab.sync(); await tab.png(out)
    await br.close()
