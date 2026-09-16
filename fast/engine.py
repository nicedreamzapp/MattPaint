"""fastpaint engine: drives MattPaint through raw Chrome DevTools Protocol.

Two ways to move the mouse:
  input  - Input.dispatchMouseEvent over the debug socket, pipelined (no waiting for replies).
           Real browser input pipeline. Visible windows need --disable-frame-rate-limit or they
           take one movement per frame.
  replay - one Runtime.evaluate per stroke; the page dispatches the MouseEvents itself.
           One round trip per stroke regardless of how many points.
Counts every movement so the run can report movements per second.
"""
import asyncio, json, time, subprocess, tempfile, urllib.request, os, sys, re
import websockets

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

TOOL_KEYS = {'pencil': 'p', 'brush': 'b', 'eraser': 'e', 'fill': 'g', 'text': 't', 'picker': 'i', 'select': 's'}


CONTROL_JS = r"""
window.__fpc = window.__fpc || {
  click(sel) { const e = document.querySelector(sel); if (e) { e.click(); return true; } return false; },
  setColor(target, r, g, b) {
    document.getElementById(target === 1 ? 'color1' : 'color2').click();   // openColorPicker(target)
    document.getElementById('color-r').value = r;
    document.getElementById('color-g').value = g;
    document.getElementById('color-b').value = b;
    document.getElementById('color-ok').click();
  },
  resize(w, h) {
    document.getElementById('btn-resize').click();
    const px = document.querySelector('input[name="resize-unit"][value="pixels"]'); if (px) px.click();
    const asp = document.getElementById('resize-aspect'); if (asp && asp.checked) asp.click();
    document.getElementById('resize-h').value = w;
    document.getElementById('resize-v').value = h;
    document.getElementById('resize-ok').click();
  }
};
"""

REPLAY_JS = r"""
window.__fp = window.__fp || (() => {
  const c = document.getElementById('main-canvas');
  function ev(type, x, y, button, buttons) {
    const r = c.getBoundingClientRect();
    const k = c.width ? r.width / c.width : 1;     // canvas shown zoomed (fit to screen): scale px to screen
    return new MouseEvent(type, {bubbles: true, cancelable: true, clientX: r.left + x * k, clientY: r.top + y * k,
                                 button: button, buttons: buttons});
  }
  return {
    stroke(pts, button) {           // pts in canvas px
      const btn = button || 0, bmask = btn === 2 ? 2 : 1;
      c.dispatchEvent(ev('mousedown', pts[0][0], pts[0][1], btn, bmask));
      for (let i = 1; i < pts.length; i++) c.dispatchEvent(ev('mousemove', pts[i][0], pts[i][1], btn, bmask));
      const l = pts[pts.length - 1];
      c.dispatchEvent(ev('mouseup', l[0], l[1], btn, 0));
      return pts.length + 1;
    },
    batch(list, button) {           // list = [[[x,y],...], ...] ; all in one call
      const btn = button || 0, bmask = btn === 2 ? 2 : 1;
      for (const pts of list) {
        c.dispatchEvent(ev('mousedown', pts[0][0], pts[0][1], btn, bmask));
        for (let i = 1; i < pts.length; i++) c.dispatchEvent(ev('mousemove', pts[i][0], pts[i][1], btn, bmask));
        const l = pts[pts.length - 1];
        c.dispatchEvent(ev('mouseup', l[0], l[1], btn, 0));
      }
      return list.length;
    },
    png() { return c.toDataURL('image/png'); }
  };
})();
"""

# Matt's standing rule: every painting run must be WATCHABLE. Not headless, not off-screen,
# not minimised. This is enforced here rather than left to each script, because a per-script
# flag is exactly the thing that quietly flips back.
BANNED_FLAGS = ("--headless", "--window-position=-", "--start-minimized", "--disable-gpu-compositing")

def _no_browser_in_preflight():
    # 2026-09-16: a script that paints through its own runner instead of G5.paint() would reach
    # the browser during a "no browser" preflight and paint on Matt's screen. Refuse here, where
    # every path to the browser passes.
    if os.environ.get("PAINT_PREFLIGHT"):
        raise SystemExit("PREFLIGHT: this script paints directly instead of calling "
                         "G5.paint(a, OUT, ...) — use G5.paint so it can be checked without a browser.")

def screen_size():
    """main screen in points (what window positions use), e.g. 1728x1117 on the MacBook, or None.
    system_profiler needs no Automation permission (asking Finder hangs over ssh on the mini)."""
    try:
        out = subprocess.run(["system_profiler", "SPDisplaysDataType"], capture_output=True,
                             text=True, timeout=15).stdout
    except Exception:
        return None
    for block in re.split(r"\n(?=\s{8}\S[^\n]*:\n)", out):
        if "Main Display: Yes" not in block:
            continue
        m = re.search(r"UI Looks like: (\d+) x (\d+)", block)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.search(r"Resolution: (\d+) x (\d+)( Retina)?", block)
        if m:
            k = 2 if m.group(3) else 1
            return int(m.group(1)) // k, int(m.group(2)) // k
    return None

def launch_brave(port, pos=(900, 120), size=(1600, 987), extra=()):
    _no_browser_in_preflight()
    for f in extra:
        for bad in BANNED_FLAGS:
            if str(f).startswith(bad):
                raise RuntimeError(f"refused: {f} would hide the run. Painting must stay on screen.")
    if pos[0] < 0 or pos[1] < 0:
        raise RuntimeError(f"refused: window position {pos} is off screen. Painting must stay on screen.")
    # 2026-09-16: pos (900,120) was tuned on the mini's 3440-wide display. On the MacBook's
    # 1728x1117 screen it put ~70% of the window past the right edge, so paintings ran mostly
    # out of view. Fit the window to THIS screen, and refuse if it still cannot fit.
    scr = screen_size()
    if scr is None:   # unknown screen: keep the caller's geometry rather than guess smaller
        scr = (pos[0] + size[0], pos[1] + size[1])
    sw, sh = scr
    size = (min(size[0], sw), min(size[1], sh - 25))
    pos = (max(0, min(pos[0], sw - size[0])), max(25, min(pos[1], sh - size[1])))
    if pos[0] + size[0] > sw or pos[1] + size[1] > sh:
        raise RuntimeError(f"refused: window {size} at {pos} runs past the {sw}x{sh} screen. Painting must stay on screen.")
    prof = tempfile.mkdtemp(prefix=f"fastpaint-{port}-")
    args = [BRAVE, f"--remote-debugging-port={port}", f"--user-data-dir={prof}", "--no-first-run",
            "--no-default-browser-check", "--disable-features=Translate", "--disable-frame-rate-limit",
            "--disable-gpu-vsync", f"--window-size={size[0]},{size[1]}", f"--window-position={pos[0]},{pos[1]}",
            *extra, "about:blank"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1); return proc
        except Exception: time.sleep(0.25)
    raise RuntimeError("brave did not come up")

class Browser:
    """one websocket to the browser; every tab is a flattened CDP session on it"""
    def __init__(self, port):
        self.port = port; self.ws = None; self._id = 0; self._waiters = {}; self.tabs = {}
    async def connect(self):
        _no_browser_in_preflight()
        with urllib.request.urlopen(f"http://localhost:{self.port}/json/version") as r:
            url = json.load(r)["webSocketDebuggerUrl"]
        self.ws = await websockets.connect(url, max_size=64 * 1024 * 1024, ping_interval=None)
        self._reader = asyncio.create_task(self._read())
    async def _read(self):
        async for raw in self.ws:
            m = json.loads(raw)
            if "id" in m and m["id"] in self._waiters:
                self._waiters.pop(m["id"]).set_result(m)
    def send(self, method, params=None, session=None):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        if session: msg["sessionId"] = session
        asyncio.ensure_future(self.ws.send(json.dumps(msg)))
        return self._id
    async def call(self, method, params=None, session=None):
        fut = asyncio.get_event_loop().create_future()
        self._waiters[self.send(method, params, session)] = fut
        m = await fut
        if "error" in m: raise RuntimeError(f"{method}: {m['error']}")
        return m.get("result", {})
    async def existing_page(self, mode="input"):
        r = await self.call("Target.getTargets")
        pages = [t for t in r["targetInfos"] if t["type"]=="page"]
        if not pages: return None
        tgt = pages[0]["targetId"]
        a = await self.call("Target.attachToTarget", {"targetId": tgt, "flatten": True})
        t = Tab(self, a["sessionId"], mode); t.target_id = tgt
        await t.connect()
        try: await self.call("Target.activateTarget", {"targetId": tgt})
        except Exception: pass
        return t

    async def new_tab(self, mode="input"):
        r = await self.call("Target.createTarget", {"url": "about:blank"})
        a = await self.call("Target.attachToTarget", {"targetId": r["targetId"], "flatten": True})
        t = Tab(self, a["sessionId"], mode); t.target_id = r["targetId"]
        await t.connect()
        return t
    async def close(self):
        self._reader.cancel(); await self.ws.close()

class Tab:
    def __init__(self, browser, session, mode="input"):
        self.b = browser; self.session = session; self.mode = mode
        self.moves = 0; self.strokes = 0; self.sent = 0
        self.canvas = None   # dict x,y,w,h in CSS px
        self._boxes = {}
        self.t_first = None      # wall clock of the first draw call, for the run sidecar
        self.page_url = None
        self.run_meta = {}       # anything a script wants recorded; merged into the sidecar

    async def connect(self):
        await self.call("Page.enable"); await self.call("Runtime.enable")

    def send(self, method, params=None):
        """fire and forget"""
        self.sent += 1
        return None, self.b.send(method, params, self.session)

    async def call(self, method, params=None):
        self.sent += 1
        return await self.b.call(method, params, self.session)

    async def sync(self):
        """wait until everything sent so far has been processed"""
        await self.call("Runtime.evaluate", {"expression": "1"})

    async def eval(self, expr, ret=True):
        r = await self.call("Runtime.evaluate", {"expression": expr, "returnByValue": ret, "awaitPromise": True})
        return r.get("result", {}).get("value")

    async def goto(self, url):
        self.page_url = url
        await self.call("Page.navigate", {"url": url})
        for _ in range(100):
            if await self.eval("!!document.getElementById('main-canvas') && !!window.MattPaintReady || !!document.getElementById('main-canvas')"): break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.4)
        await self.eval(REPLAY_JS, ret=False)
        await self.eval(CONTROL_JS, ret=False)

    async def box(self, selector, fresh=False):
        if fresh or selector not in self._boxes:
            b = await self.eval(f"(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }})()")
            if not b: raise RuntimeError("no element " + selector)
            self._boxes[selector] = b
        return self._boxes[selector]

    async def measure_canvas(self):
        for _ in range(40):              # 2026-09-16: a slow page load raised "no element" mid-run
            try:
                b = await self.box('#main-canvas', fresh=True)
                break
            except RuntimeError:
                await asyncio.sleep(0.5)
        else:
            b = await self.box('#main-canvas', fresh=True)
        px = await self.eval("document.getElementById('main-canvas').width") or b[2]
        self.canvas = {"x": b[0], "y": b[1], "w": b[2], "h": b[3], "k": (b[2] / px) if px else 1.0}

    async def fit_canvas(self, margin=24):
        """Zoom MattPaint out (its own zoom, display only) until the whole canvas is on screen.
        Paint ops are in canvas px, so nothing about the painting changes. 2026-09-16: a 1380x900
        canvas under the ribbon ran off the bottom of the MacBook's window."""
        z = await self.eval(f"""(() => {{
            const c = document.getElementById('main-canvas');
            const box = document.getElementById('canvas-container').getBoundingClientRect();
            const room = Math.min(window.innerHeight, box.bottom) - box.top;
            let z = Math.min(1, (box.width - {margin}) / c.width, (room - {margin}) / c.height);
            z = Math.max(0.125, Math.floor(z / 0.125) * 0.125);
            const s = document.getElementById('status-zoom-slider');
            s.value = z * 100; s.dispatchEvent(new Event('input', {{bubbles: true}}));
            return z; }})()""")
        await self.measure_canvas()
        return z

    # ---------- raw input ----------
    def mouse(self, type_, x, y, button="none", buttons=0, click_count=0):
        p = {"type": type_, "x": x, "y": y, "button": button, "buttons": buttons}
        if click_count: p["clickCount"] = click_count
        self.send("Input.dispatchMouseEvent", p)
        if type_ == "mouseMoved": self.moves += 1

    def click_at(self, x, y, button="left"):
        self.mouse("mouseMoved", x, y)
        self.mouse("mousePressed", x, y, button, 1 if button == "left" else 2, 1)
        self.mouse("mouseReleased", x, y, button, 0, 1)

    async def click(self, selector, fresh=False):
        b = await self.box(selector, fresh)
        self.click_at(b[0] + b[2] / 2, b[1] + b[3] / 2)

    def key(self, ch):
        self.send("Input.dispatchKeyEvent", {"type": "keyDown", "key": ch, "text": ch})
        self.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch})

    # ---------- strokes (canvas px) ----------
    def stroke(self, pts, button=0):
        """pts = [(x, y), ...] in canvas pixels"""
        if self.t_first is None: self.t_first = time.time()
        self.strokes += 1
        if self.mode == "replay":
            self.send("Runtime.evaluate", {"expression": f"__fp.stroke({json.dumps([[round(x,1), round(y,1)] for x, y in pts])},{button})"})
            self.moves += len(pts) + 1
            return
        cx, cy, k = self.canvas["x"], self.canvas["y"], self.canvas.get("k", 1.0)
        pts = [(x * k, y * k) for x, y in pts]
        bname = "right" if button == 2 else "left"; bmask = 2 if button == 2 else 1
        x0, y0 = pts[0]
        self.mouse("mouseMoved", cx + x0, cy + y0)
        self.mouse("mousePressed", cx + x0, cy + y0, bname, bmask, 1)
        for x, y in pts[1:]:
            self.mouse("mouseMoved", cx + x, cy + y, bname, bmask)
        xl, yl = pts[-1]
        self.mouse("mouseReleased", cx + xl, cy + yl, bname, 0, 1)

    def batch(self, strokes, button=0):
        """strokes = [[(x,y),...], ...] in canvas px, one message"""
        if self.t_first is None: self.t_first = time.time()
        self.strokes += len(strokes)
        payload = [[[round(x, 1), round(y, 1)] for x, y in st] for st in strokes]
        self.send("Runtime.evaluate", {"expression": f"__fp.batch({json.dumps(payload)},{button})"})

    def fast(self, ops):
        """ops in canvas-internal px; drawn straight to the canvas via the accelerator"""
        if self.t_first is None: self.t_first = time.time()
        self.send("Runtime.evaluate", {"expression": f"window.__mpFast({json.dumps(ops)})"})
        self.strokes += len(ops)
    def fast_commit(self):
        self.send("Runtime.evaluate", {"expression": "window.__mpFastCommit&&window.__mpFastCommit()"})

    def drag(self, x1, y1, x2, y2, steps=2):
        pts = [(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps) for i in range(steps + 1)]
        self.stroke(pts)

    # ---------- app helpers (in-page, same path as replay strokes) ----------
    def jclick(self, sel):
        self.send("Runtime.evaluate", {"expression": f"__fpc.click({json.dumps(sel)})"})

    async def tool(self, name):
        self.jclick(f'#tool-{name}')

    async def shape(self, name):
        self.jclick(f'[data-shape="{name}"]')

    async def brush(self, kind):
        self.jclick(f'[data-brush="{kind}"]')

    async def size(self, n):
        self.jclick(f'[data-size="{n}"]')

    async def fill_mode(self, mode):
        self.jclick(f'[data-fill="{mode}"]')

    async def outline_mode(self, mode):
        self.jclick(f'[data-outline="{mode}"]')

    async def set_color(self, target, rgb):
        r, g, b = (int(v) for v in rgb)
        self.send("Runtime.evaluate", {"expression": f"__fpc.setColor({target},{r},{g},{b})"})

    async def resize_canvas(self, w, h):
        await self.eval(f"__fpc.resize({w},{h})", ret=False)
        await self.fit_canvas()

    async def png(self, path):
        data = await self.eval("__fp.png()")
        import base64
        open(path, "wb").write(base64.b64decode(data.split(",", 1)[1]))
        write_run_sidecar(self, path)

    async def close(self):
        try: await self.b.call("Target.closeTarget", {"targetId": self.target_id})
        except Exception: pass


# ---------- run log ----------
# Every png() writes a sidecar JSON beside it, unconditionally. Benchmarks you did not
# write down are benchmarks you lose; this is the ten lines that stops that happening.
def write_run_sidecar(tab, png_path):
    import hashlib, datetime, platform
    try:
        main = sys.modules.get("__main__")
        script = getattr(main, "__file__", None)
        src = open(script, "rb").read() if script else b""
        g = vars(main) if main else {}
        seed = g.get("SEED")
        if seed is None and src:                       # scripts hardcode random.seed(N)
            m = re.search(rb"random\.seed\(\s*(\d+)\s*\)", src)
            seed = int(m.group(1)) if m else None
        t_end = time.time()
        wall = (t_end - tab.t_first) if tab.t_first else None
        rec = {
            "png": os.path.basename(png_path),
            "finished": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "ops": tab.strokes,
            "wall_s": round(wall, 3) if wall else None,
            "ops_per_s": round(tab.strokes / wall) if wall and wall > 0 else None,
            "mouse_moves": tab.moves,
            "messages_sent": tab.sent,
            "mode": tab.mode,
            "seed": seed,
            "source_ref": g.get("REF"),
            "canvas": [g.get("CW"), g.get("CH")] if g.get("CW") else (
                [round(tab.canvas["w"]), round(tab.canvas["h"])] if tab.canvas else None),
            "script": os.path.basename(script) if script else None,
            "script_sha256": hashlib.sha256(src).hexdigest()[:16] if src else None,
            "argv": sys.argv[1:],
            "page_url": tab.page_url,
            "host": platform.node(),
        }
        rec.update(tab.run_meta)
        open(os.path.splitext(png_path)[0] + ".run.json", "w").write(json.dumps(rec, indent=1) + "\n")
    except Exception as e:                              # a log must never kill a render
        print(f"[run log] skipped: {e}", file=sys.stderr)
