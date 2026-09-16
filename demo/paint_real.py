"""Claude paints a Bob Ross mountain lake in MattPaint through the real browser UI.
usage: python3 paint_bob.py dry   -> fast rehearsal in a hidden broker tab, screenshots per stage
       python3 paint_bob.py live  -> visible Brave window on screen, human-speed, video recorded
"""
import asyncio, sys, time, math, random, os
from playwright.async_api import async_playwright
try:
    from Quartz import CGWarpMouseCursorPosition as WARP
except Exception:
    WARP = None

MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
LIVE = MODE == "live"
URL = "https://nicedreamzwholesale.com/paint/?r=" + str(int(time.time()))
BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
OUT = os.path.dirname(os.path.abspath(__file__))
VW, VH = 1600, 900
CW, CH = 1200, 680
STEP_DT = 0.0
FRAME = 0.02 if LIVE else 0.0   # a visible window commits input on the next frame      # pause between mouse steps
PAUSE = 0.05          # "thinking" pause between stages
random.seed(7)

page = None; bb = None; stage_n = 0

async def sleep(s): await asyncio.sleep(s * 0.08)

T0 = time.time()
async def stage(name):
    global stage_n; stage_n += 1
    print(f"{time.time()-T0:6.1f}s  {name}", flush=True)
    await sleep(PAUSE)
    if not LIVE:
        await page.screenshot(path=f"{OUT}/stage_{stage_n:02d}_{name}.png")

def P(nx, ny):
    nx = max(0.002, min(0.998, nx)); ny = max(0.002, min(0.998, ny))
    return bb['x'] + nx * bb['width'], bb['y'] + ny * bb['height']

SCREEN_OFF = None
def warp(x, y):
    if LIVE and SCREEN_OFF and WARP:
        try: WARP((SCREEN_OFF[0] + x, SCREEN_OFF[1] + y))
        except Exception: pass

async def move_to(x, y, speed=1.0, base=18):
    cur = await page.evaluate("[window.__mx||0, window.__my||0]")
    x0, y0 = cur
    d = math.hypot(x - x0, y - y0)
    n = max(2, int(d / (base * speed)))
    for i in range(1, n + 1):
        t = i / n
        # ease in-out so it looks like a hand, plus a whisper of jitter
        e = t * t * (3 - 2 * t)
        jx = random.uniform(-0.6, 0.6) if 0 < i < n else 0
        jy = random.uniform(-0.6, 0.6) if 0 < i < n else 0
        px, py = x0 + (x - x0) * e + jx, y0 + (y - y0) * e + jy
        await page.mouse.move(px, py); warp(px, py)
        if STEP_DT: await asyncio.sleep(STEP_DT)
    await page.evaluate(f"window.__mx={x};window.__my={y}")

PROBE_ON = False
_last_ops = []
async def probe(desc):
    global PROBE_ON
    _last_ops.append(desc); del _last_ops[:-6]
    if not PROBE_ON: return
    px = await page.evaluate("(() => { const c = document.getElementById('main-canvas'); const d = c.getContext('2d').getImageData(Math.floor(c.width*0.12), Math.floor(c.height*0.75), 1, 1).data; return [d[0], d[1], d[2]]; })()")
    if px != [255, 255, 255]:
        print("PROBE HIT", px, "after:", _last_ops, flush=True)
        PROBE_ON = False

async def drag(nx1, ny1, nx2, ny2, speed=1.0):
    x1, y1 = P(nx1, ny1); x2, y2 = P(nx2, ny2)
    await move_to(x1, y1, 2.0, 40)
    await page.mouse.down(); await asyncio.sleep(FRAME)
    await move_to(x2, y2, speed, 40)
    await asyncio.sleep(FRAME); await page.mouse.up()
    await sleep(0.03)
    await probe(f"drag {nx1:.3f},{ny1:.3f} -> {nx2:.3f},{ny2:.3f}")

async def path(points, speed=1.0):
    """freehand stroke through normalized points"""
    x, y = P(*points[0])
    await move_to(x, y, 2.0, 40)
    await page.mouse.down(); await asyncio.sleep(FRAME)
    for nx, ny in points[1:]:
        x, y = P(nx, ny)
        await move_to(x, y, speed, 7)
    await asyncio.sleep(FRAME); await page.mouse.up()
    await sleep(0.02)
    await probe(f"path {points[0][0]:.3f},{points[0][1]:.3f}.. n={len(points)}")

async def click(sel):
    el = await page.wait_for_selector(sel, state="visible", timeout=5000)
    b = await el.bounding_box()
    await move_to(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, 2.5)
    await asyncio.sleep(FRAME); await page.mouse.down(); await asyncio.sleep(FRAME); await page.mouse.up()
    await sleep(0.04)

PALETTE = ['#000000', '#7F7F7F', '#880015', '#ED1C24', '#FF7F27', '#FFF200', '#22B14C', '#00A2E8', '#3F48CC', '#A349A4',
           '#FFFFFF', '#C3C3C3', '#B97A57', '#FFAEC9', '#FFC90E', '#EFE4B0', '#B5E61D', '#99D9EA', '#7092BE', '#C8BFE7',
           '#404040', '#808080', '#993300', '#CC6600', '#FFCC00', '#99CC00', '#009999', '#0066CC', '#663399', '#CC3399']
PAL_RGB = [tuple(int(h[i:i+2], 16) for i in (1, 3, 5)) for h in PALETTE]
_cur = {1: None, 2: None}

async def set_color(target, rgb):
    rgb = tuple(int(v) for v in rgb)
    if _cur[target] == rgb: return
    _cur[target] = rgb
    # a palette swatch is one click; the dialog is five actions. Use the swatch when it is close enough.
    best = min(range(len(PAL_RGB)), key=lambda i: sum((PAL_RGB[i][k] - rgb[k]) ** 2 for k in range(3)))
    if target == 1 and sum((PAL_RGB[best][k] - rgb[k]) ** 2 for k in range(3)) < 18 ** 2:
        sw = await page.query_selector_all('#color-palette .color-swatch')
        b = await sw[best].bounding_box()
        await move_to(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, 2.5)
        if target == 1: await page.mouse.down(); await page.mouse.up()
        else: await page.mouse.down(button='right'); await page.mouse.up(button='right')
        await sleep(0.04); return
    await click('#color2' if target == 2 else '#color1')
    await page.wait_for_selector('#color-dialog:not(.hidden)')
    for k, v in zip(('r', 'g', 'b'), rgb):
        await page.fill(f'#color-{k}', str(v))
    await click('#color-ok')

async def fill2(rgb): await set_color(2, rgb)
async def color1(rgb): await set_color(1, rgb)

async def shape(name): await click(f'[data-shape="{name}"]')
async def brush(kind):
    await click('#btn-brushes'); await click(f'[data-brush="{kind}"]')
async def size(n):
    await click('#btn-size'); await click(f'[data-size="{n}"]')
async def fill_mode(mode):
    await click('#btn-fill'); await click(f'[data-fill="{mode}"]')
async def outline_mode(mode):
    await click('#btn-outline'); await click(f'[data-outline="{mode}"]')


async def rect(x1, y1, x2, y2, rgb=None, speed=1.4):
    if rgb: await fill2(rgb)
    await shape('rect'); await drag(x1, y1, x2, y2, speed)
async def oval(x1, y1, x2, y2, rgb=None, speed=1.2):
    if rgb: await fill2(rgb)
    await shape('oval'); await drag(x1, y1, x2, y2, speed)

async def tri(x1, y1, x2, y2, rgb=None, speed=1.4):
    if rgb: await fill2(rgb)
    await shape('triangle'); await drag(x1, y1, x2, y2, speed)

def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))
def clamp(v, lo=0, hi=255): return max(lo, min(hi, int(v)))
def shade(c, k): return tuple(clamp(v * k) for v in c)

HORIZON = 0.58
SUN_X, SUN_Y = 0.66, 0.30

def ridge_factory(peaks, noise_amp, seed):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    def ridge(x):
        y = HORIZON
        for px, py, sl, sr in peaks:
            yy = py + ((px - x) * sl if x < px else (x - px) * sr)
            y = min(y, yy)
        n = (math.sin(x * 43 + ph[0]) * 0.55 + math.sin(x * 101 + ph[1]) * 0.3 + math.sin(x * 233 + ph[2]) * 0.15) * noise_amp
        return min(HORIZON, y + n)
    return ridge

async def mountain_range(ridge, base_col, lit_col, dark_col, snow_line, snow_col, step=0.005, x0=0.0, x1=0.998, haze=None):
    """silhouette in thin strokes toned by which way the whole face looks; then rock lines, snow, haze"""
    cols = []
    x = x0
    while x < x1:
        y = ridge(x)
        if y < HORIZON - 0.002:
            dy = ridge(min(x1, x + 0.05)) - ridge(max(x0, x - 0.05))     # smoothed slope = whole face
            facing = -dy if x < SUN_X else dy
            t = max(-1.0, min(1.0, facing / 0.09))
            level = round(t * 2) / 2.0                                    # five tones
            q = mix(base_col, lit_col, level) if level > 0 else mix(base_col, dark_col, -level)
            cols.append((x, y, q))
        x += step
    groups = {}
    for x, y, q in cols: groups.setdefault(q, []).append((x, y))
    for q in sorted(groups, key=lambda c: sum(c)):
        await fill2(q); await shape('rect')
        for x, y in groups[q]:
            await drag(x, y, min(0.998, x + step * 1.4), HORIZON + 0.004, 6.0)
    # snow: capped columns with a gullied lower edge, then a few streaks running down
    caps = [(x, y) for x, y, q in cols if y < snow_line - 0.006]
    if caps:
        await fill2(snow_col); await shape('rect')
        for x, y in caps:
            depth = (snow_line - y) * 0.85 + 0.012 * abs(math.sin(x * 260)) + 0.004
            await drag(x, y, min(0.998, x + step * 1.4), y + depth, 6.0)
        await brush('marker'); await size(1); await color1(snow_col)
        for x, y in caps[::3]:
            d0 = (snow_line - y) * 0.85 + 0.01
            await path([(x, y + d0), (x + random.uniform(-0.004, 0.004), y + d0 + random.uniform(0.006, 0.014))], 4.0)
    if haze:
        await brush('watercolor'); await size(8); await color1(haze)
        for y in (HORIZON - 0.03, HORIZON - 0.075):
            pts = [(xx, y + random.uniform(-0.01, 0.01)) for xx in [i / 20 for i in range(21)]]
            await path(pts, 3.0)

async def evergreen(x, base, h, dark, light, size_px):
    await brush('brush'); await size(size_px)
    await color1((48, 30, 16))
    await path([(x, base - h * 0.92), (x, base)], 2.5)
    lit_left = x > SUN_X
    n = 9
    await color1(dark)
    strokes = []
    for i in range(1, n + 1):
        y = base - h + h * i / n
        hw = 0.567 * h * 0.36 * (i / n) * random.uniform(0.85, 1.05)
        strokes.append(((x, y - h * 0.035), (x - hw, y + h * 0.045)))
        strokes.append(((x, y - h * 0.035), (x + hw, y + h * 0.045)))
    for a, b in strokes: await path([a, b], 2.4)
    await color1(light)
    for i in range(1, n + 1):
        y = base - h + h * i / n
        hw = 0.567 * h * 0.36 * (i / n) * 0.6
        a = (x, y - h * 0.03)
        b = (x - hw, y + h * 0.02) if lit_left else (x + hw, y + h * 0.02)
        await path([a, b], 2.4)

async def paint():
    global bb
    await click('#btn-resize')
    await page.wait_for_selector('#resize-dialog:not(.hidden)')
    await click('input[name="resize-unit"][value="pixels"]')
    if await page.is_checked('#resize-aspect'): await click('#resize-aspect')
    await page.fill('#resize-h', str(CW)); await page.fill('#resize-v', str(CH))
    await click('#resize-ok'); await sleep(0.3)
    bb = await (await page.query_selector('#main-canvas')).bounding_box()
    await fill_mode('solid'); await outline_mode('none')
    await stage('blank')

    # ---- sky: smooth gradient from 34 bands ----
    keys = [(0.00, (28, 12, 70)), (0.16, (96, 34, 122)), (0.30, (178, 60, 120)), (0.40, (236, 104, 92)),
            (0.48, (252, 158, 82)), (0.55, (255, 210, 120)), (HORIZON, (255, 236, 170))]
    def sky_at(y):
        for (ya, ca), (yb, cb) in zip(keys, keys[1:]):
            if ya <= y <= yb: return mix(ca, cb, (y - ya) / (yb - ya))
        return keys[-1][1]
    nb = 22
    for i in range(nb):
        y1 = HORIZON * i / nb; y2 = HORIZON * (i + 1) / nb + 0.004
        await rect(0.0, y1, 0.999, min(HORIZON, y2), sky_at((y1 + y2) / 2), 3.0)
    await brush('watercolor'); await size(8)
    for i in range(1, nb):
        y = HORIZON * i / nb
        await color1(sky_at(y))
        pts = [(x, y + random.uniform(-0.01, 0.01)) for x in [j / 16 for j in range(17)]]
        await path(pts if i % 2 else pts[::-1], 3.0)
    await stage('sky')

    # ---- sun: brushed halo, then the disc ----
    core = (255, 252, 228)
    await brush('watercolor'); await size(8)
    for r, col in [(0.085, (255, 190, 130)), (0.07, (255, 205, 145)), (0.058, (255, 222, 165)), (0.049, (255, 238, 190))]:
        await color1(col)
        for rep in range(2):
            pts = [(SUN_X + r * math.cos(a), SUN_Y + r * 1.76 * math.sin(a)) for a in [i * 2 * math.pi / 28 for i in range(29)]]
            await path(pts if rep == 0 else pts[::-1], 2.2)
    await oval(SUN_X - 0.05, SUN_Y - 0.05 * 1.76, SUN_X + 0.05, SUN_Y + 0.05 * 1.76, (255, 236, 190), 2.0)
    await oval(SUN_X - 0.041, SUN_Y - 0.041 * 1.76, SUN_X + 0.041, SUN_Y + 0.041 * 1.76, core, 2.0)
    await stage('sun')

    # ---- clouds: three tones each ----
    await brush('watercolor'); await size(8)
    clouds = [(0.04, 0.34, 0.15), (0.50, 0.94, 0.19), (0.24, 0.46, 0.265), (0.72, 0.99, 0.30), (0.00, 0.20, 0.36)]
    tones = [((150, 70, 130), 1.0, 0.012), ((222, 130, 170), 0.85, -0.004), ((255, 200, 215), 0.55, -0.022)]
    for xa, xb, y in clouds:
        L = xb - xa
        for col, frac, dy in tones:
            await color1(mix(col, sky_at(y), 0.25))
            for k in range(2):
                cx = xa + L * (0.5 + random.uniform(-0.1, 0.1)); half = L * frac / 2 * random.uniform(0.85, 1.0)
                pts = [(cx - half + (2 * half) * i / 18, y + dy + random.uniform(-0.005, 0.005)) for i in range(19)]
                await path(pts if k == 0 else pts[::-1], 2.0)
    await stage('clouds')

    # ---- mountains: far range (hazy), near range (bold) ----
    far = ridge_factory([(0.12, 0.30, 0.9, 0.7), (0.40, 0.235, 0.85, 0.75), (0.66, 0.33, 0.8, 0.9), (0.88, 0.25, 0.75, 1.0)], 0.014, 3)
    await mountain_range(far, (150, 108, 168), (214, 160, 196), (96, 64, 126), 0.315, (252, 240, 250), haze=(232, 150, 150))
    await stage('far_mountains')
    near = ridge_factory([(0.0, 0.42, 0.9, 0.6), (0.30, 0.36, 0.75, 0.7), (0.53, 0.45, 0.8, 0.8), (0.76, 0.385, 0.7, 0.75), (0.97, 0.43, 0.9, 0.8)], 0.012, 11)
    await mountain_range(near, (72, 50, 108), (128, 92, 150), (30, 18, 56), 0.40, (240, 234, 252))
    await stage('near_mountains')

    global PROBE_ON; PROBE_ON = False
    # ---- lake: the sky upside down, then the peaks, then ripples ----
    LAKE_BOT = 0.87
    water = (26, 40, 104)
    nb = 14
    for i in range(nb):
        y1 = HORIZON + (LAKE_BOT - HORIZON) * i / nb; y2 = HORIZON + (LAKE_BOT - HORIZON) * (i + 1) / nb + 0.004
        sky_y = HORIZON - (y1 - HORIZON) * 1.4
        col = mix(sky_at(max(0.0, sky_y)), water, 0.5 + 0.4 * (i / nb))
        await rect(0.0, y1, 0.999, min(LAKE_BOT, y2), col, 3.0)
    await brush('watercolor'); await size(5)
    for i in range(1, nb):
        y = HORIZON + (LAKE_BOT - HORIZON) * i / nb
        await color1(mix(sky_at(max(0.0, HORIZON - (y - HORIZON) * 1.4)), water, 0.5 + 0.4 * (i / nb)))
        pts = [(x, y + random.uniform(-0.006, 0.006)) for x in [j / 16 for j in range(17)]]
        await path(pts if i % 2 else pts[::-1], 3.0)
    # mountain reflection (near range, squashed, darker, bluer)
    cols = []
    x = 0.0
    while x < 0.998:
        y = near(x)
        if y < HORIZON - 0.004: cols.append((x, HORIZON + (HORIZON - y) * 0.55))
        x += 0.01
    await fill2((40, 30, 84)); await shape('rect')
    for x, yb in cols:
        await drag(x, HORIZON, min(0.998, x + 0.013), yb, 6.0)
    await brush('watercolor'); await size(3); await color1((40, 30, 84))
    await path([(x / 16, HORIZON + 0.004) for x in range(17)], 3.0)
    await size(5); await color1((70, 60, 120))
    for y in (HORIZON + 0.03, HORIZON + 0.07):
        pts = [(xx, y + random.uniform(-0.006, 0.006)) for xx in [i / 16 for i in range(17)]]
        await path(pts, 3.0)
    # the sun's light on the water: a soft column, then a few bright glints
    await brush('watercolor'); await size(3); await color1((255, 215, 150))
    for rep in range(3):
        pts = [(SUN_X + random.uniform(-0.008, 0.008), y) for y in [HORIZON + 0.005 + i * 0.012 for i in range(20)]]
        await path(pts if rep % 2 == 0 else pts[::-1], 2.5)
    await brush('brush'); await size(1); await color1((255, 245, 205))
    for i in range(6):
        y = HORIZON + 0.02 + i * 0.03; hw = 0.03 - i * 0.003
        await path([(SUN_X - hw + random.uniform(-0.01, 0.01), y), (SUN_X + hw + random.uniform(-0.01, 0.01), y)], 4.0)
    # ripples
    await brush('marker'); await size(1)
    for i in range(18):
        y = HORIZON + 0.02 + random.uniform(0, LAKE_BOT - HORIZON - 0.04)
        await color1(mix(sky_at(max(0.0, HORIZON - (y - HORIZON) * 1.4)), (200, 200, 240), 0.3))
        xa = random.uniform(0.0, 0.85); L = random.uniform(0.03, 0.12)
        await path([(xa, y), (xa + L, y)], 4.0)
    await stage('lake')

    # ---- shore and meadow ----
    await rect(0.998, LAKE_BOT - 0.005, 0.0, 0.999, (22, 44, 26), 3.0)
    await oval(0.40, 0.72, 0.0, 0.999, (28, 58, 32), 2.0)
    await oval(0.998, 0.80, 0.56, 0.999, (28, 58, 32), 2.0)
    await brush('brush'); await size(1)
    for col in ((40, 84, 40), (66, 122, 52), (96, 150, 60)):
        await color1(col)
        for i in range(22):
            x = random.uniform(0.0, 0.999); y = random.uniform(0.885, 0.995)
            await path([(x, y), (x + random.uniform(-0.004, 0.004), y - random.uniform(0.012, 0.03))], 3.0)
    await stage('ground')

    # ---- cabin ----
    await rect(0.60, 0.815, 0.705, 0.885, (92, 58, 32))
    await rect(0.60, 0.815, 0.705, 0.828, (120, 78, 44))
    await tri(0.585, 0.752, 0.72, 0.82, (56, 32, 20))
    await rect(0.685, 0.760, 0.697, 0.792, (70, 44, 30))
    await rect(0.632, 0.838, 0.655, 0.858, (255, 214, 110))
    await rect(0.672, 0.845, 0.690, 0.885, (40, 24, 14))
    await brush('airbrush'); await size(5); await color1((225, 220, 235))
    await path([(0.691, 0.755), (0.70, 0.73), (0.712, 0.71), (0.70, 0.69), (0.715, 0.665)], 1.2)
    await stage('cabin')

    # ---- evergreens, painted branch by branch ----
    trees = [(0.045, 0.90, 0.24, 3), (0.11, 0.965, 0.34, 5), (0.19, 0.925, 0.29, 5), (0.27, 0.985, 0.37, 5), (0.34, 0.95, 0.23, 3),
             (0.78, 0.93, 0.25, 3), (0.86, 0.985, 0.37, 5), (0.93, 0.95, 0.30, 5), (0.985, 0.975, 0.26, 3)]
    for x, base, h, sz in trees:
        await evergreen(x, base, h, (12, 50, 26), (52, 124, 58), sz)
    await stage('trees')

    # ---- birds, signature ----
    await brush('brush'); await size(1); await color1((40, 20, 50))
    for cx, cy, s in [(0.30, 0.20, 0.012), (0.33, 0.18, 0.010), (0.355, 0.215, 0.008)]:
        await path([(cx - s, cy), (cx, cy + s * 0.9), (cx + s, cy)], 2.5)
    await color1((255, 255, 255))
    await click('#tool-text')
    await drag(0.845, 0.93, 0.995, 0.985, 2.0)
    await page.keyboard.type("claude '26", delay=90 if LIVE else 5)
    await page.mouse.click(*P(0.5, 0.3))
    await sleep(0.3)
    await stage('done')
    await page.screenshot(path=f"{OUT}/final_{MODE}.png")

async def main():
    global page
    async with async_playwright() as p:
        if LIVE:
            import subprocess, tempfile, urllib.request
            prof = tempfile.mkdtemp(prefix="mattpaint-live-")
            proc = subprocess.Popen([BRAVE, "--remote-debugging-port=9231", f"--user-data-dir={prof}", "--no-first-run",
                                     "--no-default-browser-check", "--disable-features=Translate",
                                     f"--window-size={VW},{VH+87}", "--window-position=900,120", "about:blank"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(60):
                try:
                    urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); break
                except Exception: await asyncio.sleep(0.5)
            browser = await p.chromium.connect_over_cdp("http://localhost:9231")
            ctx = browser.contexts[0]
        else:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            ctx = browser.contexts[0]
        page = await ctx.new_page()
        if LIVE:
            for pg in ctx.pages:
                if pg is not page: await pg.close()
        else:
            await page.set_viewport_size({"width": VW, "height": VH})
        await page.goto(URL); await page.wait_for_selector('#main-canvas'); await sleep(1.0)
        await page.evaluate("window.__mx=800;window.__my=450")
        if LIVE:
            global SCREEN_OFF
            SCREEN_OFF = tuple(await page.evaluate("[window.screenX, window.screenY + (window.outerHeight - window.innerHeight)]"))
            print("page screen offset", SCREEN_OFF, flush=True)
        t0 = time.time()
        await paint()
        print(f"painted in {time.time()-t0:.0f}s")
        await sleep(2.0)
        if LIVE:
            print("done; window stays open", flush=True)
        else:
            await page.close()
asyncio.run(main())
