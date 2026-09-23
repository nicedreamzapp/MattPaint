"""Ray/scene intersection on the M5 GPU (a custom Metal kernel through MLX), for pt.py.

Intersection was ~85% of render time on the CPU (profiled 2026-09-23 on 09_citrus). This does the
whole object loop per ray in one kernel launch. Shading stays in numpy.
Import this only inside worker processes: Metal must not be initialised before fork().
"""
import numpy as np

HEADER = r"""
constant float EPS = 1e-4f;
template <typename P> inline float3 ld3(P a, uint i) { return float3(a[3*i], a[3*i+1], a[3*i+2]); }
"""

SOURCE = r"""
uint i = thread_position_in_grid.x;
uint n = (uint)params[0];
if (i >= n) return;
uint nobj = (uint)params[1];
float3 O = ld3(o, i), D = ld3(d, i);
float best = tmax[i];
int bidx = -1, baux = 0;
for (uint k = 0; k < nobj; k++) {
    auto ob = objs + k * 32;
    int typ = (int)ob[0];
    float3 T = float3(ob[10], ob[11], ob[12]);
    float3 S = float3(ob[13], ob[14], ob[15]);
    float3 q = O - T;
    // (o - T) @ R : column j = sum_i q_i R[i][j]
    float3 ol = float3(q.x*ob[1] + q.y*ob[4] + q.z*ob[7], q.x*ob[2] + q.y*ob[5] + q.z*ob[8], q.x*ob[3] + q.y*ob[6] + q.z*ob[9]) / S;
    float3 dl = float3(D.x*ob[1] + D.y*ob[4] + D.z*ob[7], D.x*ob[2] + D.y*ob[5] + D.z*ob[8], D.x*ob[3] + D.y*ob[6] + D.z*ob[9]) / S;
    if (typ == 0) {                                   // unit sphere
        float a = dot(dl, dl), b = dot(ol, dl), c = dot(ol, ol) - 1.0f;
        float disc = b*b - a*c;
        if (disc < 0.0f) continue;
        float sq = sqrt(disc);
        float t0 = (-b - sq) / a, t1 = (-b + sq) / a;
        float t = t0 > EPS ? t0 : (t1 > EPS ? t1 : INFINITY);
        if (t < best) { best = t; bidx = k; baux = 0; }
    } else if (typ == 1) {                            // box -h..h
        float3 h = float3(ob[16], ob[17], ob[18]);
        float3 inv = 1.0f / select(dl, float3(1e-12f), fabs(dl) < 1e-12f);
        float3 t1 = (-h - ol) * inv, t2 = (h - ol) * inv;
        float3 mn = min(t1, t2), mx = max(t1, t2);
        float tn = max(max(mn.x, mn.y), mn.z), tf = min(min(mx.x, mx.y), mx.z);
        if (tf < tn) continue;
        float t = tn > EPS ? tn : (tf > EPS ? tf : INFINITY);
        if (t < best) { best = t; bidx = k; baux = 0; }
    } else if (typ == 2) {                            // plane y=0, optional extent
        float dy = fabs(dl.y) < 1e-12f ? 1e-12f : dl.y;
        float t = -ol.y / dy;
        if (!(t > EPS) || t >= best) continue;
        if (ob[19] > 0.5f) {
            float x = ol.x + dl.x * t, z = ol.z + dl.z * t;
            if (fabs(x) > ob[16] || fabs(z) > ob[17]) continue;
        }
        best = t; bidx = k; baux = 0;
    } else {                                          // lathe
        float rmax = ob[16], ylo = ob[17], yhi = ob[18];
        float3 lo = float3(-rmax, ylo, -rmax) - 1e-3f, hi = float3(rmax, yhi, rmax) + 1e-3f;
        float3 inv = 1.0f / select(dl, float3(1e-12f), fabs(dl) < 1e-12f);
        float3 t1 = (lo - ol) * inv, t2 = (hi - ol) * inv;
        float3 mn = min(t1, t2), mx = max(t1, t2);
        float tn = max(max(mn.x, mn.y), mn.z), tf = min(min(mx.x, mx.y), mx.z);
        if (tf < max(tn, 0.0f) || tn >= best) continue;
        uint s0 = (uint)ob[20], ns = (uint)ob[21];
        for (uint s = 0; s < ns; s++) {
            auto sg = segs + (s0 + s) * 4;
            float r0 = sg[0], y0 = sg[1], r1 = sg[2], y1 = sg[3];
            float ymin = min(y0, y1), ymax = max(y0, y1);
            if (fabs(y1 - y0) < 1e-6f) {
                float dy = fabs(dl.y) < 1e-12f ? 1e-12f : dl.y;
                float t = (y0 - ol.y) / dy;
                if (!(t > EPS) || t >= best) continue;
                float x = ol.x + dl.x * t, z = ol.z + dl.z * t, rr = sqrt(x*x + z*z);
                if (rr >= min(r0, r1) && rr <= max(r0, r1)) { best = t; bidx = k; baux = (int)s; }
                continue;
            }
            float kk = (r1 - r0) / (y1 - y0);
            float A = r0 + kk * (ol.y - y0), B = kk * dl.y;
            float a = dl.x*dl.x + dl.z*dl.z - B*B;
            float b = ol.x*dl.x + ol.z*dl.z - A*B;
            float c = ol.x*ol.x + ol.z*ol.z - A*A;
            float disc = b*b - a*c;
            if (disc < 0.0f || fabs(a) < 1e-12f) continue;
            float sq = sqrt(disc);
            float ta = (-b - sq) / a, tb = (-b + sq) / a;
            float tt[2] = {min(ta, tb), max(ta, tb)};
            for (int m = 0; m < 2; m++) {
                float t = tt[m];
                float y = ol.y + dl.y * t;
                if (t > EPS && t < best && y >= ymin && y <= ymax && A + B * t >= 0.0f) { best = t; bidx = k; baux = (int)s; }
            }
        }
    }
}
tout[i] = best; iout[i] = bidx; aout[i] = baux;
"""

_kernel = None
_packed = {}

def pack(objs):
    """scene objects -> (objs float32 [M,32], segs float32 [K,4])"""
    from pt import Sphere, Box, Plane, Lathe
    rows, segs = [], []
    for ob in objs:
        r = np.zeros(32, np.float32)
        r[1:10] = np.asarray(ob.R, np.float32).reshape(-1); r[10:13] = ob.T; r[13:16] = ob.S
        if isinstance(ob, Sphere): r[0] = 0
        elif isinstance(ob, Box): r[0] = 1; r[16:19] = ob.h
        elif isinstance(ob, Plane):
            r[0] = 2
            if ob.ext is not None: r[16], r[17], r[19] = ob.ext[0], ob.ext[1], 1
        elif isinstance(ob, Lathe):
            r[0] = 3; r[16], r[17], r[18] = ob.rmax, ob.ylo, ob.yhi
            r[20] = len(segs); r[21] = len(ob.p) - 1
            for a, b in zip(ob.p[:-1], ob.p[1:]): segs.append([a[0], a[1], b[0], b[1]])
        else: raise TypeError(type(ob))
        rows.append(r)
    if not segs: segs = [[0, 0, 0, 0]]
    return np.stack(rows), np.asarray(segs, np.float32)

def intersect(objs, o, d, tmax=None):
    global _kernel
    import mlx.core as mx
    if _kernel is None:
        _kernel = mx.fast.metal_kernel(name="pt_isect", input_names=["o", "d", "tmax", "objs", "segs", "params"],
                                       output_names=["tout", "iout", "aout"], source=SOURCE, header=HEADER)
    key = id(objs)
    if key not in _packed:
        ob, sg = pack(objs); _packed[key] = (mx.array(ob), mx.array(sg), len(ob))
    ob, sg, m = _packed[key]
    n = len(o)
    if n == 0:
        return np.zeros(0, np.float32), np.zeros(0, np.int32), np.zeros(0, np.int32)
    tm = np.full(n, np.inf, np.float32) if tmax is None else np.asarray(tmax, np.float32)
    outs = _kernel(inputs=[mx.array(np.ascontiguousarray(o, np.float32)), mx.array(np.ascontiguousarray(d, np.float32)),
                           mx.array(tm), ob, sg, mx.array(np.array([n, m], np.float32))],
                   grid=(n, 1, 1), threadgroup=(256, 1, 1),
                   output_shapes=[(n,), (n,), (n,)], output_dtypes=[mx.float32, mx.int32, mx.int32])
    mx.eval(outs)
    return np.array(outs[0]), np.array(outs[1]), np.array(outs[2])
