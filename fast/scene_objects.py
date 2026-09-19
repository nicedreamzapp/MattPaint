"""SCENE OBJECTS — things the scene engine can paint besides landscape (2026-09-18).

Until today the engine knew 14 layer types, all nature (sky, ridges, water, forest, pines...), so
every prompt came back as a forest: Matt asked for a haunted black-light town and got tree trunks,
because trunks were the only tall shapes on the menu. This module adds two things:

  1. OBJECTS — ready-made subjects: town, house, castle, bare_tree, ghost, pumpkin, web, spider,
     bats, lamp, figure (person / goblin / witch / skeleton), moon, path.
  2. SVG + SHAPES — the director can draw ANY subject as an SVG (painted with brush dabs), or use
     free primitives (polygon, circle, ellipse, line, glow, text), so the director can
     build anything the object list does not cover. Nothing is hard-coded to one kind of picture.

Positions and sizes are fractions of the canvas (x 0..1 left->right, y 0..1 top->bottom; sizes are
fractions of the canvas HEIGHT). Colours are "#rrggbb" or [r, g, b]. A `glow` colour makes a thing
emit light (black-light paint, lit windows, jack-o'-lantern faces), which is how neon scenes read.
Everything still works as a flat-gray construction test (colours collapse to their value).
"""
import math, random
from art import mix

# every object with its defaults — scene_engine merges these into LAYERS
OBJECTS = {
    "town":      dict(count=9, ground=0.80, height=0.22, x0=0.0, x1=1.0, color=[30, 16, 52],
                      window=[255, 170, 60], lit=0.6, roofs="mixed", seed=5, trim=None),
    "house":     dict(x=0.3, ground=0.82, width=0.18, height=0.22, color=[34, 18, 58],
                      window=[255, 170, 60], roof="gable", porch=True, trim=None),
    "castle":    dict(x=0.55, ground=0.52, size=0.22, color=[24, 12, 44], window=[255, 190, 80],
                      hill=True, hill_color=[20, 10, 40]),
    "bare_tree": dict(x=0.15, ground=0.85, height=0.45, color=[14, 6, 26], lean=0.0, seed=3),
    "ghost":     dict(x=0.5, y=0.4, size=0.12, color=[200, 230, 255], glow=[120, 200, 255], alpha=0.75),
    "pumpkin":   dict(x=0.2, y=0.9, size=0.08, color=[255, 110, 10], glow=[255, 220, 90], face=True),
    "web":       dict(x=0.0, y=0.0, size=0.35, color=[120, 110, 255], corner="top-left", rings=9,
                      spokes=12),
    "spider":    dict(x=0.2, y=0.2, size=0.06, color=[12, 6, 20], eyes=[255, 60, 30], thread=True),
    "bats":      dict(count=8, x0=0.3, x1=0.9, y0=0.12, y1=0.4, size=0.03, color=[10, 4, 20], seed=9),
    "lamp":      dict(x=0.5, ground=0.85, height=0.3, color=[16, 8, 30], glow=[255, 200, 90]),
    "figure":    dict(kind="goblin", x=0.5, ground=0.9, height=0.25, color=[60, 200, 70],
                      clothes=[40, 20, 70], eyes=[255, 230, 60], facing=1),
    "moon":      dict(x=0.7, y=0.2, size=0.08, color=[240, 236, 210], glow=[160, 140, 255]),
    "path":      dict(x=0.5, top=0.62, width=0.5, color=[40, 20, 70], shine=[255, 120, 220], wet=True),
    "ground":    dict(top=0.8, color=[26, 12, 44], texture=0.15),
    "svg":       dict(svg="", x=0.0, y=0.0, w=1.0, h=1.0),
    "streaks":   dict(count=40, y0=0.08, y1=0.45, color=[60, 20, 110], lit=[255, 90, 40], x=0.5),
}

SHAPES = ("polygon", "circle", "ellipse", "line", "glow", "text")


# -------------------------------------------------------------------------- helpers
def rgb(c, fallback=(128, 128, 128)):
    if isinstance(c, str) and c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    if isinstance(c, (list, tuple)) and len(c) == 3:
        return tuple(int(max(0, min(255, v))) for v in c)
    return tuple(fallback)


class Pen:
    """Drawing on top of a Scene: fills, glows and figures in canvas px, with the scene's gray test."""

    def __init__(self, scene):
        self.s = scene
        self.W, self.H = scene.a.W, scene.a.H
        self.R, self.L, self.D = scene.a.R, scene.a.L, scene.a.D

    def c(self, col, shade=0.0):
        """a colour as painted: darkened by `shade` 0..1, collapsed to its value in the gray test"""
        col = mix(rgb(col), (0, 0, 0), max(0.0, min(1.0, shade)))
        if self.s.gray:
            v = int(0.2126 * col[0] + 0.7152 * col[1] + 0.0722 * col[2])
            return (v, v, v)
        return col

    def X(self, f): return float(f) * self.W
    def Y(self, f): return float(f) * self.H
    def S(self, f): return float(f) * self.H

    # --- fills
    def poly(self, pts, col, texture=0.06, shade_top=0.0):
        """scanline fill, 2px rows, plus a light brush texture so it is paint, not vector"""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = max(0, int(min(ys))), min(self.H, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1, 2):
            yc = y + 1.0
            xs = []
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            sh = shade_top * (1 - (y - y0) / max(1, y1 - y0))
            for a, b in zip(xs[0::2], xs[1::2]):
                if b - a >= 0.5:
                    self.R(a, y, b - a + 1, 2, self.c(col, sh))
        if texture:
            w = max(1, (max(p[0] for p in pts) - min(p[0] for p in pts)))
            for _ in range(int(w * (y1 - y0) / 180)):
                x = random.uniform(min(p[0] for p in pts), max(p[0] for p in pts))
                y = random.uniform(y0, y1)
                if self.inside(pts, x, y):
                    self.D(x, y, random.uniform(1, 3), self.c(col, random.uniform(-texture, texture * 2)), 0.5)

    @staticmethod
    def inside(pts, x, y):
        n, ok = len(pts), False
        for i in range(n):
            (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                ok = not ok
        return ok

    def ellipse(self, cx, cy, rx, ry, col, texture=0.06, shade_top=0.0):
        pts = [(cx + math.cos(t) * rx, cy + math.sin(t) * ry) for t in
               (i * 2 * math.pi / 48 for i in range(48))]
        self.poly(pts, col, texture, shade_top)

    def glow(self, x, y, r, col, strength=1.0):
        """emitted light that ADDS to what is under it (Screen), with a hot core — the way neon and
        black-light paint read in a composite (idea: Robbie Tilton's Compositor)"""
        col = self.c(col)
        self.s.a.G(x, y, r * 1.8, col, min(1.0, 0.55 * strength), 0)
        self.s.a.G(x, y, r * 0.8, col, min(1.0, 0.5 * strength), 1)
        self.s.a.G(x, y, max(1.0, r * 0.18), mix(col, (255, 255, 255), 0.55), min(1.0, 0.9 * strength), 1)

    def line(self, pts, w, col, alpha=1.0):
        col = self.c(col)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if alpha >= 1.0:
                self.L(ax, ay, bx, by, w, col)
            else:
                d = math.hypot(bx - ax, by - ay); n = max(2, int(d / max(1.0, w * 0.6)))
                for i in range(n + 1):
                    t = i / n
                    self.D(ax + (bx - ax) * t, ay + (by - ay) * t, w / 2, col, alpha)

    def light(self, x, y, col, r):
        """remember an emitted light so a wet street can reflect it (see finish())"""
        if not hasattr(self.s, "_lights"):
            self.s._lights = []
        self.s._lights.append((x, y, rgb(col), r))

    def neon(self, pts, col, w=2.0, closed=False, strength=1.0):
        """a glowing line: soft halo dabs under a bright core — black-light trim, glowing web silk"""
        if closed:
            pts = list(pts) + [pts[0]]
        c = self.c(col)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            d = math.hypot(bx - ax, by - ay); n = max(2, int(d / (w * 2.5)))
            for i in range(n + 1):
                t = i / n
                self.s.a.G(ax + (bx - ax) * t, ay + (by - ay) * t, w * 4.0, c, 0.22 * strength, 0)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self.L(ax, ay, bx, by, w, mix(c, (255, 255, 255), 0.25))

    def grad(self, pts, top, bottom, texture=0.05):
        """polygon filled with a vertical gradient, top colour to bottom colour"""
        ys = [q[1] for q in pts]
        y0, y1 = max(0, int(min(ys))), min(self.H, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1, 2):
            yc = y + 1.0
            xs = sorted(ax + (yc - ay) * (bx - ax) / (by - ay)
                        for (ax, ay), (bx, by) in ((pts[i], pts[(i + 1) % n]) for i in range(n))
                        if (ay <= yc < by) or (by <= yc < ay))
            c = self.c(mix(rgb(top), rgb(bottom), (y - y0) / max(1, y1 - y0)))
            for a_, b_ in zip(xs[0::2], xs[1::2]):
                if b_ - a_ >= 0.5:
                    self.R(a_, y, b_ - a_ + 1, 2, c)
        if texture:
            x0, x1 = min(q[0] for q in pts), max(q[0] for q in pts)
            for _ in range(int((x1 - x0) * (y1 - y0) / 160)):
                x, y = random.uniform(x0, x1), random.uniform(y0, y1)
                if self.inside(pts, x, y):
                    c = mix(rgb(top), rgb(bottom), (y - y0) / max(1, y1 - y0))
                    self.D(x, y, random.uniform(1, 3), self.c(c, random.uniform(-texture, texture * 2)), 0.5)

    def mist(self, pts, col, alpha=0.35, step=3.0, core=None):
        """translucent fill made of dabs (a ghost, a veil): denser toward `core` if given"""
        x0, x1 = min(q[0] for q in pts), max(q[0] for q in pts)
        y0, y1 = min(q[1] for q in pts), max(q[1] for q in pts)
        c = self.c(col)
        y = y0
        while y < y1:
            x = x0
            while x < x1:
                px, py = x + random.uniform(-1, 1), y + random.uniform(-1, 1)
                if self.inside(pts, px, py):
                    a = alpha
                    if core:
                        d = math.hypot(px - core[0], py - core[1]) / core[2]
                        a = alpha * max(0.25, 1.2 - d)
                    self.D(px, py, step * 0.9, c, min(1.0, a))
                x += step
            y += step

    def window(self, x, y, w, h, col, lit=True):
        self.R(x - w * 0.12, y - h * 0.1, w * 1.24, h * 1.2, self.c((10, 4, 18)))   # frame
        if lit:
            self.glow(x + w / 2, y + h / 2, max(w, h) * 1.3, col, 0.35)
            self.light(x + w / 2, y + h / 2, col, max(w, h))
            self.grad([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                      mix(rgb(col), (255, 255, 230), 0.35), mix(rgb(col), (120, 30, 0), 0.25), texture=0)
            self.R(x + w * 0.46, y, max(1, w * 0.08), h, self.c(col, 0.6))     # mullion
            self.R(x, y + h * 0.46, w, max(1, h * 0.08), self.c(col, 0.6))
        else:
            self.R(x, y, w, h, self.c(col, 0.85))


# -------------------------------------------------------------------------- objects
def house(pen, x, ground, w, h, col, win, roof="gable", porch=False, lit=0.7, trim=None):
    """a crooked old house front: boards, shingled roof, framed glowing windows, optional neon trim"""
    col = rgb(col)
    lean = random.uniform(-0.04, 0.04) * w                                # nothing here is square
    x0, x1, gy, top = x - w / 2, x + w / 2, ground, ground - h
    walls = [(x0, gy), (x0 + lean, top), (x1 + lean, top), (x1, gy)]
    pen.grad(walls, mix(col, (255, 255, 255), 0.08), mix(col, (0, 0, 0), 0.45))
    for k in range(1, int(w / 7)):                                        # clapboards
        bx = x0 + k * w / int(w / 7)
        pen.line([(bx, gy), (bx + lean, top)], 1.0, mix(col, (0, 0, 0), 0.4), 0.35)
    rh = h * random.uniform(0.4, 0.65) * (1.8 if roof == "spire" else 1.0)
    peak = (x + lean + random.uniform(-0.08, 0.08) * w, top - rh)
    if roof == "flat":
        rpts = [(x0 + lean - 3, top), (x0 + lean - 3, top - h * 0.07), (x1 + lean + 3, top - h * 0.07), (x1 + lean + 3, top)]
    else:
        ov = w * (0.05 if roof == "spire" else 0.1)
        sag = rh * 0.08                                                   # an old roof sags
        rpts = [(x0 + lean - ov, top), ((x0 + lean + peak[0]) / 2, (top + peak[1]) / 2 + sag), peak,
                ((x1 + lean + peak[0]) / 2, (top + peak[1]) / 2 + sag), (x1 + lean + ov, top)]
    pen.grad(rpts, mix(col, (0, 0, 0), 0.25), mix(col, (0, 0, 0), 0.55))
    if roof != "flat":                                                    # shingle rows
        for k in range(1, int(rh / 6)):
            yy = top - k * 6
            t = (top - yy) / rh
            half = (w / 2 + w * 0.1) * (1 - t)
            for sx in range(int(peak[0] - half), int(peak[0] + half), 7):
                pen.L(sx, yy, sx + 5, yy + random.uniform(-0.6, 0.6), 1.0, pen.c(col, 0.65))
    if trim:
        pen.neon(rpts, trim, 1.6, strength=1.2)
        pen.neon([(x0, gy), (x0 + lean, top)], trim, 1.0, strength=0.6)
    if random.random() < 0.6:                                             # chimney
        cx = x0 + w * random.uniform(0.6, 0.78) + lean
        pen.grad([(cx, top - rh * 0.25), (cx, top - rh * 0.85), (cx + w * 0.09, top - rh * 0.85),
                  (cx + w * 0.09, top - rh * 0.1)], mix(col, (0, 0, 0), 0.3), mix(col, (0, 0, 0), 0.6))
    rows = max(1, int(h / max(18, w * 0.35)))
    cols = max(1, int(w / max(16, h * 0.3)))
    ww, wh = w / (cols * 2.6), h / (rows * 2.4)
    for r in range(rows):
        for c in range(cols):
            wx = x0 + lean * (1 - (r + 0.5) / rows) + (c + 0.5) * w / cols - ww / 2
            wy = top + (r + 0.3) * h / rows
            if wy + wh < gy - h * 0.2:
                pen.window(wx, wy, ww, wh, win, random.random() < lit)
    door_w = w * 0.17
    pen.grad([(x - door_w / 2, gy), (x - door_w / 2, gy - h * 0.3), (x + door_w / 2, gy - h * 0.3),
              (x + door_w / 2, gy)], mix(col, (0, 0, 0), 0.6), mix(col, (0, 0, 0), 0.8), texture=0)
    if porch:
        pen.R(x0 - w * 0.06, gy - h * 0.36, w * 1.12, max(2, h * 0.035), pen.c(col, 0.55))
        for px in (x0 - w * 0.03, x1 + w * 0.02):
            pen.R(px, gy - h * 0.36, 3, h * 0.36, pen.c(col, 0.6))
        if trim:
            pen.neon([(x0 - w * 0.06, gy - h * 0.36), (x1 + w * 0.06, gy - h * 0.36)], trim, 1.2)


def pen_dark(col):
    return mix(rgb(col), (0, 0, 0), 0.35)


def draw_town(pen, p):
    trim = p.get("trim")
    random.seed(int(p["seed"]))
    n = max(1, int(p["count"]))
    x0, x1 = pen.X(p["x0"]), pen.X(p["x1"])
    gy, h = pen.Y(p["ground"]), pen.S(p["height"])
    span = (x1 - x0) / n
    order = list(range(n))
    random.shuffle(order)
    for i in order:
        w = span * random.uniform(0.8, 1.15)
        hh = h * random.uniform(0.65, 1.25)
        roof = p["roofs"] if p["roofs"] != "mixed" else random.choice(("gable", "gable", "spire", "flat"))
        house(pen, x0 + span * (i + 0.5) + random.uniform(-0.1, 0.1) * span, gy, w, hh,
              mix(rgb(p["color"]), (0, 0, 0), random.uniform(-0.15, 0.25)), p["window"], roof,
              lit=float(p["lit"]), trim=trim)


def draw_house(pen, p):
    house(pen, pen.X(p["x"]), pen.Y(p["ground"]), pen.X(p["width"]), pen.S(p["height"]), p["color"],
          p["window"], p["roof"], bool(p["porch"]), trim=p.get("trim"))


def draw_castle(pen, p):
    x, gy, s = pen.X(p["x"]), pen.Y(p["ground"]), pen.S(p["size"])
    col, win = p["color"], p["window"]
    if p["hill"]:
        pts = [(x - s * 2.6, gy + s * 1.2)] + [(x + s * 2.6 * math.cos(t), gy + s * 0.15 - s * 0.55 * math.sin(t))
                                                 for t in (i * math.pi / 30 for i in range(31))][::-1]
        pts = [(x - s * 2.6, pen.H)] + [(x + s * 2.6 * math.cos(math.pi - t), gy + s * 0.15 - s * 0.5 * math.sin(t))
                                        for t in (i * math.pi / 30 for i in range(31))] + [(x + s * 2.6, pen.H)]
        pen.poly(pts, p["hill_color"])
    body_w = s * 1.2
    pen.poly([(x - body_w / 2, gy), (x - body_w / 2, gy - s * 0.55), (x + body_w / 2, gy - s * 0.55),
              (x + body_w / 2, gy)], col)
    for dx, th, tw in ((-0.62, 0.9, 0.22), (0.62, 0.8, 0.22), (0.0, 1.25, 0.28), (-0.3, 0.7, 0.16), (0.32, 0.72, 0.16)):
        tx = x + dx * s
        w = tw * s
        pen.poly([(tx - w / 2, gy), (tx - w / 2, gy - s * th), (tx + w / 2, gy - s * th), (tx + w / 2, gy)], col)
        pen.poly([(tx - w * 0.65, gy - s * th), (tx, gy - s * th - s * 0.45 * (w / s) * 2.2), (tx + w * 0.65, gy - s * th)],
                 pen_dark(col))
        for k in range(int(th * 3)):
            if random.random() < 0.7:
                pen.window(tx - w * 0.12, gy - s * th + s * (0.12 + k * 0.28), w * 0.24, s * 0.1, win)
    for k in range(6):
        if random.random() < 0.8:
            pen.window(x - body_w * 0.4 + k * body_w * 0.15, gy - s * 0.35, s * 0.06, s * 0.1, win)


def draw_bare_tree(pen, p):
    random.seed(int(p["seed"]))
    x, gy, h = pen.X(p["x"]), pen.Y(p["ground"]), pen.S(p["height"])
    col = pen.c(p["color"])

    class _A:          # route g3's branch painter through our colour
        D = staticmethod(pen.D)
    import g3lib as G
    G.fractal_branch(_A, x, gy, -math.pi / 2 + float(p["lean"]), h * 0.34, max(3, h * 0.045), col, col,
                     maxd=7, ratio=0.74, spread=0.62)
    for _ in range(3):                                                  # roots flare into the ground
        a = random.uniform(-0.6, 0.6)
        pen.line([(x, gy - 4), (x + math.sin(a) * h * 0.12, gy + 3)], max(2, h * 0.02), p["color"])


def draw_ghost(pen, p):
    """a sheet ghost: round head, body flaring to a ragged trailing hem, see-through, glowing"""
    x, y, s = pen.X(p["x"]), pen.Y(p["y"]), pen.S(p["size"])
    lean = random.uniform(-0.25, 0.25)
    pts = []
    for i in range(13):                                                   # head: top half circle
        t = math.pi + i * math.pi / 12
        pts.append((x + math.cos(t) * s * 0.28, y - s * 0.3 + math.sin(t) * s * 0.3))
    tails = random.randint(3, 5)
    right = [(x + s * 0.36 + lean * s * 0.3, y + s * 0.2), (x + s * 0.44 + lean * s * 0.6, y + s * 0.62)]
    hem = []
    for k in range(tails * 2 + 1):                                        # ragged hem, tails trail with the lean
        t = k / (tails * 2)
        hx = x + s * 0.44 + lean * s * 0.6 - t * s * 0.9
        hy = y + s * (0.7 + (0.35 + random.uniform(0, 0.2) if k % 2 == 0 else 0.05))
        hem.append((hx + lean * s * 0.5 * (hy - y) / s, hy))
    left = [(x - s * 0.46 + lean * s * 0.6, y + s * 0.62), (x - s * 0.36 + lean * s * 0.3, y + s * 0.2)]
    pts = pts + right + hem + left
    pen.glow(x, y, s * 1.2, p["glow"], 0.9)
    pen.mist(pts, p["glow"], alpha=0.18, step=4, core=(x, y - s * 0.2, s * 0.9))
    pen.mist(pts, p["color"], alpha=float(p["alpha"]) * 0.55, step=3, core=(x, y - s * 0.25, s * 0.7))
    pen.neon(pts, p["glow"], 1.2, closed=True, strength=0.6)
    dark = pen.c((12, 8, 40))
    for side in (-1, 1):                                                  # tall hollow eyes
        pen.ellipse(x + side * s * 0.1, y - s * 0.34, s * 0.045, s * 0.075, (12, 8, 40), texture=0)
    pen.ellipse(x, y - s * 0.12, s * 0.06, s * 0.09, (12, 8, 40), texture=0)   # wailing mouth
    for side in (-1, 1):                                                  # arms raised, trailing sleeves
        pen.mist([(x + side * s * 0.3, y - s * 0.05), (x + side * s * 0.72, y - s * 0.3),
                  (x + side * s * 0.8, y - s * 0.18), (x + side * s * 0.36, y + s * 0.18)],
                 p["color"], alpha=float(p["alpha"]) * 0.4, step=3)


def draw_pumpkin(pen, p):
    """a jack-o'-lantern: ribbed, lit from inside, the face burning yellow at the core"""
    x, y, s = pen.X(p["x"]), pen.Y(p["y"]), pen.S(p["size"])
    col = rgb(p["color"])
    if p["face"]:
        pen.glow(x, y, s * 1.6, p["glow"], 0.8)
        pen.light(x, y, p["glow"], s)
    for k, dx in enumerate((-0.34, 0.34, -0.19, 0.19, 0.0)):             # ribs, outer first, lit middle
        rx, ry = s * (0.28 if k < 2 else 0.3), s * (0.4 if k < 2 else 0.44)
        cx = x + dx * s
        pts = [(cx + math.cos(t) * rx, y + math.sin(t) * ry) for t in (i * 2 * math.pi / 40 for i in range(40))]
        pen.grad(pts, mix(col, (255, 230, 150), 0.2 if k == 4 else 0.05), mix(col, (60, 10, 0), 0.55 if k < 2 else 0.4))
    pen.grad([(x - s * 0.05, y - s * 0.4), (x - s * 0.02, y - s * 0.6), (x + s * 0.08, y - s * 0.58),
              (x + s * 0.05, y - s * 0.4)], (90, 120, 40), (40, 60, 20), texture=0)
    if p["face"]:
        g = rgb(p["glow"])
        hot = mix(g, (255, 255, 220), 0.5)
        for side in (-1, 1):                                              # angry eyes
            e = [(x + side * s * 0.3, y - s * 0.02), (x + side * s * 0.1, y - s * 0.06), (x + side * s * 0.22, y - s * 0.22)]
            pen.grad(e, hot, g, texture=0)
        pen.grad([(x - s * 0.05, y + s * 0.05), (x + s * 0.05, y + s * 0.05), (x, y - s * 0.06)], hot, g, texture=0)
        mouth = [(x - s * 0.34, y + s * 0.1)]
        for i in range(9):                                                # jagged teeth
            mouth.append((x - s * 0.34 + (i + 0.5) * s * 0.68 / 9, y + s * (0.14 if i % 2 else 0.22)))
        mouth += [(x + s * 0.34, y + s * 0.1), (x + s * 0.22, y + s * 0.3), (x, y + s * 0.34), (x - s * 0.22, y + s * 0.3)]
        pen.grad(mouth, hot, g, texture=0)


def draw_web(pen, p):
    """an orb web: straight spokes, sagging spiral threads, glowing silk (black light makes it neon)"""
    s = pen.S(p["size"])
    corner = p["corner"]
    cx, cy = pen.X(p["x"]), pen.Y(p["y"])
    if corner != "none":
        cx = 0 if "left" in corner else pen.W
        cy = 0 if "top" in corner else pen.H
    a0, a1 = {"top-left": (0, math.pi / 2), "top-right": (math.pi / 2, math.pi),
              "bottom-left": (-math.pi / 2, 0), "bottom-right": (math.pi, 1.5 * math.pi)}.get(corner, (0, 2 * math.pi))
    n = int(p["spokes"])
    full = corner == "none"
    angs = [a0 + (a1 - a0) * i / (n if full else n - 1) + random.uniform(-0.04, 0.04) for i in range(n)]
    col = p["color"]
    for a in angs:
        pen.neon([(cx, cy), (cx + math.cos(a) * s * random.uniform(0.95, 1.1), cy + math.sin(a) * s)], col, 1.1, strength=0.7)
    rings = int(p["rings"])
    for r in range(1, rings + 1):
        rr = s * (r / (rings + 0.3)) ** 0.9
        pts = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr) for a in angs]
        segs = list(zip(pts, pts[1:] + ([pts[0]] if full else [])))
        for (ax, ay), (bx, by) in segs:
            curve = []
            for k in range(7):                                            # each thread droops between spokes
                t = k / 6
                mx, my = ax + (bx - ax) * t, ay + (by - ay) * t
                dip = math.sin(t * math.pi) * rr * 0.06
                dx, dy = mx - cx, my - cy; d = math.hypot(dx, dy) or 1
                curve.append((mx - dx / d * dip, my - dy / d * dip + dip * 0.5))
            pen.neon(curve, col, 0.9, strength=0.5)
            if random.random() < 0.35:
                q = curve[3]
                pen.D(q[0], q[1], 1.8, pen.c(mix(rgb(col), (255, 255, 255), 0.7)), 0.95)   # dew


def draw_spider(pen, p):
    x, y, s = pen.X(p["x"]), pen.Y(p["y"]), pen.S(p["size"])
    col = p["color"]
    if p["thread"]:
        pen.line([(x, 0), (x, y - s * 0.3)], 1.2, (200, 200, 230), 0.6)
    for side in (-1, 1):
        for k in range(4):
            a = -0.9 + k * 0.55
            kx, ky = x + side * s * 0.55 * math.cos(a), y + s * (0.5 * math.sin(a) - 0.25)
            fx, fy = x + side * s * 1.0 * math.cos(a * 0.8), y + s * (0.55 * math.sin(a) + 0.3)
            pen.line([(x, y), (kx, ky), (fx, fy)], max(1.5, s * 0.05), col)
    pen.ellipse(x, y + s * 0.18, s * 0.3, s * 0.36, col)
    pen.ellipse(x, y - s * 0.15, s * 0.18, s * 0.16, col)
    for side in (-1, 1):
        pen.glow(x + side * s * 0.07, y - s * 0.18, s * 0.08, p["eyes"], 1.0)


def draw_bats(pen, p):
    random.seed(int(p["seed"]))
    for _ in range(int(p["count"])):
        x = pen.X(random.uniform(p["x0"], p["x1"])); y = pen.Y(random.uniform(p["y0"], p["y1"]))
        s = pen.S(p["size"]) * random.uniform(0.6, 1.3)
        flap = random.uniform(-0.3, 0.4)
        for side in (-1, 1):
            pts = [(x, y), (x + side * s * 0.4, y - s * (0.25 + flap)), (x + side * s, y - s * (0.1 + flap)),
                   (x + side * s * 0.8, y + s * 0.05), (x + side * s * 0.6, y - s * 0.02),
                   (x + side * s * 0.4, y + s * 0.12), (x + side * s * 0.15, y + s * 0.02)]
            pen.poly(pts, p["color"], texture=0)
        pen.ellipse(x, y, s * 0.12, s * 0.16, p["color"], texture=0)


def draw_lamp(pen, p):
    x, gy, h = pen.X(p["x"]), pen.Y(p["ground"]), pen.S(p["height"])
    pen.light(x, gy - h * 1.05, p["glow"], h * 0.2)
    pen.poly([(x - h * 0.02, gy), (x - h * 0.012, gy - h), (x + h * 0.012, gy - h), (x + h * 0.02, gy)], p["color"])
    pen.glow(x, gy - h * 1.05, h * 0.35, p["glow"], 1.0)
    pen.poly([(x - h * 0.07, gy - h), (x - h * 0.09, gy - h * 1.14), (x + h * 0.09, gy - h * 1.14),
              (x + h * 0.07, gy - h)], p["glow"], texture=0)
    pen.poly([(x - h * 0.1, gy - h * 1.14), (x, gy - h * 1.22), (x + h * 0.1, gy - h * 1.14)], p["color"])


def draw_figure(pen, p):
    """a standing figure — goblin, witch, skeleton, zombie, person — built as shaded masses with a
    glowing rim on the side facing the light, glowing eyes, hands with fingers"""
    kind = p["kind"]
    x, gy, h, f = pen.X(p["x"]), pen.Y(p["ground"]), pen.S(p["height"]), float(p["facing"]) or 1.0
    skin = rgb(p["color"]) if kind != "skeleton" else rgb(p.get("color") or (225, 225, 210))
    cloth = rgb(p["clothes"])
    rim = rgb(p.get("rim") or mix(skin, (255, 255, 255), 0.4))
    hunch = {"goblin": 0.2, "witch": 0.12, "zombie": 0.14}.get(kind, 0.0)
    dark = lambda c, k: mix(c, (0, 0, 0), k)
    sh = (x + f * h * hunch * 0.6, gy - h * 0.7)                          # shoulders
    hx, hy = x + f * h * hunch, gy - h * (0.8 if kind == "goblin" else 0.86)
    if kind == "skeleton":
        bone = skin
        pen.neon([(hx, hy + h * 0.08), (x, gy - h * 0.42)], bone, h * 0.012, strength=0.5)
        for k in range(6):                                                # ribcage
            yy = gy - h * (0.72 - k * 0.045)
            wdt = h * (0.1 - abs(k - 2) * 0.012)
            pen.neon([(x - wdt, yy + h * 0.02), (x, yy), (x + wdt, yy + h * 0.02)], bone, h * 0.008, strength=0.5)
        pen.neon([(x - h * 0.08, gy - h * 0.42), (x + h * 0.08, gy - h * 0.42)], bone, h * 0.012, strength=0.5)
        for side in (-1, 1):
            pen.neon([(x + side * h * 0.06, gy - h * 0.42), (x + side * h * 0.09, gy - h * 0.2), (x + side * h * 0.1, gy)],
                     bone, h * 0.012, strength=0.5)
    else:
        hem = h * (0.34 if kind == "witch" else 0.2)
        body = [(x - hem, gy - (0 if kind == "witch" else h * 0.22)), (sh[0] - h * 0.15, sh[1] + h * 0.04),
                (sh[0] - h * 0.05, sh[1] - h * 0.03), (sh[0] + h * 0.1, sh[1] - h * 0.02), (sh[0] + h * 0.16, sh[1] + h * 0.06),
                (x + hem, gy - (0 if kind == "witch" else h * 0.22))]
        if kind == "witch":
            body[-1] = (x + hem, gy); body[0] = (x - hem, gy)
            for k in range(6):                                            # ragged hem
                body.insert(-1 - k, (x + hem - (k + 1) * 2 * hem / 7, gy + (h * 0.03 if k % 2 else 0)))
        pen.grad(body, mix(cloth, rim, 0.3), dark(cloth, 0.35))
        pen.neon(body[:4] if f > 0 else body[-4:], rim, max(1.2, h * 0.006), strength=0.7)
        if kind != "witch":                                               # legs, bent
            for side in (-1, 1):
                kx = x + side * h * 0.07 + f * h * 0.03
                pen.line([(x + side * h * 0.06, gy - h * 0.24), (kx, gy - h * 0.12), (x + side * h * 0.09, gy)],
                         h * 0.06, dark(cloth, 0.3))
                pen.ellipse(x + side * h * 0.09 + f * h * 0.03, gy, h * 0.05, h * 0.018, dark(skin, 0.4), texture=0)
    arm_c = skin if kind == "skeleton" else cloth
    for side in (-1, 1):                                                  # arms reaching, clawed hands
        ax = sh[0] + side * h * 0.13
        reach = 1.0 if side == f else 0.65
        el = (ax + f * h * 0.12 * reach, gy - h * 0.52)
        hd = (ax + f * h * 0.28 * reach, gy - h * 0.5 + (side * h * 0.03))
        pen.line([(ax, sh[1] + h * 0.02), el, hd], h * (0.018 if kind == "skeleton" else 0.05), dark(arm_c, 0.15))
        pen.ellipse(hd[0], hd[1], h * 0.03, h * 0.025, skin, texture=0)
        for k in range(4):
            a = -0.7 + k * 0.4
            pen.line([hd, (hd[0] + f * math.cos(a) * h * 0.07, hd[1] + math.sin(a) * h * 0.06 + h * 0.02)],
                     max(1.2, h * 0.01), dark(skin, 0.2))
    # head
    hr = h * (0.12 if kind == "goblin" else 0.1)
    head = [(hx + math.cos(t) * hr * (1.05 if kind == "goblin" else 0.9), hy + math.sin(t) * hr * 1.1)
            for t in (i * 2 * math.pi / 36 for i in range(36))]
    pen.grad(head, mix(skin, rim, 0.25), dark(skin, 0.45))
    lit_side = [(hx + math.cos(t) * hr * 0.98, hy + math.sin(t) * hr * 1.08)
                for t in (-1.2 + i * 0.12 for i in range(14))]
    pen.neon([(hx - (q[0] - hx) if f < 0 else q[0], q[1]) for q in lit_side], rim, max(1.0, h * 0.005), strength=0.5)
    if kind == "goblin":
        for side in (-1, 1):                                              # long drooping ears
            ear = [(hx + side * hr * 0.8, hy - hr * 0.3), (hx + side * hr * 2.3, hy - hr * 0.9),
                   (hx + side * hr * 1.9, hy - hr * 0.5), (hx + side * hr * 0.85, hy + hr * 0.2)]
            pen.grad(ear, mix(skin, rim, 0.2), dark(skin, 0.4), texture=0)
            pen.line([(hx + side * hr * 0.95, hy - hr * 0.1), (hx + side * hr * 1.9, hy - hr * 0.65)], max(1, h * 0.006),
                     dark(skin, 0.55), 0.8)
        nose = [(hx + f * hr * 0.1, hy - hr * 0.1), (hx + f * hr * 0.75, hy + hr * 0.25), (hx + f * hr * 0.1, hy + hr * 0.3)]
        pen.grad(nose, mix(skin, rim, 0.3), dark(skin, 0.3), texture=0)
        grin = [(hx - hr * 0.55 + f * hr * 0.15, hy + hr * 0.45), (hx + hr * 0.55 + f * hr * 0.15, hy + hr * 0.4),
                (hx + f * hr * 0.15, hy + hr * 0.75)]
        pen.grad(grin, (40, 0, 10), (10, 0, 0), texture=0)
        for k in range(5):                                                # teeth
            tx = hx - hr * 0.42 + f * hr * 0.15 + k * hr * 0.2
            pen.grad([(tx, hy + hr * 0.45), (tx + hr * 0.1, hy + hr * 0.45), (tx + hr * 0.05, hy + hr * 0.58)],
                     (250, 245, 200), (190, 180, 120), texture=0)
    elif kind == "witch":
        hat = [(hx - hr * 1.8, hy - hr * 0.6), (hx - hr * 0.7, hy - hr * 0.75), (hx - f * hr * 0.2, hy - hr * 3.4),
               (hx + f * hr * 1.2, hy - hr * 2.8), (hx + hr * 0.7, hy - hr * 0.75), (hx + hr * 1.8, hy - hr * 0.6)]
        pen.grad(hat, mix(cloth, rim, 0.1), dark(cloth, 0.5), texture=0)
        pen.neon(hat, rim, max(1, h * 0.004), closed=True, strength=0.4)
        for side in (-1, 1):                                              # stringy hair, framing the face
            for k in range(3):
                sx = hx + side * hr * (0.85 + k * 0.18)
                pen.line([(sx, hy - hr * 0.5), (sx + side * hr * 0.25, hy + hr * 1.7)], max(1, h * 0.008),
                         mix(cloth, rim, 0.3), 0.9)
        pen.grad([(hx + f * hr * 0.2, hy - hr * 0.1), (hx + f * hr * 1.0, hy + hr * 0.35), (hx + f * hr * 0.25, hy + hr * 0.3)],
                 mix(skin, rim, 0.3), dark(skin, 0.3), texture=0)
    elif kind == "skeleton":
        for side in (-1, 1):
            pen.ellipse(hx + side * hr * 0.38, hy - hr * 0.05, hr * 0.28, hr * 0.32, (10, 5, 20), texture=0)
        pen.grad([(hx - hr * 0.1, hy + hr * 0.3), (hx + hr * 0.1, hy + hr * 0.3), (hx, hy + hr * 0.1)], (10, 5, 20), (10, 5, 20), texture=0)
        for k in range(6):
            pen.R(hx - hr * 0.45 + k * hr * 0.16, hy + hr * 0.6, max(1, hr * 0.1), hr * 0.2, pen.c(skin))
    for side in (-1, 1):                                                  # glowing eyes
        ex, ey = hx + side * hr * 0.35 + f * hr * 0.12, hy - hr * 0.05
        if kind == "skeleton":
            ex -= f * hr * 0.12
        pen.glow(ex, ey, hr * 0.5, p["eyes"], 1.0)
        pen.ellipse(ex, ey, hr * 0.16, hr * 0.12, mix(rgb(p["eyes"]), (255, 255, 220), 0.5), texture=0)
        pen.D(ex + f * hr * 0.04, ey, max(1.0, hr * 0.05), pen.c((0, 0, 0)), 1.0)
    pen.light(hx, hy, p["eyes"], hr * 0.3)


def draw_moon(pen, p):
    x, y, s = pen.X(p["x"]), pen.Y(p["y"]), pen.S(p["size"])
    pen.glow(x, y, s * 2.2, p["glow"], 0.8)
    pen.ellipse(x, y, s * 0.5, s * 0.5, p["color"], texture=0.1)


def draw_path(pen, p):
    """a street running back to a vanishing point: cobbles, and (wet) it reflects every light"""
    x, top, w = pen.X(p["x"]), pen.Y(p["top"]), pen.X(p["width"])
    pts = [(x - w * 0.02, top), (x + w * 0.02, top), (x + w / 2, pen.H), (x - w / 2, pen.H)]
    col = rgb(p["color"])
    pen.grad(pts, mix(col, (0, 0, 0), 0.3), col, texture=0.1)
    for k in range(1, 22):                                                # cobble rows recede
        t = (k / 22) ** 1.7
        yy = top + t * (pen.H - top)
        half = w * 0.02 + (w / 2 - w * 0.02) * t
        step = max(4, 26 * t)
        xx = x - half + random.uniform(0, step)
        while xx < x + half:
            pen.ellipse(xx, yy, step * 0.42, max(1.5, step * 0.16), mix(col, (255, 255, 255), random.uniform(0, 0.12)), texture=0)
            xx += step
    if p["wet"]:
        pen.s._wet = (x, top, w, rgb(p["shine"]))


def draw_ground(pen, p):
    """plain ground from `top` to the bottom edge, so nothing floats over the sky"""
    top = pen.Y(p["top"])
    pen.poly([(0, top), (pen.W, top), (pen.W, pen.H), (0, pen.H)], p["color"], texture=float(p["texture"]))


def draw_svg(pen, p):
    """ANYTHING: the director writes an SVG drawing (a car, a cat, a person, a whole city) and it
    is painted here with brush dabs and edge strokes, placed in the box x, y, w, h (fractions of
    the canvas; w of the width, h of the height). SVG is the one drawing language every model
    already knows, so no subject needs its own object. rsvg-convert does the reading."""
    import subprocess, tempfile, os
    import numpy as np
    from PIL import Image
    src = str(p.get("svg") or "")
    if "<svg" not in src:
        return
    bx, by = pen.X(p["x"]), pen.Y(p["y"])
    bw, bh = max(8, int(pen.X(p["w"]))), max(8, int(pen.Y(p["h"])))
    with tempfile.TemporaryDirectory() as d:
        sp, pp = os.path.join(d, "in.svg"), os.path.join(d, "out.png")
        open(sp, "w").write(src)
        r = subprocess.run(["rsvg-convert", "-w", str(bw), "-h", str(bh), "--keep-aspect-ratio", "-o", pp, sp],
                           capture_output=True, timeout=30)
        if r.returncode != 0 or not os.path.exists(pp):
            return
        im = Image.open(pp).convert("RGBA")
    arr = np.asarray(im, dtype=np.float32)
    ih, iw = arr.shape[:2]
    ox, oy = bx + (bw - iw) / 2, by + (bh - ih) / 2
    for cell in (6, 3):                                    # coarse dabs, then fine ones
        pts = [(x, y) for y in range(0, ih, cell) for x in range(0, iw, cell)]
        random.shuffle(pts)
        for x, y in pts:
            blk = arr[y:y + cell, x:x + cell].reshape(-1, 4)
            a = blk[:, 3].mean() / 255
            if a < 0.08:
                continue
            c = blk[:, :3][blk[:, 3] > 20].mean(0) if (blk[:, 3] > 20).any() else blk[:, :3].mean(0)
            jit = random.uniform(-0.04, 0.06)
            pen.D(ox + x + cell / 2 + random.uniform(-0.6, 0.6), oy + y + cell / 2 + random.uniform(-0.6, 0.6),
                  cell * 0.75, pen.c(tuple(int(v) for v in c), jit), float(min(1.0, a * 1.05)))
    g = arr[:, :, :3].mean(2) * (arr[:, :, 3] / 255)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]; gy[1:-1, :] = g[2:, :] - g[:-2, :]
    mag = np.hypot(gx, gy)
    for y in range(2, ih - 2, 2):                          # crisp edges along contours
        for x in range(2, iw - 2, 2):
            n = mag[y, x]
            if n < 24 or arr[y, x, 3] < 60:
                continue
            ux, uy = float(-gy[y, x] / n), float(gx[y, x] / n)
            c = pen.c(tuple(int(v) for v in arr[y, x, :3]))
            pen.L(ox + x - ux * 2.2, oy + y - uy * 2.2, ox + x + ux * 2.2, oy + y + uy * 2.2, 1.4, c)


def draw_streaks(pen, p):
    """dramatic sunset cloud streaks: long brushy bands, underlit hot where they face the light"""
    lx = pen.X(p["x"])
    for _ in range(int(p["count"])):
        y = pen.Y(random.uniform(p["y0"], p["y1"]))
        cx = random.uniform(-0.1, 1.1) * pen.W
        L = random.uniform(0.12, 0.4) * pen.W
        th = random.uniform(4, 14)
        near = max(0.0, 1 - abs(cx - lx) / (pen.W * 0.6))
        low = (y - pen.Y(p["y0"])) / max(1, pen.Y(p["y1"]) - pen.Y(p["y0"]))
        body = mix(rgb(p["color"]), rgb(p["lit"]), 0.25 * near)
        for k in range(int(L / 3)):
            t = k / (L / 3)
            xx = cx - L / 2 + t * L
            yy = y + math.sin(t * 3 + cx) * th * 0.4
            wdt = th * math.sin(t * math.pi) ** 0.6
            pen.D(xx, yy, wdt, pen.c(body), 0.35)
            pen.D(xx, yy + wdt * 0.55, wdt * 0.45, pen.c(mix(rgb(p["lit"]), (255, 230, 120), 0.3 * near)),
                  0.25 + 0.5 * near * (0.4 + low))


def finish(pen):
    """after every layer: a wet street mirrors the lights standing on or above it"""
    wet = getattr(pen.s, "_wet", None)
    if not wet:
        return
    x, top, w, shine = wet
    for lx, ly, col, r in getattr(pen.s, "_lights", []):
        if ly > top + 30 or r < 3:
            continue
        t0 = max(top + 4, ly + (top - ly) * -0.05)
        if abs(lx - x) > w / 2:
            continue
        for _ in range(int(14 + r * 0.8)):                               # soft broken streak below it
            t = random.random() ** 1.3
            yy = top + 6 + t * (pen.H - top - 6)
            half = w * 0.02 + (w / 2 - w * 0.02) * ((yy - top) / (pen.H - top))
            xx = lx + random.gauss(0, r * 0.35 * (0.5 + t))
            if abs(xx - x) > half:
                continue
            for k in range(4):
                pen.D(xx, yy + k * 3, random.uniform(1.5, 3.5), pen.c(mix(col, shine, 0.25)), 0.22 * (1 - t * 0.6))
    for _ in range(int(w * 0.8)):                                         # general sheen
        t = random.random() ** 0.7
        yy = top + t * (pen.H - top)
        half = w * 0.02 + (w / 2 - w * 0.02) * t
        xx = x + random.uniform(-half, half)
        pen.D(xx, yy, random.uniform(1, 2.5), pen.c(shine), 0.25)


DRAW = {k: globals()["draw_" + k] for k in OBJECTS}


# -------------------------------------------------------------------------- free shapes
def draw_shapes(pen, p):
    """{"type": "shapes", "items": [ {"shape": "polygon", "points": [[x,y],...], "color": "#hex"},
    {"shape": "circle", "x":, "y":, "r":, "color":}, {"shape": "ellipse", "x":, "y":, "rx":, "ry":},
    {"shape": "line", "points": [[x,y],...], "width": 0.004, "color":},
    {"shape": "glow", "x":, "y":, "r":, "color":, "strength": 1}, {"shape": "text", ...}]}"""
    import art as A
    for it in p.get("items", [])[:80]:
        try:
            k, col = it.get("shape"), it.get("color", "#808080")
            if k == "polygon":
                pen.poly([(pen.X(a), pen.Y(b)) for a, b in it["points"]], col)
            elif k == "circle":
                pen.ellipse(pen.X(it["x"]), pen.Y(it["y"]), pen.S(it["r"]), pen.S(it["r"]), col)
            elif k == "ellipse":
                pen.ellipse(pen.X(it["x"]), pen.Y(it["y"]), pen.S(it["rx"]), pen.S(it["ry"]), col)
            elif k == "line":
                pen.line([(pen.X(a), pen.Y(b)) for a, b in it["points"]], max(1.0, pen.S(it.get("width", 0.004))), col)
            elif k == "glow":
                pen.glow(pen.X(it["x"]), pen.Y(it["y"]), pen.S(it.get("r", 0.05)), col, float(it.get("strength", 1)))
            elif k == "text":
                A.text(pen.s.a, str(it.get("text", ""))[:40], pen.X(it.get("x", 0.5)), pen.Y(it.get("y", 0.5)),
                       int(pen.S(it.get("size", 0.04))), 1, pen.c(col))
        except Exception:
            continue            # a malformed item is skipped, never a crash
