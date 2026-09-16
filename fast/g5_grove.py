"""GEN 5 — FIRST LIGHT IN THE GROVE. Built to GEN5_RULES.md.

PROMPT: "A redwood grove in fog at first light, with shafts of sun coming through the trees."

Read as light: fog is the medium, shafts are the subject, trunks are what interrupts them. So
the trunks are not drawn as objects with edges — they are the places the fog stops being lit.
Fog is the most extreme atmospheric perspective available, which makes distance do almost all
the work: a trunk forty metres back is a slightly darker column of fog and nothing more.
"""
import asyncio, math, random, sys
import art as A
from art import Art, mix, TOPBAR
import g3lib as G
import g5lib as G5

GRAY = (len(sys.argv) > 1 and sys.argv[1] == "gray")
A.GEN = "5TH GEN" + (" · FLAT GRAY TEST" if GRAY else "")
random.seed(5200)
W, H = 1380, 900
a = Art(W, H, "FIRST LIGHT IN THE GROVE")
R, L, D = a.R, a.L, a.D
P = G5.Paint(a, GRAY); col = P.col

GND  = H * 0.86                       # where the nearest trunks meet the ground
SUNX = W * 0.72                       # sun low and behind, off to the right
SUNY = TOPBAR + 30
TO_SUN = (0.46, -0.89)

FOG_NEAR = (86, 96, 92)               # fog close to the camera, in shadow: cool and dim
FOG_FAR  = (214, 214, 198)            # fog at distance, full of scattered light
SHAFT_C  = (255, 238, 196)            # the shafts themselves
BARK     = (74, 52, 42)
BARK_LIT = (188, 128, 84)
DUFF     = (52, 44, 34)

def fog_value(y, depth):
    """fog brightens with distance because there is more lit air between you and the subject.
    This is why anything far away in fog is LIGHTER, not darker."""
    up = G.frac(y, TOPBAR, GND)
    return 0.30 + 0.48 * depth + 0.14 * (1.0 - up)

def fog_hue(y, depth):
    return mix(FOG_NEAR, FOG_FAR, depth ** 0.7)

def shaft_at(x, y):
    """A shaft is a volume of lit fog between the camera and everything else. It runs from the
    sun down and to the left, it is soft-edged, and it is BRIGHTEST where it passes through the
    most fog — so it strengthens with distance from the source, then fades."""
    t = G.frac(y, SUNY, GND)     # CLAMPED. Hand-dividing here let t go negative
                                 # above the sun, and (-x) ** 0.55 returns a COMPLEX number.
    v = 0.0
    for k, (ox, wd, amp) in enumerate([(-30, 54, 1.0), (120, 38, 0.8), (-190, 66, 0.9),
                                       (260, 30, 0.6), (-330, 44, 0.7), (400, 52, 0.75)]):
        cx = SUNX + ox + t * (GND - SUNY) * (TO_SUN[0] / -TO_SUN[1]) * -1.0
        half = wd * (0.55 + 1.45 * t)
        d = (x - cx) / half
        v += amp * math.exp(-d * d * 1.25)
    return v * math.sin(min(1.0, t * 1.15) * math.pi) ** 0.55

def build():
    # ---- the fog itself, which IS the background. Value rises with distance.
    for y in range(TOPBAR, H, 2):
        NC = 120
        for k in range(NC):
            x0 = W * k / NC; xm = x0 + W / (2.0 * NC)
            dep = 0.86
            v = fog_value(y, dep) + shaft_at(xm, y) * 0.22
            R(x0, y, W / NC + 2, 3, col(v, mix(fog_hue(y, dep), SHAFT_C,
                                               min(0.55, shaft_at(xm, y) * 0.5)), 0.5))

    # ---- the forest floor: duff, ferns, and the light that reaches it
    for y in range(int(GND - 70), H, 2):
        d = G.frac(y, GND - 70, H)
        for k in range(60):
            x0 = W * k / 60; xm = x0 + W / 120
            # feather the floor up into the fog instead of butting against it
            blend = G.frac(y, GND - 70, GND + 30)
            v = (0.30 - 0.16 * d) + shaft_at(xm, y) * 0.30
            fv = fog_value(y, 0.8)
            v = fv * (1 - blend) + v * blend
            hue = mix(fog_hue(y, 0.8),
                      mix(DUFF, SHAFT_C, min(0.5, shaft_at(xm, y) * 0.45)), blend)
            R(x0, y, W / 60 + 2, 3, col(v, hue, 0.6))

    # ---- TRUNKS, far to near. A distant trunk is a slightly darker column of fog; a near one
    # is a lit cylinder. Everything about it — value, contrast, grain, edge softness — comes
    # from how much fog is in front of it.
    # v1 made 46 trunks of constant width ending on one line: rectangular slabs, not trees.
    # A redwood TAPERS, its base flares, and the ground it stands on recedes so no two bases
    # sit at the same height.
    trunks = []
    for i in range(26):
        depth = random.random() ** 0.55                 # 0 far, 1 near
        trunks.append(dict(depth=depth,
                           x=random.uniform(-W*0.12, W*1.12),
                           w=6 + 74 * depth ** 1.7,
                           top=TOPBAR - 30 - 90 * (1 - depth),
                           base=GND - (1 - depth) * (GND - TOPBAR) * 0.50
                                + random.uniform(-26, 26) * depth,
                           lean=random.uniform(-0.022, 0.022)))
    trunks.sort(key=lambda t: t["depth"])
    for t in trunks:
        dep = t["depth"]
        def half_at(yy, t=t):
            # taper up the trunk, with a flare in the bottom fifth where it meets the ground
            u = G.frac(yy, t["top"], t["base"])
            taper = 0.55 + 0.45 * u
            flare = 1.0 + 0.30 * max(0.0, (u - 0.80) / 0.20) ** 1.7
            return t["w"] * 0.5 * taper * flare
        half = half_at(t["base"])
        fogv = fog_value(t["base"], 1.0 - dep * 0.92)
        fogh = fog_hue(t["base"], 1.0 - dep * 0.92)
        veil = (1.0 - dep) ** 0.75                      # how much fog sits in front of it
        step = 2 if dep > 0.4 else 3
        y = t["top"]
        while y < t["base"]:
            cx = t["x"] + t["lean"] * (y - t["top"])
            hw = half_at(y)
            k = -hw
            while k <= hw:
                u = k / max(1.0, hw)
                nz = math.sqrt(max(0.0, 1 - u*u))
                nx = u
                lit = G5.shade(nx, -0.25, TO_SUN, ambient=0.34)
                lit *= (0.35 + 0.65 * min(1.0, shaft_at(cx + k, y) * 1.3 + 0.35))
                v = 0.055 + 0.42 * lit
                hue = G5.temp(lit, BARK_LIT, BARK)
                # the fog in front: everything tends toward the fog as distance grows
                # dissolve into the fog toward the base — the farther the trunk, the higher
                # up it starts disappearing. v1 cut them off and they hung in the air.
                down = G.frac(y, t["base"] - (t["base"] - t["top"]) * (0.14 + 0.55*(1-dep)),
                              t["base"])
                melt = min(0.97, veil * 0.94 + down * (1.0 - dep) * 0.95)
                v = v * (1 - melt) + fogv * melt
                hue = mix(hue, fogh, min(0.97, melt))
                R(cx + k, y, step + 1, step + 1, col(v, hue, 0.55 * dep + 0.12))
                k += step
            y += step
        # bark grain only where it can actually be resolved
        if dep > 0.55:
            for _ in range(int(2200 * (dep - 0.55) / 0.45)):
                gy = random.uniform(t["top"], t["base"])
                hw = half_at(gy)
                gk = random.uniform(-hw, hw)
                cx = t["x"] + t["lean"] * (gy - t["top"])
                u = gk / max(1.0, hw)
                lit = G5.shade(u, -0.25, TO_SUN, ambient=0.34)
                lit *= (0.35 + 0.65 * min(1.0, shaft_at(cx+gk, gy) * 1.3 + 0.35))
                v = 0.055 + 0.42 * lit + random.uniform(-0.05, 0.05)
                v = v * (1 - veil*0.94) + fogv * veil * 0.94
                L(cx + gk, gy, cx + gk + random.gauss(0, 1.2), gy + random.uniform(6, 26),
                  random.uniform(0.6, 1.6), col(v, G5.temp(lit, BARK_LIT, BARK), 0.5), )
        # the trunk's own base sits in the duff, not on it
        for _ in range(int(240 * dep)):
            D(t["x"] + random.gauss(0, half*0.9), t["base"] + random.gauss(0, 7),
              random.uniform(3, 12), col(0.10 + 0.08*dep, DUFF, 0.5), 0.10)

    # ---- THE SHAFTS, as volume in the air IN FRONT of everything. This is the subject.
    for _ in range(46000):
        x = random.uniform(-60, W + 60); y = random.uniform(TOPBAR, GND + 40)
        s = shaft_at(x, y)
        if s < 0.06: continue
        D(x, y, random.uniform(3, 16), col(min(0.97, 0.66 + 0.32*s), SHAFT_C, 0.45),
          min(0.085, 0.012 + 0.075 * s))
    # motes, visible only inside a shaft
    for _ in range(3000):
        x = random.uniform(0, W); y = random.uniform(TOPBAR, GND)
        s = shaft_at(x, y)
        if s < 0.35: continue
        D(x, y, random.uniform(0.7, 2.0), col(0.92, SHAFT_C, 0.35), min(0.8, 0.2 + 0.7*s))
    # a last veil of fog over the whole near field — many tiny, because it sits on bright ground
    G5.wash_tiny(a, 16000, (-40, W+40), (TOPBAR, H), 
                 lambda x, y: col(fog_value(y, 0.55), fog_hue(y, 0.55), 0.4), alpha=0.022)

build()
OUT = "g5_grove_gray.png" if GRAY else "g5_grove.png"
asyncio.run(G5.paint(a, OUT, {"subject": "first_light_in_the_grove",
    "prompt": "A redwood grove in fog at first light, with shafts of sun coming through the trees."},
    gray=GRAY, focal_y=H*0.6))
