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
STEP_DT = 0.004 if LIVE else 0.0      # pause between mouse steps
PAUSE = 0.6 if LIVE else 0.05          # "thinking" pause between stages
random.seed(7)

page = None; bb = None; stage_n = 0

async def sleep(s): await asyncio.sleep(s * (1.0 if LIVE else 0.08))

async def stage(name):
    global stage_n; stage_n += 1
    await sleep(PAUSE)
    if not LIVE:
        await page.screenshot(path=f"{OUT}/stage_{stage_n:02d}_{name}.png")

def P(nx, ny):
    return bb['x'] + nx * bb['width'], bb['y'] + ny * bb['height']

SCREEN_OFF = None
def warp(x, y):
    if LIVE and SCREEN_OFF and WARP:
        try: WARP((SCREEN_OFF[0] + x, SCREEN_OFF[1] + y))
        except Exception: pass

async def move_to(x, y, speed=1.0):
    cur = await page.evaluate("[window.__mx||0, window.__my||0]")
    x0, y0 = cur
    d = math.hypot(x - x0, y - y0)
    n = max(2, int(d / (10 * speed)))
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

async def drag(nx1, ny1, nx2, ny2, speed=1.0):
    x1, y1 = P(nx1, ny1); x2, y2 = P(nx2, ny2)
    await move_to(x1, y1, 2.0)
    await page.mouse.down()
    await move_to(x2, y2, speed)
    await page.mouse.up()
    await sleep(0.05)

async def path(points, speed=1.0):
    """freehand stroke through normalized points"""
    x, y = P(*points[0])
    await move_to(x, y, 2.0)
    await page.mouse.down()
    for nx, ny in points[1:]:
        x, y = P(nx, ny)
        await move_to(x, y, speed)
    await page.mouse.up()
    await sleep(0.03)

async def click(sel):
    el = await page.wait_for_selector(sel, state="visible", timeout=5000)
    b = await el.bounding_box()
    await move_to(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, 2.5)
    await page.mouse.down(); await asyncio.sleep(0.03); await page.mouse.up()
    await sleep(0.12)

async def set_color(target, rgb):
    await click('#color2' if target == 2 else '#color1')
    await page.wait_for_selector('#color-dialog:not(.hidden)')
    for k, v in zip(('r', 'g', 'b'), rgb):
        await page.fill(f'#color-{k}', str(v))
    await sleep(0.15)
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

async def rect(x1, y1, x2, y2, rgb):
    await fill2(rgb); await shape('rect'); await drag(x1, y1, x2, y2, 1.4)
async def tri(x1, y1, x2, y2, rgb=None):
    if rgb: await fill2(rgb)
    await shape('triangle'); await drag(x1, y1, x2, y2, 1.4)
async def oval(x1, y1, x2, y2, rgb):
    await fill2(rgb); await shape('oval'); await drag(x1, y1, x2, y2, 1.2)

async def tree(x, base, h, col=(18, 64, 32)):
    # x-units are canvas width, y-units canvas height: 0.567 keeps the proportions honest
    await rect(x - 0.004, base - h * 0.12, x + 0.004, base, (58, 36, 20))
    await fill2(col); await shape('triangle')
    for top, bot, wf in [(0.00, 0.36, 0.30), (0.20, 0.60, 0.50), (0.42, 0.82, 0.70), (0.62, 1.00, 0.90)]:
        w = 0.567 * h * 0.42 * wf
        await drag(x - w, base - h + h * top, x + w, base - h + h * bot, 1.8)

async def paint():
    global bb
    # ---- canvas to 1200x680 ----
    await click('#btn-resize')
    await page.wait_for_selector('#resize-dialog:not(.hidden)')
    await click('input[name="resize-unit"][value="pixels"]')
    if await page.is_checked('#resize-aspect'): await click('#resize-aspect')
    await page.fill('#resize-h', str(CW)); await page.fill('#resize-v', str(CH))
    await click('#resize-ok')
    await sleep(0.3)
    bb = await (await page.query_selector('#main-canvas')).bounding_box()
    await fill_mode('solid'); await outline_mode('none')
    await stage('blank')

    # ---- sky bands ----
    bands = [(0.00, 0.11, (40, 18, 78)), (0.10, 0.21, (86, 36, 112)), (0.20, 0.31, (146, 58, 124)),
             (0.30, 0.39, (204, 88, 112)), (0.38, 0.46, (238, 128, 92)), (0.45, 0.52, (250, 172, 98)),
             (0.51, 0.575, (255, 214, 140))]
    for y1, y2, col in bands:
        await rect(0.0, y1, 1.0, y2, col)
    await stage('sky')

    # soften the bands with a big watercolor brush dragged along each seam
    await brush('watercolor'); await size(8)
    seams = [(0.10, (66, 28, 96)), (0.20, (118, 48, 118)), (0.30, (176, 72, 118)),
             (0.38, (222, 108, 102)), (0.45, (245, 150, 95)), (0.51, (252, 194, 118))]
    for y, col in seams:
        await color1(col)
        for rep in range(3):
            pts = [(x, y + random.uniform(-0.016, 0.016)) for x in [i / 24 for i in range(25)]]
            if rep % 2: pts.reverse()
            await path(pts, 2.4)
    await stage('sky_blended')

    # ---- sun and glow ----
    sx, sy = 0.66, 0.29
    for rx, ry, col in [(0.095, 0.17, (250, 170, 120)), (0.068, 0.12, (255, 205, 150)), (0.045, 0.08, (255, 248, 215))]:
        await oval(sx - rx, sy - ry, sx + rx, sy + ry, col)
    await stage('sun')

    # ---- clouds ----
    await brush('watercolor'); await size(8)
    clouds = [((236, 168, 204), 0.09, 0.36, 0.165), ((236, 168, 204), 0.56, 0.98, 0.20),
              ((250, 150, 140), 0.26, 0.50, 0.275), ((250, 150, 140), 0.74, 1.0, 0.31), ((246, 190, 150), 0.02, 0.22, 0.34)]
    for col, xa, xb, y in clouds:
        await color1(col)
        L = xb - xa
        for k, (frac, dy) in enumerate([(1.0, 0.0), (0.72, -0.018), (0.45, -0.034)]):
            cx = xa + L * (0.5 + random.uniform(-0.08, 0.08)); half = L * frac / 2
            pts = [(cx - half + (2 * half) * i / 20, y + dy + random.uniform(-0.004, 0.004)) for i in range(21)]
            await path(pts, 1.8); await path(pts[::-1], 1.8)
    await stage('clouds')

    # ---- far mountains ----
    far = (112, 84, 140)
    await fill2(far)
    for x1, yp, x2 in [(0.005, 0.30, 0.34), (0.22, 0.235, 0.58), (0.50, 0.36, 0.82), (0.72, 0.265, 0.995)]:
        await tri(x1, yp, x2, 0.575)
    # snow caps on the far peaks
    await fill2((246, 242, 252))
    for x1, yp, x2 in [(0.005, 0.30, 0.34), (0.22, 0.235, 0.58), (0.50, 0.36, 0.82), (0.72, 0.265, 0.995)]:
        cx = (x1 + x2) / 2; hw = (x2 - x1) * 0.5
        await tri(cx - hw * 0.19, yp, cx + hw * 0.19, yp + 0.055)
    await stage('far_mountains')

    # ---- near mountains (darker, lower) ----
    near = (70, 50, 100)
    await fill2(near)
    for x1, yp, x2 in [(0.005, 0.41, 0.30), (0.17, 0.355, 0.52), (0.40, 0.43, 0.68), (0.58, 0.375, 0.90), (0.80, 0.44, 0.995)]:
        await tri(x1, yp, x2, 0.58)
    await fill2((238, 232, 250))
    for x1, yp, x2 in [(0.17, 0.355, 0.52), (0.58, 0.375, 0.90)]:
        cx = (x1 + x2) / 2; hw = (x2 - x1) * 0.5
        await tri(cx - hw * 0.14, yp, cx + hw * 0.14, yp + 0.04)
    await stage('near_mountains')

    # ---- lake ----
    await rect(0.0, 0.565, 1.0, 0.87, (34, 48, 112))
    # sky reflection bands, soft
    await brush('watercolor'); await size(8)
    for y, col in [(0.60, (150, 90, 130)), (0.64, (200, 120, 110)), (0.69, (110, 80, 130)), (0.75, (60, 60, 120))]:
        await color1(col)
        pts = [(x, y + random.uniform(-0.004, 0.004)) for x in [i / 30 for i in range(31)]]
        await path(pts, 2.4)
    # ripples
    await brush('watercolor'); await size(3); await color1((160, 140, 200))
    for i in range(12):
        y = 0.60 + i * 0.02; xa = random.uniform(0.04, 0.55); L = random.uniform(0.05, 0.18)
        await path([(xa, y), (xa + L, y + random.uniform(-0.002, 0.002))], 3.0)
    # the sun's light on the water, soft
    await brush('watercolor'); await size(8); await color1((255, 205, 150))
    for rep in range(2):
        pts = [(0.66 + 0.01 * math.sin(y * 70 + rep), y) for y in [0.575 + i * 0.012 for i in range(22)]]
        await path(pts if rep == 0 else pts[::-1], 1.6)
    await size(3); await color1((255, 235, 190))
    for i in range(5):
        y = 0.60 + i * 0.035; hw = 0.035 - i * 0.005
        await path([(0.66 - hw, y), (0.66 + hw, y)], 2.5)
    await stage('lake')

    # ---- banks and ground ----
    await rect(0.998, 0.865, 0.0, 1.0, (24, 46, 28))
    await oval(0.36, 0.70, 0.0, 1.0, (30, 60, 32))
    await oval(0.998, 0.78, 0.54, 0.999, (30, 60, 32))
    await stage('ground')

    # ---- cabin on the right bank ----
    await rect(0.60, 0.815, 0.705, 0.885, (96, 60, 34))
    await tri(0.585, 0.755, 0.72, 0.82, (58, 34, 22))
    await rect(0.685, 0.762, 0.697, 0.79, (70, 44, 30))
    await rect(0.632, 0.838, 0.655, 0.858, (255, 214, 110))
    await rect(0.672, 0.845, 0.690, 0.885, (44, 26, 16))
    # smoke
    await brush('airbrush'); await size(5); await color1((225, 220, 235))
    await path([(0.691, 0.755), (0.70, 0.73), (0.712, 0.71), (0.70, 0.69), (0.715, 0.665)], 1.2)
    await stage('cabin')

    # ---- happy little trees ----
    greens = [(18, 64, 32), (30, 92, 44), (24, 78, 38)]
    for i, (x, base, h) in enumerate([(0.05, 0.90, 0.26), (0.11, 0.96, 0.34), (0.19, 0.93, 0.30), (0.27, 0.985, 0.36), (0.335, 0.95, 0.24),
                                       (0.78, 0.93, 0.24), (0.86, 0.985, 0.36), (0.93, 0.95, 0.30), (0.985, 0.975, 0.26)]):
        await tree(x, base, h, greens[i % 3])
    await stage('trees')

    # ---- birds and the signature ----
    await brush('brush'); await size(1); await color1((40, 20, 50))
    for cx, cy, s in [(0.40, 0.22, 0.012), (0.43, 0.20, 0.010), (0.455, 0.235, 0.008)]:
        await path([(cx - s, cy), (cx, cy + s * 0.9), (cx + s, cy)], 2.5)
    await color1((255, 255, 255))
    await click('#tool-text')
    await drag(0.845, 0.925, 0.995, 0.985, 2.0)
    await page.keyboard.type("claude '26", delay=90 if LIVE else 5)
    await page.mouse.click(*P(0.5, 0.3))
    await sleep(0.3)
    await stage('done')
    await page.screenshot(path=f"{OUT}/final_{MODE}.png")

async def main():
    global page
    async with async_playwright() as p:
        if LIVE:
            browser = await p.chromium.launch(executable_path=BRAVE, headless=False,
                args=[f"--window-size={VW},{VH+90}", "--window-position=900,120", "--no-first-run", "--disable-features=Translate"])
            ctx = await browser.new_context(viewport={"width": VW, "height": VH},
                record_video_dir=f"{OUT}/video", record_video_size={"width": VW, "height": VH})
        else:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            ctx = browser.contexts[0]
        page = await ctx.new_page()
        if not LIVE: await page.set_viewport_size({"width": VW, "height": VH})
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
            v = page.video
            await page.close(); await ctx.close()
            print("video:", await v.path())
            await browser.close()
        else:
            await page.close()
asyncio.run(main())
