"""Film — a giant old robot has knelt in a misty forest for a century; dawn sun breaks through, its chest light wakes."""
import math, sys
import numpy as np
from pt import *

TITLE = "The sleeping giant"

# ---- easing helpers (every animated value is a smooth function of t) ----
def ss(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)

def mix(a, b, u):
    return tuple(float(p + (q - p) * u) for p, q in zip(a, b))

def chest_glow(t):
    if t < 0.7:
        return 0.0
    if t < 0.8:                                   # a few quick stutters as it wakes
        s = (t - 0.7) / 0.1
        return float(max(0.0, math.sin(s * math.pi * 7.0)) ** 3 * (0.25 + 0.6 * s))
    return 0.35 + 0.65 * ss(0.8, 0.9, t)          # then a steady glow

def mixc(a, b, m):
    return a * (1 - m[:, None]) + b * m[:, None]

# ---- geometry helpers ----
def frame(ydir, zhint=(0, 0, 1)):
    """rotation whose local y runs along ydir and local z leans toward zhint"""
    y = np.asarray(ydir, np.float64); y = y / np.linalg.norm(y)
    x = np.cross(y, np.asarray(zhint, np.float64)); x /= np.linalg.norm(x)
    return np.stack([x, y, np.cross(x, y)], 1).astype(f32)

def limb(sc, mat, p0, p1, hw, hd, zhint=(0, 0, 1), grow=0.0):
    p0, p1 = V(*p0), V(*p1); R = frame(p1 - p0, zhint); L = float(np.linalg.norm(p1 - p0))
    sc.add(Box(mat, (hw, L / 2 + grow, hd), R=R, T=tuple((p0 + p1) / 2)))
    return R, (p0 + p1) / 2, L

def frond(sc, mat, base, yaw, pitch, length, width):
    R = rot(yaw=yaw, pitch=pitch)                 # negative pitch arches the tip up
    c = V(*base) + R @ V(0, 0, length * 0.85)
    sc.add(Sphere(mat, R=R, T=tuple(c), S=(width, width * 0.12, length)))

def noise_bump(sxz, sy, k):
    def b(pl, pw, n):
        x, y, z = pw[:, 0] * sxz, pw[:, 1] * sy, pw[:, 2] * sxz
        v = np.stack([vnoise(x, y, z), vnoise(y + 3.1, z + 1.7, x), vnoise(z + 7.3, x + 2.9, y)], 1) - 0.5
        return (v * k).astype(f32)
    return b

def leaf_holes(pw, f):
    return np.clip((fbm(pw[:, 0] * f, pw[:, 1] * f, pw[:, 2] * f, oct=3) - 0.64) * 8, 0, 1)

PAUL = [(0, 0), (0.9, 0), (0.96, 0.1), (0.9, 0.32), (0.7, 0.55), (0.38, 0.68), (0, 0.72)]
HELM = [(0, 0), (0.55, 0), (0.6, 0.2), (0.6, 0.45), (0.52, 0.68), (0.34, 0.84), (0, 0.9)]
BEZEL = [(0.28, 0), (0.56, 0), (0.6, 0.05), (0.52, 0.13), (0.34, 0.13), (0.28, 0)]

# ---- textures (albedo before mist; shot() wraps them with the depth fog) ----
def armour_tex(pl, pw, n):
    x, y, z = pw[:, 0], pw[:, 1], pw[:, 2]
    lx, ly, lz = pl[:, 0], pl[:, 1], pl[:, 2]
    c = V(0.19, 0.20, 0.16)[None] * (0.7 + 0.6 * fbm(x * 1.3 + 11, y * 1.3, z * 1.3, oct=4)[:, None])   # faded olive paint
    chip = np.clip((fbm(x * 8 + 5, y * 8, z * 8, oct=4) - 0.58) * 9, 0, 1)                           # chipped to bare iron
    c = mixc(c, V(0.06, 0.055, 0.05), chip)
    # panel seams and rivet rows, in each plate's own coordinates
    gy = (ly / 0.55) % 1.0; dy = np.minimum(gy, 1 - gy) * 0.55
    gx = ((lx + lz) / 0.75) % 1.0; dx = np.minimum(gx, 1 - gx) * 0.75
    seam = np.clip(1 - np.minimum(dy, dx) / 0.02, 0, 1)
    c = c * (1 - 0.8 * seam[:, None])
    along = ((lx + lz) / 0.12) % 1.0
    riv = (np.abs(dy - 0.07) < 0.022) & (np.abs(along - 0.5) < 0.17)
    c = np.where(riv[:, None], c * 1.6 + 0.015, c)
    # rust: streaks running down from each panel line, out of the chips, and big blooms
    wy = (y / 0.55) % 1.0; below = (1 - wy) * 0.55
    st = fbm(x * 10, y * 0.45, z * 10, oct=4)
    rm = (np.clip((st - 0.47) * 5, 0, 1) * (0.25 + 0.75 * np.exp(-below / 0.35)) + chip * 0.7
          + np.clip((fbm(x * 1.5 + 3, y * 1.5, z * 1.5, oct=4) - 0.58) * 4, 0, 1))
    rcol = V(0.15, 0.065, 0.03)[None] + V(0.19, 0.075, 0.015)[None] * fbm(x * 14, y * 14, z * 14, oct=3)[:, None]
    c = mixc(c, rcol, np.clip(rm, 0, 1) * 0.85)
    # moss: thick on everything facing up, creeping up from the ground
    mn = fbm(x * 2.4 + 9, y * 2.4, z * 2.4, oct=4)
    up = np.clip(n[:, 1], 0, 1) ** 2
    low = np.clip((1.3 - y) / 1.3, 0, 1)
    mm = np.clip(np.maximum(up * 1.6 - 0.45, low * 1.1 - 0.2) + (mn - 0.5) * 1.8, 0, 1)
    mf = fbm(x * 20, y * 20, z * 20, oct=3)
    moss = (V(0.07, 0.13, 0.03)[None] + V(0.10, 0.07, 0.02)[None] * np.clip(mf * 2 - 0.8, 0, 1)[:, None]) * (0.6 + 0.7 * mf[:, None])
    return mixc(c, moss, mm).astype(f32)

def moss_tex(pl, pw, n):
    x, y, z = pw[:, 0], pw[:, 1], pw[:, 2]
    g = fbm(x * 5, y * 5, z * 5, oct=4); f = fbm(x * 22, y * 22, z * 22, oct=3)
    c = V(0.065, 0.125, 0.03)[None] * (0.5 + 0.8 * g[:, None]) + V(0.09, 0.07, 0.015)[None] * np.clip(f * 2 - 1.0, 0, 1)[:, None]
    return (c * (0.75 + 0.5 * f[:, None])).astype(f32)

def ground_tex(pl, pw, n):
    x, z = pw[:, 0], pw[:, 2]
    a = fbm(x * 0.3 + 2, z * 0.3, oct=4); b = fbm(x * 2.2 + 4, z * 2.2, oct=4); fine = fbm(x * 16, z * 16, oct=3)
    l1 = vnoise(x * 7, z * 7); l2 = vnoise(x * 7 + 31.7, z * 7 + 12.1)          # one value per fallen leaf
    leafc = mixc(V(0.17, 0.095, 0.045), V(0.27, 0.14, 0.05), np.clip(l2 * 1.6 - 0.4, 0, 1))
    leafc = mixc(leafc, V(0.07, 0.05, 0.035), np.clip((0.35 - l1) * 4, 0, 1))   # rotting leaves, soil
    leafc = leafc * (0.65 + 0.7 * fine[:, None])
    u = np.clip((a - 0.47) * 3.5 + (b - 0.5) * 1.4, 0, 1)
    rr = np.sqrt(x * x + z * z)
    u = np.maximum(u, np.clip((3.2 - rr) * 0.5 + (b - 0.5), 0, 1))              # moss spreading out from the robot
    moss = V(0.06, 0.115, 0.03)[None] * (0.6 + 0.8 * fbm(x * 9 + 3, z * 9, oct=3)[:, None])
    return mixc(leafc, moss, u).astype(f32)

def bark_tex(pl, pw, n):
    x, y, z = pw[:, 0], pw[:, 1], pw[:, 2]
    ridges = fbm(x * 7, y * 0.5, z * 7, oct=4)
    gro = np.clip((0.5 - ridges) * 5, 0, 1)                                     # deep vertical grooves
    c = V(0.14, 0.12, 0.10)[None] * (0.7 + 0.6 * fbm(x * 2, y * 2, z * 2, oct=3)[:, None]) * (1 - 0.8 * gro[:, None])
    lich = np.clip((fbm(x * 4 + 20, y * 4, z * 4, oct=3) - 0.62) * 6, 0, 1)
    c = mixc(c, V(0.32, 0.33, 0.26), lich * 0.7)
    side = np.clip(-n[:, 0] * 0.8 + 0.2 + np.clip(1.5 - y, 0, 1.5) * 0.4 + (fbm(x * 3, y * 3, z * 3, oct=3) - 0.5) * 1.2, 0, 1)
    return mixc(c, V(0.06, 0.12, 0.03), side).astype(f32)

def log_tex(pl, pw, n):
    c = bark_tex(pl, pw, n)
    up = np.clip(n[:, 1] * 1.6 - 0.2 + (fbm(pw[:, 0] * 3, pw[:, 1] * 3, pw[:, 2] * 3, oct=3) - 0.5), 0, 1)
    return mixc(c, moss_tex(pl, pw, n), up).astype(f32)

def rock_tex(pl, pw, n):
    x, y, z = pw[:, 0], pw[:, 1], pw[:, 2]
    g = fbm(x * 3, y * 3, z * 3, oct=4)
    c = V(0.2, 0.2, 0.19)[None] * (0.6 + 0.7 * g[:, None])
    c = mixc(c, V(0.36, 0.37, 0.3), np.clip((fbm(x * 6 + 40, y * 6, z * 6, oct=3) - 0.6) * 6, 0, 1))
    mm = np.clip(n[:, 1] * 1.4 - 0.4 + (g - 0.5) * 1.5, 0, 1)
    return mixc(c, moss_tex(pl, pw, n), mm).astype(f32)

def leaf_tex(pl, pw, n):
    x, y, z = pw[:, 0], pw[:, 1], pw[:, 2]
    g = fbm(x * 3, y * 3, z * 3, oct=4); spk = vnoise(x * 14, y * 14, z * 14)
    c = V(0.035, 0.065, 0.02)[None] * (0.4 + 1.2 * g[:, None]) + V(0.05, 0.08, 0.02)[None] * np.clip((spk - 0.65) * 4, 0, 1)[:, None]
    return (c * (1 - leaf_holes(pw, 1.1))[:, None]).astype(f32)

def fern_tex(pl, pw, n):
    lz, lx = pl[:, 2], pl[:, 0]
    leaflet = 0.5 + 0.5 * np.cos(lz * 34.0)                                    # pinnae across the frond
    c = V(0.07, 0.15, 0.035)[None] * (0.45 + 0.6 * leaflet[:, None]) * (0.7 + 0.6 * fbm(pw[:, 0] * 6, pw[:, 1] * 6, pw[:, 2] * 6, oct=3)[:, None])
    c = mixc(c, V(0.13, 0.16, 0.06), np.clip(1 - np.abs(lx) / 0.1, 0, 1) * 0.6)  # midrib
    c = mixc(c, V(0.09, 0.06, 0.03), np.clip((lz - 0.7) * 3, 0, 1))              # browning tips
    return (c * (1 - 0.5 * lx[:, None] ** 2)).astype(f32)

def const(alb):
    return lambda pl, pw, n: np.broadcast_to(V(*alb), pl.shape).astype(f32)


def shot(t):
    sc = Scene()
    rng = np.random.default_rng(41)               # fixed: nothing in the forest moves between frames

    # ---- time-dependent light: sun through a gap in the canopy, swinging a little ----
    amt = ss(0.12, 0.65, t)
    sd = norm(V(-0.62 + 0.10 * ss(0.0, 1.0, t), 0.72, 0.30))
    sd0 = norm(V(-0.57, 0.72, 0.30))
    target = V(0, 4.4, 0.4)                       # chest and head
    gap = target + sd0 * ((13.15 - target[1]) / sd0[1])
    sun_col = V(*mix((0.9, 0.6, 0.35), (1.0, 0.82, 0.55), ss(0.2, 0.9, t)))
    sc.set_sun(tuple(float(v) for v in sd), tuple(max(1e-4, float(c) * 5.5 * amt) for c in sun_col))
    w = ss(0.05, 0.95, t)
    fogL = V(*mix((0.09, 0.12, 0.19), (0.55, 0.46, 0.32), w))         # mist radiance: blue dawn to gold
    fogC = fogL * 1.15

    # ---- camera: slow push in, drifting left so the near trunks slide past ----
    u = ss(0.0, 1.0, t)
    pos = mix((1.5, 2.4, 15.0), (-0.7, 2.7, 11.5), u)
    look = mix((0.25, 3.3, 0.0), (0.0, 3.6, 0.4), u)
    C = V(*pos)

    # ---- atmosphere: depth mist and the sun shaft, both added as in-scattered light ----
    def fog(pw):
        d = np.linalg.norm(pw - C[None], axis=1)
        dens = (0.7 + 0.3 * np.exp(-np.clip(pw[:, 1], 0, None) / 5.0)) / 30.0
        return (1 - np.exp(-np.clip(d - 5.0, 0, None) * dens)).astype(f32)

    a = sd.astype(f32); A = gap.astype(f32)
    e1 = norm(np.cross(a, V(0, 0, 1))[None])[0]; e2 = np.cross(a, e1)
    c0 = C - A; c0 = c0 - (c0 @ a) * a
    def beam(P):
        uu = P - C[None]; ul = np.linalg.norm(uu, axis=1)
        cu = uu - (uu @ a)[:, None] * a[None]
        qa = (cu * cu).sum(1) + 1e-9; qb = cu @ c0
        tot = np.zeros(len(P), f32)
        for R, wt in ((2.2, 0.45), (1.4, 0.55)):                 # soft core inside a wider glow
            disc = qb * qb - qa * (c0 @ c0 - R * R)
            sq = np.sqrt(np.clip(disc, 0, None))
            s0 = np.clip((-qb - sq) / qa, 0, 1); s1 = np.clip((-qb + sq) / qa, 0, 1)
            tot += wt * (s1 - s0) * ul * (disc > 0)
        q = C[None] + uu * np.clip(-qb / qa, 0, 1)[:, None] - A[None]
        sax = q @ a                                               # 0 at the gap, negative going down
        tot *= np.clip(-sax / 1.5, 0, 1) * np.clip((sax + 16.0) / 4.0, 0, 1)
        q1, q2 = q @ e1, q @ e2; r = np.sqrt(q1 * q1 + q2 * q2) + 1e-6
        streak = 0.35 + 1.3 * vnoise(q1 / r * 2.5 + 5, q2 / r * 2.5 + 5)   # rays combed by the leaves
        return ((tot * streak * amt * 0.05)[:, None] * sun_col[None]).astype(f32)

    def glow(pl, pw, n):
        return (fog(pw)[:, None] * fogC[None] + beam(pw)).astype(f32)
    skyC = fogL * 1.6 + V(1.0, 0.8, 0.55) * 0.25 * amt
    def canopy_glow(f):                                           # sky specks through the leaves
        return lambda pl, pw, n: glow(pl, pw, n) + leaf_holes(pw, f)[:, None] * skyC[None]

    def M(kind, tex, g=glow, **k):
        return Mat(kind, tex=lambda pl, pw, n: (tex(pl, pw, n) * (1 - fog(pw))[:, None]).astype(f32), glow=g, **k)

    armour = M("plastic", armour_tex, f0=0.04, rough=0.55, bump=noise_bump(9, 9, 0.08))
    rim = M("metal", const((0.3, 0.27, 0.24)), rough=0.35)
    socket = M("diffuse", const((0.01, 0.01, 0.01)))
    mosspad = M("diffuse", moss_tex, bump=noise_bump(14, 14, 0.35))
    ground = M("diffuse", ground_tex, bump=noise_bump(8, 8, 0.25))
    bark = M("diffuse", bark_tex, bump=noise_bump(6, 0.8, 0.5))
    logm = M("diffuse", log_tex, bump=noise_bump(6, 6, 0.3))
    rock = M("diffuse", rock_tex, bump=noise_bump(5, 5, 0.3))
    leaves = M("diffuse", leaf_tex, g=canopy_glow(1.1))
    canopy = M("diffuse", leaf_tex, g=canopy_glow(0.9))
    fern = M("diffuse", fern_tex)

    # ---- the robot (faces +z, ~6 m tall kneeling; contacts checked: every part sits on/in the next) ----
    sc.add(Box(armour, (0.95, 0.4, 0.65), T=(0, 2.1, 0)))                       # pelvis, y 1.7..2.5
    sc.add(Box(armour, (0.78, 0.2, 0.6), T=(0, 2.62, 0.02)))                    # abdomen segment
    sc.add(Box(armour, (1.3, 1.0, 0.85), T=(0, 3.75, 0)))                       # torso, y 2.75..4.75
    for sx in (-1, 1):                                                          # bevelled breastplates in a shallow V
        sc.add(Box(armour, (0.6, 0.85, 0.08), R=rot(yaw=14 * sx), T=(0.6 * sx, 3.8, 0.93)))
    sc.add(Box(armour, (1.25, 0.08, 0.62), R=rot(pitch=16), T=(0, 4.72, 0.3)))  # sloped collar plate
    sc.add(Box(armour, (0.95, 0.75, 0.3), R=rot(pitch=-6), T=(0, 3.95, -1.05))) # backpack
    sc.add(Lathe(rim, BEZEL, R=rot(pitch=90), T=(0, 3.8, 1.05)))                # core bezel ring
    sc.add(Sphere(socket, T=(0, 3.8, 1.08), S=(0.32, 0.32, 0.06)))              # dark recess
    g = chest_glow(t)
    sc.sphere_light((0, 3.8, 1.13), 0.2, (0.55 * 5.0 * g, 0.95 * 5.0 * g, 1.0 * 5.0 * g), S=(0.26, 0.26, 0.07))
    sc.add(Cylinder(armour, 0.3, 0.55, T=(0, 4.68, 0.05)))                      # neck

    # head, bowed forward in sleep
    headR = rot(pitch=14); headT = V(0, 5.12, 0.08)
    def hp(v): return tuple(headR @ V(*v) + headT)
    sc.add(Lathe(armour, HELM, R=headR, T=tuple(headT), S=(1.15, 1.05, 1.2)))   # domed helmet
    sc.add(Box(armour, (0.46, 0.28, 0.1), R=headR, T=hp((0, 0.25, 0.7))))        # faceplate
    sc.add(Box(socket, (0.44, 0.05, 0.06), R=headR, T=hp((0, 0.5, 0.76))))       # visor slit
    sc.add(Box(armour, (0.56, 0.07, 0.14), R=headR @ rot(pitch=-8), T=hp((0, 0.63, 0.74))))   # visor ridge
    sc.add(Box(armour, (0.32, 0.11, 0.12), R=headR, T=hp((0, 0.0, 0.72))))       # chin
    sc.add(Sphere(mosspad, R=headR, T=hp((0.05, 0.9, -0.05)), S=(0.5, 0.13, 0.5)))   # moss cap
    hb = V(*hp((0.15, 0.95, -0.15)))
    for k in range(3):
        frond(sc, fern, tuple(hb), 40 + k * 120 + rng.uniform(-20, 20), -rng.uniform(30, 45), 0.3, 0.07)

    # shoulders and arms; big hands flat on the ground
    for sx in (-1, 1):
        Sh = V(1.95 * sx, 4.25, 0.0); E = V(2.3 * sx, 2.35, 0.15); Wr = V(2.45 * sx, 0.55, 1.2)
        pR = rot(yaw=6 * sx, roll=-28 * sx); pT = V(1.8 * sx, 4.35, 0.0)
        sc.add(Lathe(armour, PAUL, R=pR, T=tuple(pT), S=(1.0, 0.9, 0.95)))                          # pauldron
        sc.add(Lathe(armour, PAUL, R=rot(yaw=-4 * sx, roll=-52 * sx), T=(2.2 * sx, 3.92, 0.04), S=(0.75, 0.65, 0.8)))   # layered plate
        apex = pT + pR @ V(0, 0.62, 0)
        sc.add(Sphere(mosspad, R=pR, T=tuple(apex - pR @ V(0, 0.05, 0)), S=(0.55, 0.14, 0.5)))
        if sx == 1:
            for k in range(3):
                frond(sc, fern, tuple(apex + V(0, 0.05, 0)), k * 120 + rng.uniform(-25, 25), -rng.uniform(25, 40), 0.38, 0.08)
        Ru = frame(E - Sh); Lu = float(np.linalg.norm(E - Sh))
        sc.add(Lathe(armour, [(0, 0), (0.36, 0), (0.38, 0.12), (0.32, 0.3), (0.3, Lu - 0.1), (0.34, Lu), (0, Lu)], R=Ru, T=tuple(Sh)))
        Rp = frame(E - Sh, (sx, 0, 0.3))
        sc.add(Box(armour, (0.36, Lu * 0.34, 0.1), R=Rp, T=tuple((Sh + E) / 2 + Rp[:, 2] * 0.33)))  # upper-arm plate
        sc.add(Sphere(armour, T=tuple(E), S=(0.4, 0.4, 0.4)))                                       # elbow
        Rf, mid, Lf = limb(sc, armour, E, Wr, 0.36, 0.38, grow=0.1)                                 # forearm
        sc.add(Box(armour, (0.33, Lf * 0.4, 0.1), R=Rf @ rot(roll=3 * sx), T=tuple(mid + Rf[:, 2] * 0.4)))   # bracer
        sc.add(Box(armour, (0.42, 0.2, 0.44), R=rot(yaw=8 * sx, pitch=4), T=(2.52 * sx, 0.3, 1.55)))  # palm
        for k, fx in enumerate((-0.27, 0.0, 0.27)):
            sc.add(Box(armour, (0.11, 0.12, 0.3), R=rot(yaw=(8 + (k - 1) * 7) * sx, pitch=rng.uniform(-6, 6)),
                       T=(2.52 * sx + fx + 0.04 * sx, 0.13, 2.26)))

    # right leg: knee down, shin lying back along the ground
    R, mid, L = limb(sc, armour, (0.75, 2.0, -0.05), (0.75, 0.5, 0.55), 0.4, 0.42)
    sc.add(Box(armour, (0.36, L * 0.36, 0.1), R=R, T=tuple(mid + R[:, 2] * 0.4)))        # thigh plate
    sc.add(Sphere(armour, T=(0.75, 0.45, 0.6), S=(0.42, 0.42, 0.45)))                     # knee on the ground
    limb(sc, armour, (0.75, 0.45, 0.55), (0.75, 0.44, -1.35), 0.37, 0.38, zhint=(0, 1, 0))
    sc.add(Box(armour, (0.35, 0.28, 0.45), R=rot(pitch=-30), T=(0.75, 0.32, -1.8)))
    # left leg: knee up, foot planted forward
    limb(sc, armour, (-0.75, 2.0, 0.05), (-0.8, 2.3, 1.55), 0.42, 0.42, zhint=(0, 1, 0), grow=0.1)
    sc.add(Sphere(armour, T=(-0.8, 2.35, 1.67), S=(0.45, 0.45, 0.45)))                    # raised knee
    R, mid, L = limb(sc, armour, (-0.8, 2.3, 1.55), (-0.8, 0.5, 1.85), 0.38, 0.4)
    sc.add(Box(armour, (0.34, L * 0.38, 0.1), R=R @ rot(roll=-3), T=tuple(mid + R[:, 2] * 0.42)))   # shin plate
    sc.add(Box(armour, (0.42, 0.24, 0.62), T=(-0.8, 0.24, 2.05)))

    # ---- forest floor: litter, ferns, rocks, mossy mounds, a fallen log ----
    sc.add(Plane(ground))
    for (x, z, by) in ((1.9, 3.3, 10), (-3.6, 2.9, 40), (4.4, 0.6, 75)):
        for k in range(4):
            frond(sc, fern, (x, 0.05, z), by + k * 90 + rng.uniform(-20, 20), -rng.uniform(20, 40), rng.uniform(0.8, 1.0), 0.17)
    for (x, z, s) in ((-2.6, -1.2, (1.4, 0.45, 1.1)), (2.9, -2.2, (1.2, 0.4, 1.4)), (-5.5, 1.0, (2.2, 0.6, 1.6))):
        sc.add(Sphere(mosspad, R=rot(yaw=rng.uniform(0, 180)), T=(x, 0, z), S=s))
    sc.add(Sphere(rock, R=rot(yaw=30, roll=10), T=(3.6, 0.1, 2.0), S=(0.6, 0.4, 0.5)))
    sc.add(Sphere(rock, R=rot(yaw=-20, roll=-8), T=(-1.6, 0.05, 3.5), S=(0.4, 0.25, 0.35)))
    sc.add(Cylinder(logm, 0.5, 6.0, R=frame((1, 0.04, -0.4), (0, 1, 0)), T=(-9.5, 0.45, -2.5)))

    # ---- trunks with flaring roots: two near the lens for parallax, the rest fading into the mist ----
    for (x, z, r) in ((-2.6, 8.0, 0.42), (3.3, 7.0, 0.55),
                      (-7.5, -2.0, 0.85), (7.8, -4.0, 0.75), (-4.5, -9.0, 0.6), (3.5, -12.0, 0.7),
                      (-11.0, -15.0, 0.9), (10.0, -18.0, 0.8), (-1.5, -22.0, 0.75),
                      (6.5, -30.0, 1.0), (-15.0, -32.0, 1.1)):
        sc.add(Lathe(bark, [(0, 0), (2.1 * r, 0), (1.7 * r, 0.15), (1.35 * r, 0.5), (1.12 * r, 1.2),
                            (1.02 * r, 2.5), (0.9 * r, 16.0), (0, 16.0)], T=(x, 0, z)))
    for (x, z, r) in ((-7.5, -2.0, 0.85), (7.8, -4.0, 0.75)):
        for k in range(2):
            ang = rng.uniform(0, 360)
            sc.add(Sphere(bark, R=rot(yaw=ang, pitch=8), S=(0.32 * r, 0.28 * r, 1.7 * r),
                          T=(x + math.sin(math.radians(ang)) * 1.4 * r, 0.05, z + math.cos(math.radians(ang)) * 1.4 * r)))

    # ---- canopy: a leaf roof with one gap the sun pours through, and masses hanging into frame ----
    RIN = 2.7
    sc.add(Lathe(canopy, [(RIN, 0), (46, 0), (46, 0.7), (RIN, 0.7), (RIN, 0)], T=(float(gap[0]), 12.8, float(gap[2]))))
    for th in (0.4, 2.6):                                         # break the round edge of the gap
        sc.add(Sphere(leaves, T=(float(gap[0]) + math.cos(th) * RIN, 12.9, float(gap[2]) + math.sin(th) * RIN), S=(1.5, 0.7, 1.2)))
    A0 = target; a0 = sd0
    for (p, s) in (((-6.5, 9.6, -6.0), (3.2, 1.4, 2.4)), ((4.5, 10.2, -7.5), (3.6, 1.6, 2.6)),
                   ((9.0, 8.6, -2.0), (2.6, 1.5, 2.2)), ((-1.0, 11.0, -10.0), (4.0, 1.5, 2.8)),
                   ((6.0, 7.2, 6.0), (2.4, 1.0, 1.8)), ((-9.5, 10.0, 1.0), (2.4, 1.4, 2.0)),
                   ((-4.8, 7.6, 7.5), (2.2, 1.0, 1.8))):
        p = V(*p); wv = (p - A0) - ((p - A0) @ a0) * a0; dist = float(np.linalg.norm(wv)); need = 2.3 + max(s)
        if dist < need:                                           # keep the shaft clear
            p = p + wv / max(dist, 1e-6) * (need - dist)
        sc.add(Sphere(leaves, R=rot(yaw=rng.uniform(0, 180), roll=rng.uniform(-8, 8)), T=tuple(p), S=s))

    # ---- sky: only seen low between the trunks, the same colour as the far mist ----
    def env(d):
        y = d[:, 1]
        k = 0.85 + 0.3 * np.exp(-np.abs(y) * 6.0)
        sun = np.clip(d @ sd, 0, 1) ** 12 * amt * 1.5
        return (fogL[None] * k[:, None] + sun[:, None] * V(1.0, 0.8, 0.55)[None] + beam(C[None] + d * 60.0)).astype(f32)
    sc.env = env

    focus = float(np.linalg.norm(V(0, 3.8, 1.1) - C))
    sc.camera(pos=pos, look=look, vfov=40, focus=focus, aperture=0.06, W=1280, H=720)
    sc.exposure = 1.9; sc.vignette = 0.3; sc.bounces = 4
    sc.saturation = 0.92; sc.contrast = 1.05
    return sc


if __name__ == "__main__":
    sc = shot(float(sys.argv[1]) if len(sys.argv) > 1 else 0.85)
    print("objects", len(sc.objs))
