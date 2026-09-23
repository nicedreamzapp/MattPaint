"""pt: a small photoreal path tracer in numpy, grown out of billiards.py (2026-09-23).

Scenes are built from transformed primitives (sphere/ellipsoid, box, plane, cylinder, lathe,
rect), each with a material (diffuse, plastic = diffuse + clearcoat, metal, glass, emit) whose
albedo can be a procedural texture. Lights: rect/sphere area lights and a sun, all with
next-event estimation. Thin-lens camera, ACES develop, bloom, vignette, grain.
Rendered across CPU cores, then PAINTED INTO MATTPAINT ON SCREEN (preview, then final) and the
canvas is saved to gallery/opus-photoreal/.
"""
import asyncio, json, math, os, sys, time
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
import numpy as np
from multiprocessing import get_context

np.seterr(all="ignore")          # Accelerate matmul raises spurious fp warnings
f32 = np.float32
HERE = os.path.dirname(os.path.abspath(__file__))
GALLERY = os.path.join(os.path.dirname(HERE), "gallery", "opus-photoreal")

def norm(v): return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-12)
def V(*a): return np.array(a, f32)

def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """degrees; returns R with columns = local axes in world (world = local @ R.T + T)"""
    y, p, r = (math.radians(a) for a in (yaw, pitch, roll))
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    Rz = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return (Ry @ Rx @ Rz).astype(f32)

# ---------------- noise / textures ----------------
def _h(a, b, c=0.0):
    return np.modf(np.abs(np.sin(a * 127.1 + b * 311.7 + c * 74.7) * 43758.5453))[0]
def vnoise(x, y, z=None):
    if z is None: z = np.zeros_like(x)
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = (q * q * (3 - 2 * q) for q in (xf, yf, zf))
    def L(a, b, t): return a + (b - a) * t
    c00 = L(_h(xi, yi, zi), _h(xi + 1, yi, zi), u); c10 = L(_h(xi, yi + 1, zi), _h(xi + 1, yi + 1, zi), u)
    c01 = L(_h(xi, yi, zi + 1), _h(xi + 1, yi, zi + 1), u); c11 = L(_h(xi, yi + 1, zi + 1), _h(xi + 1, yi + 1, zi + 1), u)
    return L(L(c00, c10, v), L(c01, c11, v), w)
def fbm(x, y, z=None, oct=5):
    s, a, f = 0.0, 0.5, 1.0
    for _ in range(oct):
        s = s + a * vnoise(x * f, y * f, None if z is None else z * f); a *= 0.5; f *= 2.03
    return s

# ---------------- primitives (local space) ----------------
class Obj:
    """shape in local space; world = S*local rotated by R, moved by T"""
    def __init__(self, mat, R=None, T=(0, 0, 0), S=(1, 1, 1), name=""):
        self.mat = mat; self.R = np.eye(3, dtype=f32) if R is None else np.asarray(R, f32)
        self.T = V(*T); self.S = V(*S) if np.ndim(S) else V(S, S, S); self.name = name
    def to_local(self, o, d):
        return ((o - self.T) @ self.R) / self.S, (d @ self.R) / self.S
    def n_world(self, nl):
        return norm((nl / self.S) @ self.R.T)
    def bbox(self): return None          # local-space AABB (lo, hi) for culling
    def intersect(self, o, d, tmax):
        ol, dl = self.to_local(o, d)
        bb = self.bbox()
        if bb is not None:
            inv = 1.0 / np.where(np.abs(dl) < 1e-12, 1e-12, dl)
            t1 = (bb[0] - ol) * inv; t2 = (bb[1] - ol) * inv
            tn = np.minimum(t1, t2).max(1); tf = np.maximum(t1, t2).min(1)
            sub = np.nonzero((tf >= np.maximum(tn, 0)) & (tn < tmax))[0]
            t = np.full(len(o), np.inf, f32); aux = np.zeros(len(o), np.int32)
            if len(sub):
                ts, ax = self._hit(ol[sub], dl[sub]); t[sub] = ts; aux[sub] = ax
            return t, aux
        return self._hit(ol, dl)
    def normal(self, pl, aux): raise NotImplementedError

def _qroots(a, b, c):
    """roots of a t^2 + 2b t + c = 0, (near, far), inf when none"""
    disc = b * b - a * c
    ok = (disc >= 0) & (np.abs(a) > 1e-12)
    sq = np.sqrt(np.where(ok, disc, 0)); aa = np.where(ok, a, 1)
    t0 = np.where(ok, (-b - sq) / aa, np.inf); t1 = np.where(ok, (-b + sq) / aa, np.inf)
    return np.minimum(t0, t1), np.maximum(t0, t1)

EPS = 1e-4
class Sphere(Obj):                      # unit sphere; S makes ellipsoids
    def bbox(self): return (V(-1, -1, -1), V(1, 1, 1))
    def _hit(self, o, d):
        a = (d * d).sum(1); b = (o * d).sum(1); c = (o * o).sum(1) - 1
        t0, t1 = _qroots(a, b, c)
        t = np.where(t0 > EPS, t0, np.where(t1 > EPS, t1, np.inf))
        return t, np.zeros(len(o), np.int32)
    def normal(self, pl, aux): return pl

class Box(Obj):                         # box from -h..h
    def __init__(self, mat, half, **k): super().__init__(mat, **k); self.h = V(*half)
    def bbox(self): return None
    def _hit(self, o, d):
        inv = 1.0 / np.where(np.abs(d) < 1e-12, 1e-12, d)
        t1 = (-self.h - o) * inv; t2 = (self.h - o) * inv
        tn = np.minimum(t1, t2).max(1); tf = np.maximum(t1, t2).min(1)
        t = np.where(tf >= tn, np.where(tn > EPS, tn, np.where(tf > EPS, tf, np.inf)), np.inf)
        return t, np.zeros(len(o), np.int32)
    def normal(self, pl, aux):
        rel = pl / self.h; ax = np.abs(rel).argmax(1)
        n = np.zeros_like(pl); n[np.arange(len(pl)), ax] = np.sign(rel[np.arange(len(pl)), ax]); return n

class Plane(Obj):                       # y=0, normal +y, optional x/z extent
    def __init__(self, mat, ext=None, **k): super().__init__(mat, **k); self.ext = ext
    def _hit(self, o, d):
        t = -o[:, 1] / np.where(np.abs(d[:, 1]) < 1e-12, 1e-12, d[:, 1])
        ok = t > EPS
        if self.ext is not None:
            x = o[:, 0] + d[:, 0] * t; z = o[:, 2] + d[:, 2] * t
            ok &= (np.abs(x) <= self.ext[0]) & (np.abs(z) <= self.ext[1])
        return np.where(ok, t, np.inf), np.zeros(len(o), np.int32)
    def normal(self, pl, aux):
        n = np.zeros_like(pl); n[:, 1] = 1; return n

class Rect(Plane):                      # finite plane, used for area lights (normal +y local)
    def __init__(self, mat, hx, hz, **k): super().__init__(mat, ext=(hx, hz), **k); self.hx, self.hz = hx, hz

class Lathe(Obj):
    """surface of revolution about local y. profile: [(r, y), ...] traversed so the solid is on the
    right: out along the bottom, up the outside, back down the inside for hollow things."""
    def __init__(self, mat, profile, **k):
        super().__init__(mat, **k)
        self.p = np.array(profile, f32)
        self.rmax = float(self.p[:, 0].max()); self.ylo = float(self.p[:, 1].min()); self.yhi = float(self.p[:, 1].max())
        # smooth shading: vertex normals averaged across gentle bends, kept sharp at creases
        # (07_eggs showed rings on the eggs from flat-shaded segments)
        d = self.p[1:] - self.p[:-1]
        sn = np.stack([d[:, 1], -d[:, 0]], 1); sn /= np.linalg.norm(sn, axis=1, keepdims=True).clip(1e-9)
        m = len(sn); va = sn.copy(); vb = sn.copy()          # normal at start / end of each segment
        for i in range(m - 1):
            if float(sn[i] @ sn[i + 1]) > 0.6:
                avg = sn[i] + sn[i + 1]; avg /= max(np.linalg.norm(avg), 1e-9)
                vb[i] = avg; va[i + 1] = avg
        self.va, self.vb = va.astype(f32), vb.astype(f32)
    def bbox(self): return (V(-self.rmax, self.ylo, -self.rmax) - 1e-3, V(self.rmax, self.yhi, self.rmax) + 1e-3)
    def _hit(self, o, d):
        n = len(o); best = np.full(n, np.inf, f32); seg = np.zeros(n, np.int32)
        for i in range(len(self.p) - 1):
            (r0, y0), (r1, y1) = self.p[i], self.p[i + 1]
            if abs(y1 - y0) < 1e-6:            # flat annulus
                t = (y0 - o[:, 1]) / np.where(np.abs(d[:, 1]) < 1e-12, 1e-12, d[:, 1])
                x = o[:, 0] + d[:, 0] * t; z = o[:, 2] + d[:, 2] * t; rr = np.sqrt(x * x + z * z)
                ok = (t > EPS) & (t < best) & (rr >= min(r0, r1)) & (rr <= max(r0, r1))
                best[ok] = t[ok]; seg[ok] = i; continue
            k = (r1 - r0) / (y1 - y0)
            A = r0 + k * (o[:, 1] - y0); B = k * d[:, 1]
            a = d[:, 0] ** 2 + d[:, 2] ** 2 - B * B
            b = o[:, 0] * d[:, 0] + o[:, 2] * d[:, 2] - A * B
            c = o[:, 0] ** 2 + o[:, 2] ** 2 - A * A
            for t in _qroots(a, b, c):
                y = o[:, 1] + d[:, 1] * t
                ok = (t > EPS) & (t < best) & (y >= min(y0, y1)) & (y <= max(y0, y1)) & (A + B * t >= 0)
                best[ok] = t[ok]; seg[ok] = i
        return best, seg
    def normal(self, pl, aux):
        p0 = self.p[aux]; p1 = self.p[aux + 1]
        rr = np.sqrt(pl[:, 0] ** 2 + pl[:, 2] ** 2).clip(1e-9)
        seg = p1 - p0; L2 = (seg * seg).sum(1).clip(1e-12)
        u = np.clip(((rr - p0[:, 0]) * seg[:, 0] + (pl[:, 1] - p0[:, 1]) * seg[:, 1]) / L2, 0, 1)
        nv = self.va[aux] * (1 - u)[:, None] + self.vb[aux] * u[:, None]
        nv /= np.linalg.norm(nv, axis=1, keepdims=True).clip(1e-9)
        nr, ny = nv[:, 0], nv[:, 1]
        return np.stack([pl[:, 0] / rr * nr, ny, pl[:, 2] / rr * nr], 1)

def Cylinder(mat, r, h, **k):             # solid cylinder, local y 0..h
    return Lathe(mat, [(0, 0), (r, 0), (r, h), (0, h)], **k)

# ---------------- materials ----------------
class Mat:
    def __init__(self, kind="diffuse", alb=(0.5, 0.5, 0.5), f0=0.04, rough=0.02, ior=1.5,
                 absorb=(0, 0, 0), emit=(0, 0, 0), tex=None, bump=None, nee=True, spec_tint=None, glow=None):
        self.kind = kind; self.alb = V(*alb); self.f0 = f0; self.rough = rough; self.ior = ior
        self.absorb = V(*absorb); self.emit = V(*emit); self.tex = tex; self.bump = bump; self.nee = nee
        self.spec_tint = spec_tint; self.glow = glow      # glow(pl, pw, n) -> added light (fake subsurface)
    def albedo(self, pl, pw, n):
        return self.tex(pl, pw, n) if self.tex else np.broadcast_to(self.alb, pl.shape).astype(f32)

# ---------------- scene ----------------
class Scene:
    def __init__(self):
        self.objs = []; self.lights = []; self.sun = None
        self.env = lambda d: np.zeros((len(d), 3), f32)
        self.cam = None
        self.exposure = 1.0; self.bloom = 1.0; self.vignette = 0.30; self.grain = 0.006
        self.bounces = 5; self.saturation = 1.0; self.contrast = 1.0
    def add(self, o): self.objs.append(o); return o
    def rect_light(self, center, hx, hz, Le, R=None, visible=True):
        m = Mat("emit", emit=Le); o = Rect(m, hx, hz, R=R, T=center)
        o.visible = visible; self.objs.append(o)
        self.lights.append(("rect", o, V(*Le))); return o
    def sphere_light(self, center, r, Le, S=None):
        m = Mat("emit", emit=Le); o = Sphere(m, T=center, S=(r, r, r) if S is None else S)
        self.objs.append(o); self.lights.append(("sphere", o, V(*Le), r)); return o
    def set_sun(self, direction, Le, angle_deg=0.53):
        self.sun = (norm(V(*direction)[None])[0], V(*Le), math.cos(math.radians(angle_deg / 2)))
    def camera(self, pos, look, vfov, focus=None, aperture=0.0, W=1400, H=900, up=(0, 1, 0)):
        pos, look = V(*pos), V(*look)
        fwd = norm((look - pos)[None])[0]; right = norm(np.cross(fwd, V(*up))[None])[0]; upv = np.cross(right, fwd)
        self.cam = dict(pos=pos, fwd=fwd, right=right, up=upv, th=math.tan(math.radians(vfov) / 2),
                        focus=float(np.linalg.norm(look - pos)) if focus is None else float(focus),
                        ap=aperture, W=W, H=H)

TITLES = {"01_billiards": "Pool table after the break", "02_chess": "Chess endgame at a window",
          "03_espresso": "Morning espresso", "04_candles": "Candles at night", "05_whiskey": "Whiskey on the rocks",
          "06_duck": "Rubber duck in the bath", "07_eggs": "Farm eggs in a stoneware bowl",
          "08_watch": "Gold pocket watch and coins", "09_citrus": "Oranges and lemons", "10_marbles": "Marbles in late sun",
          "11_pancakes": "Sunday pancakes"}
SC = None   # the scene being rendered (set before the worker pool forks)

USE_GPU = os.environ.get("PT_GPU", "1") != "0"
def intersect(o, d, skip_invisible=False):
    if USE_GPU:
        import gpu_isect
        return gpu_isect.intersect(SC.objs, o, d)
    return intersect_cpu(o, d)

def intersect_cpu(o, d, skip_invisible=False):
    n = len(o); t = np.full(n, np.inf, f32); idx = np.full(n, -1, np.int32); aux = np.zeros(n, np.int32)
    for k, ob in enumerate(SC.objs):
        if skip_invisible and not getattr(ob, "visible", True): continue
        tt, ax = ob.intersect(o, d, t)
        ok = tt < t
        t[ok] = tt[ok]; idx[ok] = k; aux[ok] = ax[ok]
    return t, idx, aux

def transmittance(o, d, tmax):
    """shadow ray: 0 if blocked by anything opaque; glass passes light, tinted (no caustics)"""
    tr = np.ones((len(o), 3), f32); live = np.arange(len(o)); oo = o.copy(); rem = tmax.copy()
    for _ in range(6):
        if len(live) == 0: break
        t, idx, _ = intersect(oo[live], d[live])
        hit = (t < rem[live] * 0.999) & (idx >= 0)
        if not hit.any(): break
        hl = live[hit]; hidx = idx[hit]
        glass = np.array([SC.objs[i].mat.kind == "glass" for i in hidx], bool)
        emit = np.array([SC.objs[i].mat.kind == "emit" for i in hidx], bool)
        opaque = ~glass & ~emit
        tr[hl[opaque]] = 0
        gl = hl[glass | emit]
        if len(gl):
            tint = np.stack([np.exp(-SC.objs[i].mat.absorb * 0.3) * 0.92 if SC.objs[i].mat.kind == "glass"
                             else np.ones(3, f32) for i in hidx[glass | emit]])
            tr[gl] *= tint
            adv = t[hit][glass | emit]
            oo[gl] = oo[gl] + d[gl] * (adv + 2e-3)[:, None]; rem[gl] -= adv + 2e-3
        live = gl
    return tr

def onb(n):
    s = np.where(n[:, 2] >= 0, 1.0, -1.0).astype(f32)
    a = -1.0 / (s + n[:, 2]); b = n[:, 0] * n[:, 1] * a
    t = np.stack([1 + s * n[:, 0] ** 2 * a, s * b, -s * n[:, 0]], 1)
    bb = np.stack([b, s + n[:, 1] ** 2 * a, -n[:, 1]], 1)
    return t, bb

def cosine_dir(n, rng):
    u1, u2 = rng.random(len(n), dtype=f32), rng.random(len(n), dtype=f32)
    r = np.sqrt(u1); ph = 2 * np.pi * u2; t, b = onb(n)
    return norm(t * (r * np.cos(ph))[:, None] + b * (r * np.sin(ph))[:, None] + n * np.sqrt(1 - u1)[:, None])

def glossy(dirn, rough, rng):
    return norm(dirn + rng.normal(0, 1, dirn.shape).astype(f32) * rough[:, None])

def sample_lights(p, n, alb_diff, rng):
    """direct light on the diffuse lobe from every light (NEE)"""
    out = np.zeros_like(p); so = p + n * 2e-3
    for L in SC.lights:
        if L[0] == "rect":
            ob, Le = L[1], L[2]
            u = rng.uniform(-ob.hx, ob.hx, len(p)).astype(f32); v = rng.uniform(-ob.hz, ob.hz, len(p)).astype(f32)
            lp = (np.stack([u, np.zeros_like(u), v], 1) * ob.S) @ ob.R.T + ob.T
            ln = ob.n_world(np.tile(V(0, 1, 0), (1, 1)))[0]
            area = 4 * ob.hx * ob.hz * ob.S[0] * ob.S[2]
            ld = lp - p; dist = np.linalg.norm(ld, axis=1); ld /= dist[:, None]
            cl = np.abs(ld @ ln)
        else:
            ob, Le, r = L[1], L[2], L[3]
            w = norm(rng.normal(size=p.shape).astype(f32))
            lp = ob.T + w * ob.S
            area = 4 * np.pi * r * r
            ld = lp - p; dist = np.linalg.norm(ld, axis=1); ld /= dist[:, None]
            cl = np.clip(-(w * ld).sum(1), 0, 1)
        cs = np.clip((n * ld).sum(1), 0, 1)
        g = cs * cl * area / (dist * dist).clip(1e-6)
        m = g > 0
        if not m.any(): continue
        tr = np.zeros_like(p); tr[m] = transmittance(so[m], ld[m], dist[m] - 2e-3)
        out += alb_diff / np.pi * Le[None] * g[:, None] * tr
    if SC.sun is not None:
        sd, Le, cmax = SC.sun
        # jitter inside the sun disc for soft shadow edges
        jit = norm(sd[None] + rng.normal(0, 1, p.shape).astype(f32) * math.sqrt(max(1 - cmax, 1e-7)) * 0.7)
        cs = np.clip((n * jit).sum(1), 0, 1); m = cs > 0
        if m.any():
            tr = np.zeros_like(p); tr[m] = transmittance(so[m], jit[m], np.full(m.sum(), 1e5, f32))
            out += alb_diff / np.pi * Le[None] * cs[:, None] * tr     # Le = irradiance (was radiance: the sun was ~0, 03_espresso)
    return out

def env_with_sun(d, specular):
    c = SC.env(d)
    if SC.sun is not None:
        sd, Le, cmax = SC.sun
        disc = ((d @ sd) > cmax) & specular
        c = c + (Le / (2 * np.pi * (1 - cmax)))[None] * disc[:, None]
    return c

def trace_rows(args):
    y0, y1, spp, seed = args
    cam = SC.cam; W, H = cam["W"], cam["H"]
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[y0:y1, 0:W]; ys = ys.ravel().astype(f32); xs = xs.ravel().astype(f32)
    acc = np.zeros((len(xs), 3), f32)
    for s in range(spp):
        jx = xs + rng.random(len(xs), dtype=f32); jy = ys + rng.random(len(xs), dtype=f32)
        px = (jx / W * 2 - 1) * cam["th"] * (W / H); py = (1 - jy / H * 2) * cam["th"]
        d = norm(cam["fwd"][None] + cam["right"][None] * px[:, None] + cam["up"][None] * py[:, None])
        o = np.broadcast_to(cam["pos"], d.shape).copy()
        if cam["ap"] > 0:
            fp = o + d * (cam["focus"] / (d @ cam["fwd"]))[:, None]
            r = cam["ap"] * np.sqrt(rng.random(len(xs), dtype=f32)); ph = rng.random(len(xs), dtype=f32) * 2 * np.pi
            o = o + cam["right"][None] * (r * np.cos(ph))[:, None] + cam["up"][None] * (r * np.sin(ph))[:, None]
            d = norm(fp - o)
        thr = np.ones((len(xs), 3), f32); rad = np.zeros((len(xs), 3), f32)
        alive = np.arange(len(xs)); spec = np.ones(len(xs), bool)
        for bounce in range(SC.bounces):
            if len(alive) == 0: break
            oo, dd = o[alive], d[alive]
            t, idx, aux = intersect(oo, dd)
            miss = idx < 0
            CL = 50.0 if bounce == 0 else 3.0                # clamp indirect spikes (fireflies), 02_chess lesson
            rad[alive[miss]] += np.minimum(thr[alive[miss]] * env_with_sun(dd[miss], spec[alive[miss]]), CL)
            keep = ~miss
            alive, t, idx, aux, oo, dd = alive[keep], t[keep], idx[keep], aux[keep], oo[keep], dd[keep]
            if len(alive) == 0: break
            p = oo + dd * t[:, None]
            n = np.zeros_like(p); kinds = np.empty(len(p), object)
            alb = np.zeros_like(p); f0 = np.zeros(len(p), f32); rough = np.zeros(len(p), f32)
            ior = np.ones(len(p), f32); absorb = np.zeros_like(p); emit = np.zeros_like(p); nee = np.ones(len(p), bool)
            kind_id = np.zeros(len(p), np.int8)          # 0 diffuse,1 plastic,2 metal,3 glass,4 emit
            KID = {"diffuse": 0, "plastic": 1, "metal": 2, "glass": 3, "emit": 4}
            for k in np.unique(idx):
                m = idx == k; ob = SC.objs[k]; mt = ob.mat
                pl = ((p[m] - ob.T) @ ob.R) / ob.S
                nl = ob.normal(pl, aux[m])
                nw = ob.n_world(nl)
                if mt.bump is not None: nw = norm(nw + mt.bump(pl, p[m], nw))
                n[m] = nw
                alb[m] = mt.albedo(pl, p[m], nw); f0[m] = mt.f0; rough[m] = mt.rough
                ior[m] = mt.ior; absorb[m] = mt.absorb; emit[m] = mt.emit; nee[m] = mt.nee
                kind_id[m] = KID[mt.kind]
                if mt.glow is not None: rad[alive[m]] += thr[alive[m]] * mt.glow(pl, p[m], nw)
            # emitters
            em = kind_id == 4
            if em.any():
                cnt = spec[alive[em]] | ~nee[em]
                rad[alive[em]] += np.minimum(thr[alive[em]] * emit[em] * cnt[:, None], CL)
            keep = ~em
            alive, p, n, dd, alb, f0, rough, ior, absorb, kind_id, t = (a[keep] for a in (alive, p, n, dd, alb, f0, rough, ior, absorb, kind_id, t))
            if len(alive) == 0: break
            outward = n.copy()
            inside = (n * dd).sum(1) > 0
            n = np.where(inside[:, None], -n, n)                 # n faces the incoming ray
            cosi = np.clip(-(n * dd).sum(1), 0, 1)
            nd = np.zeros_like(dd); newspec = np.zeros(len(p), bool); mult = np.ones_like(p); off = n * 2e-3
            # --- glass ---
            g = kind_id == 3
            if g.any():
                # Beer absorption for the stretch we just travelled inside
                thr[alive[g & inside]] *= np.exp(-absorb[g & inside] * t[g & inside][:, None])
                eta = np.where(inside[g], ior[g], 1.0 / ior[g])
                ci = cosi[g]; s2 = eta * eta * (1 - ci * ci)
                tir = s2 > 1
                ct = np.sqrt(np.clip(1 - s2, 0, 1))
                rs = ((eta * ci - ct) / (eta * ci + ct)) ** 2; rp = ((ci - eta * ct) / (ci + eta * ct)) ** 2
                F = np.where(tir, 1.0, 0.5 * (rs + rp))
                refl = rng.random(g.sum(), dtype=f32) < F
                dg = dd[g]; ng = n[g]
                rdir = dg + 2 * ci[:, None] * ng
                tdir = eta[:, None] * dg + (eta * ci - ct)[:, None] * ng
                out = norm(np.where(refl[:, None], rdir, tdir))
                out = glossy(out, rough[g] * 0.3, rng)
                nd[g] = out; newspec[g] = True
                off[g] = np.where(refl[:, None], ng, -ng) * 2e-3
            # --- metal ---
            mm = kind_id == 2
            if mm.any():
                ci = cosi[mm]
                Fm = alb[mm] + (1 - alb[mm]) * ((1 - ci) ** 5)[:, None]
                nd[mm] = glossy(dd[mm] + 2 * ci[:, None] * n[mm], rough[mm], rng)
                mult[mm] = Fm; newspec[mm] = True
            # --- diffuse / plastic ---
            dp = (kind_id == 0) | (kind_id == 1)
            if dp.any():
                ci = cosi[dp]
                F = np.where(kind_id[dp] == 1, f0[dp] + (1 - f0[dp]) * (1 - ci) ** 5, 0.0)
                rad[alive[dp]] += np.minimum(thr[alive[dp]] * sample_lights(p[dp], n[dp], alb[dp] * (1 - F)[:, None], rng), CL)
                pick = rng.random(dp.sum(), dtype=f32) < F
                rdir = glossy(dd[dp] + 2 * ci[:, None] * n[dp], rough[dp], rng)
                ddir = cosine_dir(n[dp], rng)
                nd[dp] = np.where(pick[:, None], rdir, ddir)
                mult[dp] = np.where(pick[:, None], 1.0, alb[dp]); newspec[dp] = pick
            thr[alive] *= mult
            # russian roulette after a few bounces
            if bounce >= 3:
                q = np.clip(thr[alive].max(1), 0.05, 1)
                live = rng.random(len(alive), dtype=f32) < q
                thr[alive[live]] /= q[live][:, None]
                thr[alive[~live]] = 0
            o[alive] = p + off; d[alive] = nd; spec[alive] = newspec
            alive = alive[thr[alive].max(1) > 0]
        acc += np.nan_to_num(rad).clip(0, 50)            # clamp fireflies
    return y0, (acc / spp).reshape(y1 - y0, W, 3)

def render(spp, seed, workers=14):
    W, H = SC.cam["W"], SC.cam["H"]
    rows = [(y, min(y + 20, H), spp, seed * 100003 + y) for y in range(0, H, 20)]
    img = np.zeros((H, W, 3), f32)
    for y0, blk in executor(workers).map(trace_rows, rows):
        img[y0:y0 + len(blk)] = blk
    return img

# Workers are SPAWNED, not forked: Metal (the GPU) does not survive fork() on macOS — forked
# workers either crashed in objc or lost the Metal compiler service (00:31-00:40, 2026-09-23).
# A spawned child re-runs the scene script as __mp_main__, which rebuilds the scene; the
# initializer then points SC at it. ProcessPoolExecutor also raises if a worker dies, where
# mp.Pool hung forever.
_EX = None
def _spawn_init():
    global SC
    m = sys.modules.get("__mp_main__") or sys.modules.get("__main__")
    SC = getattr(m, "sc", None)
def executor(workers=14):
    global _EX
    if _EX is None:
        from concurrent.futures import ProcessPoolExecutor
        _EX = ProcessPoolExecutor(workers, mp_context=get_context("spawn"), initializer=_spawn_init)
    return _EX

def denoise(img, strength=1.0):
    """light edge-aware smoothing (bilateral on luminance) to take the last grain out"""
    if strength <= 0: return img
    from scipy.ndimage import gaussian_filter
    lum = img.mean(2)
    out = np.zeros_like(img); wsum = np.zeros_like(lum)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            sh = np.roll(np.roll(img, dy, 0), dx, 1); sl = sh.mean(2)
            w = np.exp(-(dx * dx + dy * dy) / 4.0) * np.exp(-((sl - lum) / (0.12 * (lum + 0.02) * strength + 1e-6)) ** 2)
            out += sh * w[..., None]; wsum += w
    return out / wsum[..., None]

def develop(hdr, sc):
    from scipy.ndimage import gaussian_filter
    H, W = hdr.shape[:2]
    hdr = np.nan_to_num(hdr).clip(0, 500) * sc.exposure
    hot = np.clip(hdr - 1.5, 0, None)
    bloom = sum(gaussian_filter(hot, sigma=(s, s, 0)) * w for s, w in ((3, 0.08), (14, 0.05), (45, 0.035))) * sc.bloom
    x = hdr + bloom
    # tone map on luminance so hot colored lights keep their hue (per-channel ACES turned the
    # candle flames green-yellow in 04_candles), then roll the brightest parts toward white
    L = (x * V(0.2126, 0.7152, 0.0722)).sum(2, keepdims=True)
    Lt = (L * (2.51 * L + 0.03)) / (L * (2.43 * L + 0.59) + 0.14)
    ldr = x * (Lt / np.maximum(L, 1e-6))
    over = np.clip(ldr.max(2, keepdims=True) - 1, 0, None)
    ldr = np.clip(ldr + over * 0.6, 0, 1)
    if sc.saturation != 1.0:
        l = ldr.mean(2, keepdims=True); ldr = np.clip(l + (ldr - l) * sc.saturation, 0, 1)
    ldr = np.power(ldr, 1 / 2.2)
    if sc.contrast != 1.0: ldr = np.clip(0.5 + (ldr - 0.5) * sc.contrast, 0, 1)
    vy, vx = np.mgrid[0:H, 0:W]
    v = 1 - sc.vignette * (((vx / W - 0.5) ** 2 * 1.2 + (vy / H - 0.5) ** 2) * 2.2) ** 1.3
    ldr = ldr * v[..., None]
    ldr = ldr + np.random.default_rng(1).normal(0, sc.grain, ldr.shape[:2])[..., None]
    return np.clip(ldr * 255, 0, 255).astype(np.uint8)

def to_ops(img, q=2):
    H, W = img.shape[:2]; ops = []; qi = img // q * q
    for y in range(H):
        row = qi[y]; ch = np.nonzero(np.any(row[1:] != row[:-1], axis=1))[0] + 1
        for s, e in zip(np.r_[0, ch], np.r_[ch, W]):
            c = row[s]; ops.append([0, int(s), y, int(e - s), 1, int(c[0]), int(c[1]), int(c[2])])
    return ops

MODEL = "Claude Opus 5.5"
MODEL_ID = "claude-opus-5-5"
BANNER_JS = r"""
window.__opusBanner = function(html) {
  let b = document.getElementById('opus-banner');
  if (!b) {
    b = document.createElement('div'); b.id = 'opus-banner';
    b.style.cssText = 'position:fixed;top:8px;right:12px;z-index:99999;background:rgba(20,18,28,.86);color:#f3efe6;' +
      'font:13px/1.45 -apple-system,Helvetica,sans-serif;padding:8px 12px;border-radius:8px;pointer-events:none;' +
      'box-shadow:0 2px 10px rgba(0,0,0,.35);max-width:440px';
    document.body.appendChild(b);
  }
  b.innerHTML = html;
};
"""
def _fmt(n): return f"{n:,}"
async def banner(tab, title, phase, done, total, t0, extra=""):
    el = time.time() - t0
    html = (f"<b>Painted by {MODEL}</b> <span style='opacity:.6'>({MODEL_ID})</span><br>"
            f"{title}<br>{phase}: <b>{_fmt(done)}</b> / {_fmt(total)} strokes &nbsp;·&nbsp; {el:.0f}s{extra}")
    await tab.eval(BANNER_JS + f"window.__opusBanner({json.dumps(html)}); document.title = {json.dumps(f'{title} — {MODEL}')};", ret=False)

async def _paint(tab, img, title, phase, t0, stats):
    ops = to_ops(img)
    for i in range(0, len(ops), 6000):
        tab.fast(ops[i:i + 6000]); await tab.sync(); await asyncio.sleep(0.01)
    stats["strokes"] = stats.get("strokes", 0) + len(ops)
    return len(ops)

TOPBAR = 58
def _spaced(d_img, s, cx, cy, size, tracking, col, bg, sup=3):
    """letter-spaced caps, same as art.text() used for the gen 1-6 gallery"""
    from PIL import Image, ImageDraw, ImageFont
    f = None
    for p in ("/System/Library/Fonts/Supplemental/Copperplate.ttc", "/System/Library/Fonts/Supplemental/Futura.ttc"):
        try: f = ImageFont.truetype(p, size * sup); break
        except Exception: pass
    tmp = ImageDraw.Draw(Image.new("L", (8, 8)))
    ws = [tmp.textlength(ch, font=f) for ch in s]
    total = sum(ws) + tracking * sup * (len(s) - 1); Hh = int(size * sup * 1.6)
    im = Image.new("L", (int(total) + 40, Hh), 0); dr = ImageDraw.Draw(im); x = 20
    for ch, w in zip(s, ws):
        dr.text((x, Hh * 0.2), ch, font=f, fill=255); x += w + tracking * sup
    im = im.resize((max(1, im.width // sup), max(1, im.height // sup)), Image.LANCZOS)
    m = np.asarray(im, np.float32)[..., None] / 255.0
    x0 = int(cx - im.width / 2); y0 = int(cy - im.height / 2)
    reg = d_img[y0:y0 + im.height, x0:x0 + im.width]
    mm = m[:reg.shape[0], :reg.shape[1]]
    d_img[y0:y0 + im.height, x0:x0 + im.width] = (np.asarray(bg) * (1 - mm) + np.asarray(col) * mm).astype(np.uint8)

def with_header(img, title, strokes):
    """the picture with the gallery's title bar on top: TITLE / PAINTED BY ... · N STROKES"""
    H, W = img.shape[:2]
    bar = np.zeros((TOPBAR + 2, W, 3), np.uint8); bar[:] = (18, 20, 18)
    bar[TOPBAR:TOPBAR + 2] = (120, 118, 96)
    _spaced(bar, title.upper(), W * 0.5, TOPBAR * 0.42, 21, 7, (232, 226, 196), (18, 20, 18))
    sub = f"PAINTED BY {MODEL.upper()}   ·   {strokes:,} STROKES   ·   PATH TRACED"
    _spaced(bar, sub, W * 0.5, TOPBAR * 0.78, 11, 5, (150, 146, 120), (18, 20, 18))
    return np.concatenate([bar, img], 0)

def sign(img):
    """small signature in the corner, like an artist's"""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    txt = "Opus 5.5"; bb = d.textbbox((0, 0), txt, font=f)
    x, y = im.width - bb[2] - 14, im.height - bb[3] - 10
    region = np.asarray(img[y:y + bb[3], x:x + bb[2]]).mean()
    d.text((x, y), txt, font=f, fill=(20, 20, 20) if region > 140 else (235, 230, 220))
    return np.asarray(im)

async def _run(sc, name, spp, preview, denoise_s):
    global SC
    SC = sc
    from engine import Browser, launch_brave, paint_url
    import urllib.request
    try: urllib.request.urlopen("http://localhost:9231/json/version", timeout=1); up = True
    except Exception: up = False
    if not up: launch_brave(9231, size=(1560, 1010)); await asyncio.sleep(2.0)
    br = Browser(9231); await br.connect()
    tab = await br.existing_page("replay") or await br.new_tab("replay")
    await tab.goto(paint_url()); await tab.measure_canvas()
    await tab.resize_canvas(sc.cam["W"], sc.cam["H"])
    title = TITLES.get(name, name)
    T0 = time.time(); stats = {}
    await tab.resize_canvas(sc.cam["W"], sc.cam["H"] + TOPBAR + 2)
    await tab.eval(f"document.title = {json.dumps(title + ' — ' + MODEL)};", ret=False)
    t0 = time.time(); pv = render(preview, 1)
    print(f"[{name}] preview {preview} spp {time.time() - t0:.0f}s", flush=True)
    rough = develop(pv, sc)
    n1 = await _paint(tab, with_header(rough, title, len(to_ops(rough))), title, "rough pass", T0, stats)
    t0 = time.time(); fin = render(spp, 2)
    fin = (fin * spp + pv * preview) / (spp + preview)
    print(f"[{name}] final {spp} spp {time.time() - t0:.0f}s", flush=True)
    final = develop(denoise(fin, denoise_s), sc)
    n_pic = len(to_ops(final))
    n2 = await _paint(tab, with_header(final, title, n_pic), title, "final", T0, stats)
    total = time.time() - T0
    import json as _j
    open(os.path.join(GALLERY, name + ".stats.json"), "w").write(_j.dumps(
        {"title": title, "model": MODEL, "model_id": MODEL_ID, "strokes_total": stats["strokes"],
         "strokes_picture": n_pic, "samples_per_pixel": spp, "minutes": round(total / 60, 2)}, indent=1))
    print(f"[{name}] {MODEL}: {stats['strokes']:,} strokes, {total / 60:.1f} min", flush=True)
    os.makedirs(GALLERY, exist_ok=True)
    out = os.path.join(GALLERY, name + ".png")
    await tab.png(out)                                  # the canvas Matt is looking at
    print(f"[{name}] saved {out}", flush=True)
    await br.close()                                    # paint window stays up

def run(sc, name, spp=None, preview=8, denoise_s=1.0, budget=60):
    if spp is None:                                  # fit the render to ~budget seconds
        spp = int(np.clip(budget / max(timing(sc), 1e-3), 64, 600))
    asyncio.run(_run(sc, name, spp, preview, denoise_s))

def _timing_job(args):
    rows, spp = args
    trace_rows((rows[0], rows[1], 1, 0))                 # warm-up (kernel compile)
    t = time.time(); trace_rows((rows[0], rows[1], spp, 0)); return time.time() - t

def timing(sc, rows=(430, 450), spp=1):
    """cost check on a thin strip, no picture made; runs in a forked worker so the parent
    process never touches the GPU (Metal does not survive fork)"""
    global SC
    SC = sc
    dt = executor().submit(_timing_job, (rows, spp)).result()
    return dt / spp / (rows[1] - rows[0]) * sc.cam["H"] / 14
