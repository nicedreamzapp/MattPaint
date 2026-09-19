"""SCENE ENGINE — generation 6. Paints a picture from a short art-direction recipe, from scratch.

No images go in. The drawing knowledge lives HERE, written once from what gens 1-5 learned
(GEN5_RULES.md, TRICKS.md, CONSTRUCTION.md and the g5_* scripts), so the art director only has
to say WHAT to paint and where:

    {"title": "DAWN RIDGES", "seed": 7, "horizon": 0.70,
     "light": {"kind": "sun", "x": 0.62, "y": 0.25, "color": [255, 196, 132]},
     "sky":   {"top": [26, 42, 88], "horizon": [255, 178, 108]},
     "layers": [{"type": "ridges", "count": 5, "height": 0.35, "haze": 0.7}, ...]}

Positions are fractions of the canvas (0 = left/top, 1 = right/bottom). Layers are painted in
the order given, far to near. Every colour goes through a value first (Paint.col), so a recipe
also paints as a flat-gray construction test.

    python3 scene_engine.py recipe.json OUT.png [gray]      paint it (G5.paint: on screen, in view)
    PAINT_PREFLIGHT=1 python3 scene_engine.py recipe.json -  build only, no browser

LAYER TYPES — see LAYERS below for every parameter and its default.
"""
import asyncio, json, math, os, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

W, H = 1380, 900

LAYERS = {
    "clouds":  dict(amount=0.4, y=0.25, spread=0.18, color=[236, 226, 214]),
    "aurora":  dict(strength=1.0, colors=[[74, 240, 158], [58, 196, 224], [176, 96, 226]]),
    "ridges":  dict(count=5, top=0.45, bottom=1.0, height=0.30, haze=0.7,
                    rock=[120, 104, 96], seed=11),
    "hills":   dict(y=0.62, height=0.10, color=[40, 52, 44], seed=31),
    "water":   dict(top=0.60, stillness=0.85, tint=[40, 60, 80]),
    "meadow":  dict(top=0.72, lit=[206, 194, 116], dark=[62, 72, 40]),
    "canyon":  dict(opening=0.5, width=0.16, rock=[196, 104, 58], glow=[255, 196, 120]),
    "forest":  dict(kind="redwood", count=26, ground=0.86, near=1.0, far=0.0,
                    bark=[74, 52, 42], bark_lit=[188, 128, 84]),
    "pines":   dict(count=14, ground=0.80, height=0.30, color=[22, 34, 30]),
    "oak":     dict(x=0.46, ground=0.78, height=0.30, width=0.30, acorns=True,
                    leaf=[168, 186, 86], leaf_dark=[22, 44, 34]),
    "rocks":   dict(count=7, top=0.84, size=0.08, color=[112, 100, 90]),
    "fog":     dict(amount=0.5, top=0.2, bottom=1.0, color=[214, 214, 198]),
    "shafts":  dict(count=6, strength=0.8, spread=0.30, color=[255, 238, 196]),
    "stars":   dict(count=1600),
}

# 2026-09-18: towns, castles, ghosts, figures... and free shapes — see scene_objects.py
import scene_objects as SO
LAYERS.update(SO.OBJECTS)
LAYERS["shapes"] = dict(items=[])


def _merge(defaults, given):
    out = dict(defaults)
    out.update({k: v for k, v in given.items() if k != "type"})
    return out


class Scene:
    def __init__(self, recipe, gray=False):
        self.r = recipe
        self.gray = gray
        random.seed(int(recipe.get("seed", 1)))
        self.a = Art(W, H, str(recipe.get("title", "UNTITLED")).upper()[:40])
        self.P = G5.Paint(self.a, gray)
        # 2026-09-18: every landscape colour was capped near 0.6 saturation, so neon/black-light
        # prompts came out pastel. "vivid" (1.0 default, up to 1.6) lifts it for the whole scene.
        _viv = max(0.5, min(1.6, float(recipe.get("vivid", 1.0))))
        self.col = (lambda v, hue, sat=0.62: self.P.col(v, hue, min(1.0, sat * _viv))) if _viv != 1.0 else self.P.col
        self.R, self.L, self.D = self.a.R, self.a.L, self.a.D
        self.hor = H * float(recipe.get("horizon", 0.70))
        lt = recipe.get("light", {})
        self.lkind = lt.get("kind", "sun")
        self.lx = W * float(lt.get("x", 0.6))
        self.ly = TOPBAR + (self.hor - TOPBAR) * float(lt.get("y", 0.4))
        self.lcol = tuple(lt.get("color", [255, 214, 160]))
        self.lstr = float(lt.get("strength", 1.0))
        sk = recipe.get("sky", {})
        night = self.lkind in ("moon", "none") or recipe.get("time") == "night"
        self.night = night
        self.sky_top = tuple(sk.get("top", [8, 12, 30] if night else [52, 92, 160]))
        self.sky_hor = tuple(sk.get("horizon", [24, 34, 64] if night else [214, 196, 170]))
        self.glow = tuple(sk.get("glow", self.lcol))
        # 2026-09-18: a dusk sky was always bright pastel; a black-light or stormy sky needs to go dark
        # and saturated. sky.brightness scales the sky's value, sky.saturation its colour (0-1).
        self.sky_bright = max(0.2, min(1.5, float(sk.get("brightness", 1.0))))
        self.sky_sat = max(0.2, min(1.0, float(sk.get("saturation", 0.66))))
        self.aurora = None
        self.fog_amt = 0.0

    # ------------------------------------------------------------------ light model
    def to_light(self, x, y):
        """direction from a surface point toward the light, screen space (y down)"""
        dx = (self.lx - x) / W * 2.0
        dy = (self.ly - y) / H * 2.0 - 0.25
        n = math.hypot(dx, dy) or 1.0
        return dx / n, dy / n

    def lit(self, nx, ny, x, y, occ=0.0, ambient=0.30, bounce=0.0):
        """direct + sky fill + bounce − occlusion (GEN5_RULES: full lighting model)"""
        if self.lkind == "none":
            direct = 0.0
        else:
            tx, ty = self.to_light(x, y)
            direct = max(0.0, nx * tx + ny * ty) * self.lstr * (0.35 if self.lkind == "moon" else 1.0)
        sky = (max(0.0, -ny) * 0.5 + 0.5) * ambient
        return max(0.0, (direct * (1 - ambient) + sky + bounce * 0.3) * (1 - occ))

    def temp(self, amount, cool=(138, 170, 214)):
        """lit runs warm (the light's colour), shadow runs cool (skylight)"""
        return mix(cool, self.lcol, max(0.0, min(1.0, amount * 1.25)))

    # ------------------------------------------------------------------ sky
    def sky_value(self, x, y):
        t = G.frac(y, TOPBAR, self.hor)
        v = (0.05 + 0.10 * t) if self.night else (0.30 + 0.50 * t ** 0.7)
        if self.lkind != "none":
            dx = (x - self.lx) / (W * 0.46); dy = (y - self.ly) / (self.hor * 0.46)
            v += (0.12 if self.night else 0.38) * self.lstr * math.exp(-(dx * dx + dy * dy) * 0.8)
        if self.aurora:
            v += 0.68 * min(1.0, self.aurora_at(x, y)[0]) ** 0.75
        return min(0.985, v * self.sky_bright)

    def sky_hue(self, x, y):
        base = mix(self.sky_top, self.sky_hor, G.frac(y, TOPBAR, self.hor) ** 0.82)
        if self.lkind != "none":
            dx = (x - self.lx) / (W * 0.42); dy = (y - self.ly) / (self.hor * 0.42)
            near = math.exp(-(dx * dx + dy * dy) * 0.9)
            low = G.frac(y, TOPBAR, self.hor) ** 1.6          # the horizon warms, the zenith stays cool
            base = mix(base, self.glow, min(0.9, (near * 0.8 + low * 0.35) * (0.4 if self.night else 1.0)))
        if self.aurora:
            amt, c = self.aurora_at(x, y)
            base = mix(base, c, min(0.92, amt * 1.4))
        return base

    def paint_sky(self, rows_to=None):
        col, R, D = self.col, self.R, self.D
        for y in range(0, H, 4):                      # base coat: the canvas starts WHITE
            R(0, y, W, 5, col(self.sky_value(W / 2, min(y, self.hor)), self.sky_hor, 0.4))
        bottom = int(rows_to or self.hor) + 6
        NC = 110 if self.aurora else 60
        for y in range(TOPBAR - 2, bottom, 2):        # wide stretched rects, not dabs
            for k in range(NC):
                x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
                R(x0, y, W / NC + 2, 3, col(self.sky_value(xm, y), self.sky_hue(xm, y), self.sky_sat))
        if not self.night:                            # variation: many tiny (bright field)
            for _ in range(22000):
                x = random.uniform(-40, W + 40); y = random.uniform(TOPBAR, self.hor + 12)
                D(x, y, random.uniform(2.0, 6.5),
                  col(self.sky_value(x, y) + random.uniform(-0.05, 0.05), self.sky_hue(x, y), 0.55), 0.03)
        if self.lkind in ("sun", "moon"):
            self.paint_light_source()

    def paint_light_source(self):
        col, D = self.col, self.D
        sun = self.lkind == "sun"
        size = (700 if sun else 260) * self.lstr
        for k in range(190):                          # diffused into the air, never a clean disc
            u = k / 190.0
            D(self.lx + random.gauss(0, 3), self.ly + random.gauss(0, 2.4),
              size * (1 - u) ** 1.75 + (9 if sun else 6),
              col(0.70 + 0.29 * u * u, mix(self.glow, (255, 250, 240), u), 0.74),
              (0.0068 if sun else 0.009) * (u ** 2.2))
        for _ in range(1600 if sun else 500):
            ang = random.uniform(0, 6.2832); r = random.random() ** 0.40 * (210 if sun else 70)
            D(self.lx + math.cos(ang) * r * 1.25, self.ly + math.sin(ang) * r * 0.66,
              random.uniform(14, 46) * (1 if sun else 0.5), col(0.93, self.glow, 0.68), 0.016)

    # ------------------------------------------------------------------ layers
    def stars(self, p):
        for _ in range(int(p["count"])):
            x = random.uniform(0, W); y = random.uniform(TOPBAR, self.hor)
            if self.aurora and self.aurora_at(x, y)[0] > 0.12 and random.random() < 0.7:
                continue
            self.D(x, y, random.uniform(0.6, 1.5), self.col(random.uniform(0.35, 0.92), (226, 232, 255), 0.3),
                   random.uniform(0.3, 0.9))

    def aurora_at(self, x, y):
        tot = 0.0; rr = gg = bb = 0.0
        p = self.aurora
        for i, c in enumerate(p["colors"][:3]):
            base = self.hor - 40 - i * 46 - 60 * G5.fbm(x * 0.004 + i * 3.1, 7.7, 3)
            top = base - 320 - i * 60
            if y > base or y < top:
                continue
            fold = G5.fbm(x * 0.0030 + i * 4.7, 0.5, 4)
            drift = (fold - 0.5) * 220
            band = math.exp(-(((x - (W * 0.5 + drift)) / (W * (0.34 + 0.08 * i))) ** 2) * 1.1)
            down = G.frac(y, top, base)
            ragged = G5.ridged(x * 0.010 + i * 9.1, y * 0.0016, 2, 3.0)
            v = max(0.0, band * (0.30 + 0.90 * ragged) * (down ** 0.7) * (1.0 - down * 0.25)) * p["strength"]
            if v <= 0:
                continue
            tot += v; rr += c[0] * v; gg += c[1] * v; bb += c[2] * v
        if tot <= 0:
            return 0.0, self.sky_top
        return tot, (rr / tot, gg / tot, bb / tot)

    def clouds(self, p):
        col = self.col
        n = int(4 + 10 * p["amount"])
        for _ in range(n):
            cx = random.uniform(0, W); cy = H * p["y"] + random.gauss(0, H * p["spread"] * 0.5)
            rx = random.uniform(80, 240); ry = rx * random.uniform(0.18, 0.32)
            # a cloud is lit from the light's side and cool underneath; soft, never outlined
            for _ in range(int(900 * p["amount"] + 300)):
                a = random.uniform(0, 6.2832); r = random.random() ** 0.6
                x = cx + math.cos(a) * rx * r; y = cy + math.sin(a) * ry * r
                ny = -math.sin(a); nx = math.cos(a)
                l = self.lit(nx * 0.6, ny, x, y, ambient=0.45)
                v = min(0.97, self.sky_value(x, y) * 0.75 + 0.30 * l)
                self.D(x, y, random.uniform(6, 20), col(v, self.temp(l, tuple(p["color"])), 0.45), 0.05)

    def ridges(self, p):
        """faceted terrain organised by drainage, lit by the full model (g5_ridges)"""
        col, R, D = self.col, self.R, self.D
        n = max(1, int(p["count"]))
        rock = tuple(p["rock"])
        for i in range(n):
            depth = (i + 1) / n                                  # far -> near
            base_y = H * (p["top"] + (p["bottom"] - p["top"]) * (i / max(1, n - 1)) ** 0.9)
            amp = H * p["height"] * (0.45 + 0.55 * depth)
            h0 = G5.envelope(int(p["seed"]) + i * 12, W, base_y, amp, 3 + (i % 2))
            h = lambda x, h0=h0: max(TOPBAR + 30, min(H + 40, h0(x)))
            ridges = G5.drainage(900 + i, int(6 + 14 * depth), W, h)
            jit = 0.10 + 0.34 * depth
            sat = 0.18 + 0.56 * depth
            floor = (0.28 - 0.22 * depth) if not self.night else 0.04
            haze = p["haze"] * (1 - depth) ** 1.2
            step_y = 3 + int(4 * (1 - depth))
            x = 0.0
            while x < W:
                cy = h(x)
                y = cy
                while y < H + 6:
                    nx, ny = G5.terrain_normal(x, y, ridges, jit)
                    down = G.frac(y, cy, H)
                    occ = 0.42 * down ** 1.5 + 0.22 * max(0.0, 0.5 - abs(nx)) * down
                    tx, ty = self.to_light(x, y)
                    direct = max(0.0, nx * tx + ny * ty) * (0.0 if self.lkind == "none" else self.lstr)
                    if self.ly < self.hor:           # light behind the range: facing planes are backlit
                        direct *= 0.55
                    skyf = max(0.0, -ny) * 0.5 + 0.5
                    bounce = max(0.0, 1.0 - direct) * down * 0.30
                    I_sun, I_sky, I_bnc = 0.20 + 0.16 * depth, 0.26 - 0.16 * depth, 0.05 + 0.13 * depth
                    v = floor + I_sun * direct ** 1.15 + I_sky * skyf * 0.5 + I_bnc * bounce
                    v *= 1.0 - min(0.78, occ) * (0.45 + 0.35 * depth)
                    l = min(1.0, direct * 1.25)
                    hue = mix(mix((138, 170, 214), rock, 0.45), self.lcol, l)
                    # distance loses information: lift toward the sky colour and value
                    sv = self.sky_value(x, self.hor - 10)
                    v = v * (1 - haze) + sv * haze * 0.95
                    hue = mix(hue, self.sky_hue(x, self.hor - 10), haze)
                    R(x, y, 3, step_y + 1, col(max(0.02, v), hue, sat))
                    y += step_y
                x += 2.0
            if depth > 0.25:                                     # grain only where resolvable
                gr = 0.9 + 3.2 * (1 - depth)
                for _ in range(int(6000 * depth)):
                    gx = random.uniform(0, W); cy = h(gx)
                    gy = cy + random.random() ** 0.55 * (H - cy)
                    nx, ny = G5.terrain_normal(gx, gy, ridges, jit)
                    l = self.lit(nx, ny, gx, gy, ambient=0.2)
                    v = floor + 0.40 * l + random.uniform(-0.05, 0.05)
                    D(gx, gy, gr * random.uniform(0.55, 1.5),
                      col(max(0.02, v), mix(rock, self.lcol, min(1, l)), sat), 0.11)
            hz = 0.60 + 0.28 * (1 - depth)                       # the haze that buries the next range
            for _ in range(int(4800 * (1.15 - depth) * (0.4 + p["haze"]))):
                hx = random.uniform(-120, W + 120); hy = h(hx) + random.uniform(-10, 70)
                D(hx, hy, random.uniform(3.0, 11.0),
                  col(hz if not self.night else 0.08, mix(self.sky_hue(hx, max(TOPBAR, hy)), self.glow, 0.22), 0.36),
                  0.026)

    def hills(self, p):
        h = G5.envelope(int(p["seed"]), W, H * p["y"], H * p["height"], 3)
        for x in range(0, W, 3):
            y = h(x)
            v = 0.025 if self.night else 0.18 + 0.45 * self.sky_value(x, self.hor) * 0.6
            self.R(x, y, 4, H * p["y"] - y + 8, self.col(v, mix(tuple(p["color"]), self.sky_hor, 0.25), 0.5))

    def water(self, p):
        """a still surface repeats everything above it, dimmer, smeared by the faintest movement"""
        top = H * p["top"]
        still = p["stillness"]
        src = [o for o in self.a.ops if (o[2] < top)]
        tint = tuple(p["tint"])
        dim = 0.72
        for o in src:
            if o[0] == 0:                                        # rect
                _, x, y, w, hh, r, g, b = o
                ny = 2 * top - y - hh
                if ny > H or ny + hh < top:
                    continue
                d = G.frac(ny, top, H)
                sm = (1 - still) * (6 + 30 * d) * (G5.vnoise(x * 0.01, ny * 0.05) - 0.5)
                c = mix((r * dim, g * dim, b * dim), tint, 0.18)
                self.a.ops.append([0, int(x + sm), int(max(top, ny)), int(w), int(hh), int(c[0]), int(c[1]), int(c[2])])
            elif o[0] == 2:                                      # dab
                _, x, y, r, g, b, rad, al = o
                ny = 2 * top - y
                if ny > H + rad or ny < top - rad:
                    continue
                c = mix((r * dim, g * dim, b * dim), tint, 0.18)
                self.a.ops.append([2, x, round(ny, 1), int(c[0]), int(c[1]), int(c[2]), rad, al])
        # the surface itself: long horizontal glints where the water is not quite still
        for _ in range(int(26000 * (1.2 - still))):
            y = top + random.random() ** 0.75 * (H - top)
            x = random.uniform(0, W)
            d = G.frac(y, top, H)
            sy = max(TOPBAR, 2 * top - y)
            v = self.sky_value(x, sy)
            if v < 0.25:
                continue
            self.L(x, y, x + random.uniform(4, 30) * (0.5 + d), y + random.gauss(0, 0.8),
                   random.uniform(0.5, 1.6), self.col(min(0.95, v * 0.9), self.sky_hue(x, sy), 0.6))

    def meadow(self, p):
        col = self.col
        top = H * p["top"]
        lit_c, dk = tuple(p["lit"]), tuple(p["dark"])
        for y in range(int(top), H, 2):
            d = G.frac(y, top, H)
            for k in range(70):
                x0 = W * k / 70; xm = x0 + W / 140
                l = self.lit(0, -1, xm, y, ambient=0.35) * (0.8 + 0.4 * G5.fbm(xm * 0.004, y * 0.01, 3))
                v = (0.10 if self.night else 0.22) + 0.40 * l * (0.7 + 0.3 * d)
                hue = mix(dk, lit_c, min(1, l))
                haze = (1 - d) ** 3 * 0.5
                v = v * (1 - haze) + self.sky_value(xm, self.hor - 5) * haze
                self.R(x0, y, W / 70 + 2, 3, col(v, mix(hue, self.sky_hor, haze), 0.6))
        for _ in range(int(40000)):                              # grass: detail grows toward us
            y = top + random.random() ** 0.6 * (H - top)
            d = G.frac(y, top, H)
            x = random.uniform(0, W)
            ln = 2 + 16 * d ** 1.6
            lean = random.gauss(0, 0.35)
            l = self.lit(lean, -1, x, y, ambient=0.35)
            v = (0.10 if self.night else 0.20) + 0.46 * l + random.uniform(-0.06, 0.06)
            self.L(x, y, x + lean * ln, y - ln, 0.5 + 1.2 * d, col(v, mix(dk, lit_c, min(1, l)), 0.6))

    def canyon(self, p):
        """two walls of layered rock, lit only by light bounced down from a slot far above"""
        col = self.col
        ox = W * p["opening"]; half = W * p["width"] / 2
        rock, glow = tuple(p["rock"]), tuple(p["glow"])
        for y in range(TOPBAR - 2, H, 2):
            t = G.frac(y, TOPBAR, H)
            gap = half * (1 - 0.55 * t) + 18 * (G5.fbm(y * 0.01, 3.3, 3) - 0.5)
            for side in (-1, 1):
                edge = ox + side * gap
                xs = range(0, int(edge), 3) if side < 0 else range(int(edge), W, 3)
                for x in xs:
                    dist = abs(x - edge) / W
                    strata = G5.fbm(x * 0.002, y * 0.03, 3)
                    bounce = math.exp(-dist * 9) * (1 - t * 0.6)
                    v = 0.05 + 0.55 * bounce * (0.7 + 0.5 * strata)
                    self.R(x, y, 4, 3, col(v, mix(rock, glow, bounce), 0.7))
        for _ in range(30000):                                   # light falling down the slot
            y = random.uniform(TOPBAR, H); t = G.frac(y, TOPBAR, H)
            x = ox + random.gauss(0, half * (1 - 0.5 * t) * 0.6)
            self.D(x, y, random.uniform(3, 12), col(0.8 - 0.3 * t, glow, 0.45), 0.03 * (1 - t) + 0.01)

    def fog_at(self, y, p):
        return p["amount"] * G5.env(G.frac(y, H * p["top"], H * p["bottom"]), 0.6)

    def fog(self, p):
        """many tiny over bright ground, few huge over dark (TRICKS: two safe regimes)"""
        c = tuple(p["color"])
        v = 0.12 if self.night else 0.80
        G5.wash_tiny(self.a, int(22000 * p["amount"]), (-40, W + 40), (H * p["top"], H * p["bottom"]),
                     lambda x, y: self.col(v, c, 0.4), alpha=0.028 * p["amount"] + 0.004)
        G5.wash_huge(self.a, int(900 * p["amount"]), (-100, W + 100), (H * p["top"], H * p["bottom"]),
                     lambda x, y: self.col(v, c, 0.4), alpha=0.012)

    def shaft_at(self, x, y, p):
        t = G.frac(y, self.ly, H * 0.9)
        v = 0.0
        offs = [(-30, 54, 1.0), (120, 38, 0.8), (-190, 66, 0.9), (260, 30, 0.6), (-330, 44, 0.7),
                (400, 52, 0.75), (-470, 40, 0.6), (530, 36, 0.5)][:max(1, int(p["count"]))]
        slope = (W * 0.5 - self.lx) / max(200.0, H * 0.9 - self.ly) * p["spread"] * 2
        for ox, wd, amp in offs:
            cx = self.lx + ox + t * (H * 0.9 - self.ly) * slope
            half = wd * (0.55 + 1.45 * t)
            d = (x - cx) / half
            v += amp * math.exp(-d * d * 1.25)
        return v * math.sin(min(1.0, t * 1.15) * math.pi) ** 0.55 * p["strength"]

    def shafts(self, p):
        c = tuple(p["color"])
        for _ in range(46000):
            x = random.uniform(-60, W + 60); y = random.uniform(TOPBAR, H)
            s = self.shaft_at(x, y, p)
            if s < 0.06:
                continue
            self.D(x, y, random.uniform(3, 16), self.col(min(0.97, 0.66 + 0.32 * s), c, 0.45),
                   min(0.085, 0.012 + 0.075 * s))
        for _ in range(3000):                                    # motes, only inside a shaft
            x = random.uniform(0, W); y = random.uniform(TOPBAR, H)
            s = self.shaft_at(x, y, p)
            if s > 0.35:
                self.D(x, y, random.uniform(0.7, 2.0), self.col(0.92, c, 0.35), min(0.8, 0.2 + 0.7 * s))

    def forest(self, p):
        """trunks far to near; a far trunk is a darker column of fog, a near one a lit cylinder"""
        col = self.col
        gnd = H * p["ground"]
        bark, bark_lit = tuple(p["bark"]), tuple(p["bark_lit"])
        fogc = tuple(self.r.get("fog_color", [214, 214, 198]))
        trunks = []
        for _ in range(int(p["count"])):
            depth = p["far"] + (p["near"] - p["far"]) * random.random() ** 0.55
            trunks.append(dict(depth=depth, x=random.uniform(-W * 0.12, W * 1.12),
                               w=(6 + 74 * depth ** 1.7) * (1.0 if p["kind"] == "redwood" else 0.45),
                               top=TOPBAR - 30 - 90 * (1 - depth),
                               base=gnd - (1 - depth) * (gnd - TOPBAR) * 0.50 + random.uniform(-26, 26) * depth,
                               lean=random.uniform(-0.022, 0.022)))
        trunks.sort(key=lambda t: t["depth"])
        duff = tuple(p.get("floor", [52, 44, 34]))
        for y in range(int(gnd - 70), H, 2):                     # the floor, feathered up into the fog
            d = G.frac(y, gnd - 70, H); blend = G.frac(y, gnd - 70, gnd + 30)
            for k in range(60):
                x0 = W * k / 60
                fv = 0.30 + 0.48 * 0.8 if not self.night else 0.06
                v = fv * (1 - blend) + (0.30 - 0.16 * d) * blend
                self.R(x0, y, W / 60 + 2, 3, col(v, mix(fogc, duff, blend), 0.6))
        for t in trunks:
            dep = t["depth"]
            def half_at(yy, t=t):
                u = G.frac(yy, t["top"], t["base"])
                return t["w"] * 0.5 * (0.55 + 0.45 * u) * (1.0 + 0.30 * max(0.0, (u - 0.80) / 0.20) ** 1.7)
            veil = (1.0 - dep) ** 0.75
            for _ in range(int(240 * dep)):                     # the base sits IN the duff, not on it
                self.D(t["x"] + random.gauss(0, t["w"] * 0.45), t["base"] + random.gauss(0, 7),
                       random.uniform(3, 12), col(0.10 + 0.08 * dep, duff, 0.5), 0.10)
            fogv = 0.30 + 0.48 * (1 - dep) if not self.night else 0.06
            step = 2 if dep > 0.4 else 3
            y = t["top"]
            while y < t["base"]:
                cx = t["x"] + t["lean"] * (y - t["top"])
                hw = half_at(y)
                k = -hw
                while k <= hw:
                    u = k / max(1.0, hw)
                    l = self.lit(u, -0.25, cx + k, y, ambient=0.34)
                    v = 0.055 + 0.42 * l
                    hue = mix(bark, bark_lit, min(1, l * 1.2))
                    down = G.frac(y, t["base"] - (t["base"] - t["top"]) * (0.14 + 0.55 * (1 - dep)), t["base"])
                    melt = min(0.97, veil * 0.94 + down * (1.0 - dep) * 0.95)
                    self.R(cx + k, y, step + 1, step + 1,
                           col(v * (1 - melt) + fogv * melt, mix(hue, fogc, melt), 0.55 * dep + 0.12))
                    k += step
                y += step
            if dep > 0.55:
                for _ in range(int(2200 * (dep - 0.55) / 0.45)):
                    gy = random.uniform(t["top"], t["base"]); hw = half_at(gy)
                    gk = random.uniform(-hw, hw); cx = t["x"] + t["lean"] * (gy - t["top"])
                    l = self.lit(gk / max(1.0, hw), -0.25, cx + gk, gy, ambient=0.34)
                    v = 0.055 + 0.42 * l + random.uniform(-0.05, 0.05)
                    self.L(cx + gk, gy, cx + gk + random.gauss(0, 1.2), min(t["base"] - 4, gy + random.uniform(6, 26)),
                           random.uniform(0.6, 1.6), col(v, mix(bark, bark_lit, min(1, l)), 0.5))

    def pines(self, p):
        """conifers: stacked, drooping branch tiers built from dabs; dark against the light"""
        col = self.col
        gnd = H * p["ground"]
        c = tuple(p["color"])
        for _ in range(int(p["count"])):
            depth = random.random()
            x = random.uniform(-40, W + 40)
            base = gnd + (depth - 0.5) * 40
            ht = H * p["height"] * (0.5 + 0.7 * depth)
            haze = (1 - depth) * 0.55
            for k in range(int(40 + 60 * depth)):
                u = k / (40 + 60 * depth)                         # 0 top .. 1 bottom
                y = base - ht * (1 - u)
                wdt = ht * 0.26 * u ** 0.9 * random.uniform(0.8, 1.15)
                for s in (-1, 1):
                    for j in range(int(3 + 9 * u)):
                        f = random.random()
                        bx = x + s * wdt * f
                        by = y + wdt * 0.22 * f * f                # branches droop
                        l = self.lit(s * 0.8, -0.4, bx, by, ambient=0.25)
                        v = 0.05 + 0.20 * l
                        sv = self.sky_value(bx, self.hor - 5)
                        self.D(bx, by, random.uniform(1.2, 3.5) * (0.6 + depth),
                               col(v * (1 - haze) + sv * haze, mix(c, self.lcol, l * 0.5), 0.5), 0.9)
            self.L(x, base - ht, x, base, 1 + 2 * depth, col(0.05, (40, 30, 24), 0.4))

    def oak(self, p):
        """a lone canopy is separate lit volumes with sky between them, never one dome (g5_oak)"""
        col = self.col
        tx, gnd = W * p["x"], H * p["ground"]
        th = H * p["height"]
        crx, cry = W * p["width"], H * p["height"] * 0.66
        ccx, ccy = tx, gnd - th - cry * 0.4
        leaf, dk = tuple(p["leaf"]), tuple(p["leaf_dark"])
        rl = random.Random(77)
        lobes = []
        for _ in range(9):
            a = rl.uniform(0, 6.2832); r = rl.random() ** 0.6
            lobes.append((ccx + math.cos(a) * crx * 0.62 * r, ccy + math.sin(a) * cry * 0.70 * r,
                          rl.uniform(0.26, 0.52) * crx, rl.uniform(0.30, 0.58) * cry))
        # shadow on the ground, away from the light
        sx = 1 if self.lx < tx else -1
        for _ in range(5000):
            x = tx + sx * random.random() * crx * 1.6 + random.gauss(0, crx * 0.3)
            y = gnd + random.gauss(0, 10) + abs(x - tx) * 0.04
            self.D(x, y, random.uniform(4, 14), col(0.10, (40, 50, 40), 0.4), 0.05)
        # trunk and limbs
        tw = W * 0.018
        yy = gnd
        while yy > gnd - th:                                     # trunk: a lit cylinder that tapers
            u = G.frac(yy, gnd - th, gnd)
            hw = tw * (0.7 + 0.3 * u) * (1 + 0.5 * max(0.0, u - 0.85) / 0.15)
            k = -hw
            while k <= hw:
                l = self.lit(k / hw, -0.1, tx + k, yy, ambient=0.25)
                self.R(tx + k, yy, 2, 2, col(0.05 + 0.32 * l, mix((34, 26, 20), (176, 148, 112), l), 0.5))
                k += 1.5
            yy -= 1.5
        for _ in range(7):                                       # limbs spreading into the lobes
            ang = -math.pi / 2 + random.uniform(-1.05, 1.05)
            G.fractal_branch(self.a, tx, gnd - th * random.uniform(0.85, 1.0), ang, th * 0.34, tw * 0.28,
                             col(0.12, (60, 46, 34), 0.5), col(0.04, (20, 16, 12), 0.4), maxd=4, spread=0.55)
        # lobes, back to front: outside lit and warm, inside deep and cool, holes to the sky
        for (cx, cy, rx, ry) in sorted(lobes, key=lambda l: l[1]):
            for _ in range(int(rx * ry * 0.06)):
                a = random.uniform(0, 6.2832); r = random.random() ** 0.55
                x = cx + math.cos(a) * rx * r; y = cy + math.sin(a) * ry * r
                if random.random() < 0.10 * r:
                    continue
                nx, ny = math.cos(a) * r, math.sin(a) * r - 0.2
                occ = (1 - r) * 0.55
                l = self.lit(nx, ny, x, y, occ=occ, ambient=0.28)
                v = 0.06 + 0.52 * l
                self.D(x, y, random.uniform(1.8, 5.5), col(v, mix(dk, leaf, min(1, l * 1.2)), 0.62), 1.0)
        if p.get("acorns"):
            for _ in range(900):
                cx, cy, rx, ry = random.choice(lobes)
                a = random.uniform(0, 6.2832); r = random.uniform(0.6, 1.0)
                x = cx + math.cos(a) * rx * r; y = cy + math.sin(a) * ry * r
                l = self.lit(math.cos(a), math.sin(a), x, y, ambient=0.3)
                self.D(x, y, random.uniform(1.2, 2.2), col(0.22 + 0.4 * l, (156, 116, 58), 0.7), 1.0)

    def rocks(self, p):
        col = self.col
        c = tuple(p["color"])
        for _ in range(int(p["count"])):
            x = random.uniform(0, W); y = H * p["top"] + random.random() * (H - H * p["top"])
            s = W * p["size"] * random.uniform(0.5, 1.4) * (0.6 + G.frac(y, H * p["top"], H))
            for _ in range(int(s * 18)):
                a = random.uniform(0, 6.2832); r = random.random() ** 0.5
                px = x + math.cos(a) * s * r; py = y + math.sin(a) * s * 0.55 * r
                if py > y + s * 0.2:
                    continue
                nx, ny = math.cos(a) * r, math.sin(a) * r - 0.3
                l = self.lit(nx, ny, px, py, occ=(1 - r) * 0.2, ambient=0.25)
                v = 0.06 + 0.45 * l + random.uniform(-0.04, 0.04)
                self.D(px, py, random.uniform(1.5, 4.5), col(v, mix(c, self.lcol, l * 0.6), 0.5), 1.0)
            for _ in range(int(s * 3)):                           # contact shadow: dark only where it touches
                self.D(x + random.gauss(0, s * 0.6), y + s * 0.2 + random.gauss(0, 3),
                       random.uniform(2, 6), col(0.05, (30, 30, 30), 0.3), 0.08)

    # ------------------------------------------------------------------ build
    def build(self):
        layers = list(self.r.get("layers", []))
        for l in layers:
            if l.get("type") == "aurora":
                self.aurora = _merge(LAYERS["aurora"], l)
        water = next((l for l in layers if l.get("type") == "water"), None)
        self.paint_sky()
        for l in layers:
            t = l.get("type")
            if t not in LAYERS or t == "aurora":
                continue
            if t in SO.DRAW:
                SO.DRAW[t](SO.Pen(self), _merge(LAYERS[t], l))
            elif t == "shapes":
                SO.draw_shapes(SO.Pen(self), _merge(LAYERS[t], l))
            else:
                getattr(self, t)(_merge(LAYERS[t], l))
        SO.finish(SO.Pen(self))
        return self.a


def render(recipe, out, gray=False):
    s = Scene(recipe, gray)
    a = s.build()
    A.GEN = str(recipe.get("gen_label", "6TH GEN")) + (" · FLAT GRAY" if gray else "")
    A.BY = os.environ.get("MATTPAINT_NAME") or str(recipe.get("painter", ""))
    return asyncio.run(G5.paint(a, out, {"subject": recipe.get("title", ""), "engine": "scene_engine",
                                         "recipe": recipe}, gray=gray, focal_y=H * 0.6))


if __name__ == "__main__":
    recipe = json.loads(open(sys.argv[1]).read())
    render(recipe, sys.argv[2] if len(sys.argv) > 2 else "scene.png", gray="gray" in sys.argv[3:])
