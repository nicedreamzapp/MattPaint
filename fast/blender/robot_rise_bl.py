# robot_launch_bl.py
# Blender 5.1 headless:  blender -b --factory-startup -P robot_launch_bl.py -- OUTDIR [FRAME]
# Shot 2: the overgrown robot rises from its kneel, ignites its engines and launches up the sunbeam
# through the canopy gap. Same modeling, materials, forest, mist and render setup as robot_forest_bl.py,
# rendered with Cycles on the Apple GPU (Metal).

import bpy, bmesh, sys, os, math, random, time
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils import noise as mnoise

# ------------------------------------------------------------------ args
argv = sys.argv
args = argv[argv.index("--") + 1:] if "--" in argv else []
OUTDIR = os.path.abspath(os.path.expanduser(args[0])) if len(args) > 0 else os.path.abspath("robot_launch_out")
FRAME = int(args[1]) if len(args) > 1 else None
os.makedirs(OUTDIR, exist_ok=True)

random.seed(20261102)
mnoise.seed_set(7)
RND = random.Random(20261102)

scene = bpy.context.scene
PREFS = bpy.context.preferences


def log(msg):
    print(f"[robot_launch] {msg}", flush=True)


# ------------------------------------------------------------------ clean slate
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.curves):
    for d in list(coll):
        if d.users == 0:
            coll.remove(d)


def new_coll(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


C_ROBOT = new_coll("Robot")
C_PLANTS = new_coll("Plants")
C_FOREST = new_coll("Forest")
C_FX = new_coll("FX")

# ------------------------------------------------------------------ node helpers


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def N(nt, typ, **props):
    n = nt.nodes.new(typ)
    for k, v in props.items():
        try:
            setattr(n, k, v)
        except Exception:
            pass
    return n


def sock(node, key, out=False):
    coll = node.outputs if out else node.inputs
    if isinstance(key, int):
        return coll[key]
    cands = [s for s in coll if s.identifier == key] + [s for s in coll if s.name == key]
    for s in cands:
        if getattr(s, "enabled", True):
            return s
    if cands:
        return cands[0]
    raise KeyError(f"{node.bl_idname}: no socket '{key}'")


def L(nt, a, b):
    nt.links.new(a, b)


def feed(nt, s, v):
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, s)
    elif isinstance(v, (tuple, list)):
        v = tuple(float(x) for x in v)
        n = len(s.default_value)
        if len(v) < n:
            v = v + (1.0,) * (n - len(v))
        s.default_value = v[:n]
    else:
        s.default_value = v


def setin(node, key, val):
    try:
        feed(None, sock(node, key), val)
    except Exception:
        pass


def math_(nt, op, a, b=0.0, clamp=False):
    n = N(nt, 'ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    feed(nt, n.inputs[0], a)
    feed(nt, n.inputs[1], b)
    return n.outputs[0]


def maprange(nt, v, fmin, fmax, tmin=0.0, tmax=1.0):
    n = N(nt, 'ShaderNodeMapRange')
    n.clamp = True
    feed(nt, sock(n, 'Value'), v)
    setin(n, 'From Min', fmin)
    setin(n, 'From Max', fmax)
    setin(n, 'To Min', tmin)
    setin(n, 'To Max', tmax)
    return sock(n, 'Result', True)


def noise(nt, vec, scale, detail=4.0, rough=0.5, distortion=0.0, out='Fac'):
    n = N(nt, 'ShaderNodeTexNoise')
    if vec is not None:
        L(nt, vec, sock(n, 'Vector'))
    setin(n, 'Scale', scale)
    setin(n, 'Detail', detail)
    setin(n, 'Roughness', rough)
    setin(n, 'Distortion', distortion)
    return sock(n, out, True)


def ramp(nt, fac, stops):
    n = N(nt, 'ShaderNodeValToRGB')
    els = n.color_ramp.elements
    c0 = stops[0][1]
    c1 = stops[-1][1]
    els[0].position = stops[0][0]
    els[0].color = tuple(c0) + (1.0,) * (4 - len(c0))
    els[-1].position = stops[-1][0]
    els[-1].color = tuple(c1) + (1.0,) * (4 - len(c1))
    for p, c in stops[1:-1]:
        e = els.new(p)
        e.color = tuple(c) + (1.0,) * (4 - len(c))
    feed(nt, sock(n, 'Fac'), fac)
    return sock(n, 'Color', True)


def mix_node(nt, dtype):
    n = N(nt, 'ShaderNodeMix')
    n.data_type = dtype
    try:
        n.clamp_factor = True
    except Exception:
        pass
    return n


def mix_col(nt, fac, a, b, return_node=False):
    n = mix_node(nt, 'RGBA')
    feed(nt, sock(n, 'Factor_Float'), fac)
    feed(nt, sock(n, 'A_Color'), a)
    feed(nt, sock(n, 'B_Color'), b)
    if return_node:
        return n
    return sock(n, 'Result_Color', True)


def mix_f(nt, fac, a, b):
    n = mix_node(nt, 'FLOAT')
    feed(nt, sock(n, 'Factor_Float'), fac)
    feed(nt, sock(n, 'A_Float'), a)
    feed(nt, sock(n, 'B_Float'), b)
    return sock(n, 'Result_Float', True)


def bump(nt, height, strength, distance, normal=None):
    n = N(nt, 'ShaderNodeBump')
    feed(nt, sock(n, 'Strength'), strength)
    setin(n, 'Distance', distance)
    feed(nt, sock(n, 'Height'), height)
    if normal is not None:
        L(nt, normal, sock(n, 'Normal'))
    return sock(n, 'Normal', True)


def set_disp(m, method):
    for target in (m, getattr(m, "cycles", None)):
        if target is None:
            continue
        try:
            target.displacement_method = method
            return
        except Exception:
            pass


def principled_out(nt):
    out = N(nt, 'ShaderNodeOutputMaterial')
    b = N(nt, 'ShaderNodeBsdfPrincipled')
    L(nt, sock(b, 'BSDF', True), sock(out, 'Surface'))
    return b, out


def moss_block(nt, co, geo, lo, hi, extra=None):
    """Moss mask from world normal Z (plus optional extra term), moss color, moss bump height."""
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, sock(geo, 'Normal', True), sock(sep, 'Vector'))
    nz = sock(sep, 'Z', True)
    mn = noise(nt, co, 3.0, 6, 0.6)
    pert = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', mn, 0.5), 0.7)
    raw = math_(nt, 'ADD', nz, pert)
    if extra is not None:
        raw = math_(nt, 'ADD', raw, extra)
    mask = maprange(nt, raw, lo, hi, 0.0, 1.0)
    mcol = ramp(nt, noise(nt, co, 28.0, 8, 0.65),
                [(0.3, (0.018, 0.035, 0.006)), (0.55, (0.06, 0.11, 0.018)), (0.8, (0.15, 0.21, 0.035))])
    mh = noise(nt, co, 70.0, 6, 0.7)
    return mask, mcol, mh


# ------------------------------------------------------------------ materials


def make_robot_mat(name, paint, chip_lo):
    m, nt = new_mat(name)
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    geo = N(nt, 'ShaderNodeNewGeometry')

    n_rust = noise(nt, co, 1.4, 12, 0.62)
    rust = ramp(nt, n_rust, [(0.50, (0, 0, 0)), (0.66, (1, 1, 1))])
    n_chip = noise(nt, co, 9.0, 10, 0.72)
    chip = ramp(nt, n_chip, [(chip_lo, (0, 0, 0)), (chip_lo + 0.035, (1, 1, 1))])
    edge = maprange(nt, sock(geo, 'Pointiness', True), 0.53, 0.62)
    edge = math_(nt, 'MULTIPLY', edge, ramp(nt, noise(nt, co, 25.0, 4, 0.6), [(0.4, (0, 0, 0)), (0.55, (1, 1, 1))]))
    chip = math_(nt, 'MAXIMUM', chip, edge)

    ao = N(nt, 'ShaderNodeAmbientOcclusion')
    try:
        ao.samples = 8
        ao.only_local = True
    except Exception:
        pass
    setin(ao, 'Distance', 0.35)
    dirt = ramp(nt, sock(ao, 'AO', True), [(0.3, (1, 1, 1)), (0.92, (0, 0, 0))])

    vor = N(nt, 'ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    L(nt, co, sock(vor, 'Vector'))
    setin(vor, 'Scale', 0.9)
    seam = maprange(nt, sock(vor, 'Distance', True), 0.0, 0.018, 1.0, 0.0)

    rust_col = ramp(nt, noise(nt, co, 9.0, 8, 0.6),
                    [(0.3, (0.09, 0.035, 0.015)), (0.55, (0.32, 0.12, 0.04)), (0.8, (0.55, 0.25, 0.08))])
    faded = tuple(min(1.0, c * 2.2) for c in paint)
    paint_col = mix_col(nt, noise(nt, co, 2.5, 6, 0.6), paint, faded)
    metal_col = (0.42, 0.40, 0.37)

    c = mix_col(nt, chip, paint_col, metal_col)
    c = mix_col(nt, rust, c, rust_col)
    dirt_f = math_(nt, 'MULTIPLY', dirt, 0.75)
    c = mix_col(nt, dirt_f, c, (0.035, 0.03, 0.022))
    c = mix_col(nt, math_(nt, 'MULTIPLY', seam, 0.8), c, (0.015, 0.014, 0.012))

    metal = mix_f(nt, chip, 0.0, 0.9)
    metal = mix_f(nt, rust, metal, 0.0)
    rough = mix_f(nt, chip, 0.62, 0.34)
    rough = mix_f(nt, rust, rough, 0.88)
    rough = mix_f(nt, dirt_f, rough, 0.95)

    mask, mcol, mh = moss_block(nt, co, geo, 0.42, 0.68, math_(nt, 'MULTIPLY', dirt, 0.2))
    c = mix_col(nt, mask, c, mcol)
    metal = mix_f(nt, mask, metal, 0.0)
    rough = mix_f(nt, mask, rough, 0.97)

    h1 = math_(nt, 'ADD', math_(nt, 'MULTIPLY', rust, 0.4), math_(nt, 'MULTIPLY', seam, -1.0))
    h1 = math_(nt, 'ADD', h1, math_(nt, 'MULTIPLY', noise(nt, co, 60.0, 4, 0.6), 0.15))
    nrm = bump(nt, h1, 0.35, 0.01)
    nrm = bump(nt, mh, math_(nt, 'MULTIPLY', mask, 0.9), 0.03, nrm)

    feed(nt, sock(b, 'Base Color'), c)
    feed(nt, sock(b, 'Metallic'), metal)
    feed(nt, sock(b, 'Roughness'), rough)
    feed(nt, sock(b, 'Normal'), nrm)
    setin(b, 'Sheen Weight', 0.0)
    return m


def make_glass_mat():
    m, nt = new_mat("CoreGlass")
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    dist = N(nt, 'ShaderNodeVectorMath')
    dist.operation = 'DISTANCE'
    L(nt, co, dist.inputs[0])
    dist.inputs[1].default_value = (0.0, -0.9, 3.3)
    radial = maprange(nt, sock(dist, 'Value', True), 0.0, 0.4, 1.0, 0.0)
    ecol = mix_col(nt, radial, (0.15, 0.55, 0.9), (0.85, 0.98, 1.0))
    setin(b, 'Base Color', (0.01, 0.015, 0.018))
    setin(b, 'Roughness', 0.08)
    setin(b, 'Metallic', 0.0)
    setin(b, 'Coat Weight', 1.0)
    feed(nt, sock(b, 'Emission Color'), ecol)
    setin(b, 'Emission Strength', 0.0)
    return m, sock(b, 'Emission Strength')


def make_simple_mat(name, color, rough, metal=0.0):
    m, nt = new_mat(name)
    b, out = principled_out(nt)
    setin(b, 'Base Color', color)
    setin(b, 'Roughness', rough)
    setin(b, 'Metallic', metal)
    return m


def make_moss_mat():
    m, nt = new_mat("MossClump")
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    geo = N(nt, 'ShaderNodeNewGeometry')
    mask, mcol, mh = moss_block(nt, co, geo, -2.0, -1.0)
    feed(nt, sock(b, 'Base Color'), mcol)
    setin(b, 'Roughness', 0.95)
    setin(b, 'Sheen Weight', 0.35)
    feed(nt, sock(b, 'Normal'), bump(nt, mh, 0.9, 0.02))
    return m


def make_rock_mat():
    m, nt = new_mat("Rock")
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    geo = N(nt, 'ShaderNodeNewGeometry')
    rn = noise(nt, co, 2.5, 10, 0.65)
    col = ramp(nt, rn, [(0.3, (0.07, 0.07, 0.065)), (0.7, (0.22, 0.21, 0.19))])
    mask, mcol, mh = moss_block(nt, co, geo, 0.15, 0.55)
    col = mix_col(nt, mask, col, mcol)
    feed(nt, sock(b, 'Base Color'), col)
    feed(nt, sock(b, 'Roughness'), mix_f(nt, mask, 0.75, 0.96))
    nrm = bump(nt, noise(nt, co, 12.0, 8, 0.6), 0.5, 0.05)
    nrm = bump(nt, mh, math_(nt, 'MULTIPLY', mask, 0.8), 0.02, nrm)
    feed(nt, sock(b, 'Normal'), nrm)
    return m


def make_bark_mat():
    m, nt = new_mat("Bark")
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    geo = N(nt, 'ShaderNodeNewGeometry')
    mp = N(nt, 'ShaderNodeMapping')
    L(nt, co, sock(mp, 'Vector'))
    setin(mp, 'Scale', (2.4, 2.4, 0.3))
    mv = sock(mp, 'Vector', True)
    vor = N(nt, 'ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    L(nt, mv, sock(vor, 'Vector'))
    setin(vor, 'Scale', 3.2)
    fiss = maprange(nt, sock(vor, 'Distance', True), 0.0, 0.09)
    nb = noise(nt, mv, 7.0, 10, 0.62, 0.3)
    col = ramp(nt, nb, [(0.25, (0.03, 0.024, 0.019)), (0.55, (0.085, 0.07, 0.055)), (0.8, (0.17, 0.15, 0.12))])
    col = mix_col(nt, math_(nt, 'SUBTRACT', 1.0, fiss), col, (0.01, 0.008, 0.006))
    lich = maprange(nt, noise(nt, co, 1.3, 5, 0.6), 0.56, 0.62)
    col = mix_col(nt, math_(nt, 'MULTIPLY', lich, 0.6), col, (0.2, 0.22, 0.17))

    away = N(nt, 'ShaderNodeVectorMath')
    away.operation = 'DOT_PRODUCT'
    L(nt, sock(geo, 'Normal', True), away.inputs[0])
    away.inputs[1].default_value = (-0.85, -0.45, 0.0)
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, co, sock(sep, 'Vector'))
    low = maprange(nt, sock(sep, 'Z', True), 0.0, 3.5, 0.45, 0.0)
    extra = math_(nt, 'ADD', math_(nt, 'MULTIPLY', sock(away, 'Value', True), 0.75), low)
    mask, mcol, mh = moss_block(nt, co, geo, 0.42, 0.8, extra)

    col = mix_col(nt, mask, col, mcol)
    feed(nt, sock(b, 'Base Color'), col)
    feed(nt, sock(b, 'Roughness'), mix_f(nt, mask, 0.88, 0.96))
    height = math_(nt, 'ADD', math_(nt, 'MULTIPLY', fiss, 0.7), math_(nt, 'MULTIPLY', nb, 0.3))
    nrm = bump(nt, height, 0.45, 0.03)
    nrm = bump(nt, mh, math_(nt, 'MULTIPLY', mask, 0.8), 0.02, nrm)
    feed(nt, sock(b, 'Normal'), nrm)
    d = N(nt, 'ShaderNodeDisplacement')
    feed(nt, sock(d, 'Height'), height)
    setin(d, 'Midlevel', 0.5)
    setin(d, 'Scale', 0.05)
    L(nt, sock(d, 'Displacement', True), sock(out, 'Displacement'))
    set_disp(m, 'BOTH')
    return m


def make_leaf_mat(name, c_dark, c_mid, c_light, trans_col, trans_amt):
    m, nt = new_mat(name)
    out = N(nt, 'ShaderNodeOutputMaterial')
    b = N(nt, 'ShaderNodeBsdfPrincipled')
    tr = N(nt, 'ShaderNodeBsdfTranslucent')
    mx = N(nt, 'ShaderNodeMixShader')
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    rnd = sock(N(nt, 'ShaderNodeObjectInfo'), 'Random', True)
    col = ramp(nt, rnd, [(0.0, c_dark), (0.5, c_mid), (1.0, c_light)])
    col = mix_col(nt, math_(nt, 'MULTIPLY', noise(nt, co, 6.0, 2, 0.5), 0.45), col, (0.13, 0.12, 0.03))
    feed(nt, sock(b, 'Base Color'), col)
    setin(b, 'Roughness', 0.5)
    setin(b, 'Specular IOR Level', 0.4)
    setin(tr, 'Color', trans_col)
    mx.inputs[0].default_value = trans_amt
    L(nt, sock(b, 'BSDF', True), mx.inputs[1])
    L(nt, sock(tr, 'BSDF', True), mx.inputs[2])
    L(nt, sock(mx, 'Shader', True), sock(out, 'Surface'))
    return m


def make_ground_mat():
    m, nt = new_mat("ForestFloor")
    b, out = principled_out(nt)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    v1 = N(nt, 'ShaderNodeTexVoronoi')
    L(nt, co, sock(v1, 'Vector'))
    setin(v1, 'Scale', 9.0)
    leaf = ramp(nt, sock(v1, 'Color', True),
                [(0.15, (0.045, 0.022, 0.01)), (0.4, (0.13, 0.055, 0.02)),
                 (0.65, (0.24, 0.12, 0.04)), (0.88, (0.32, 0.2, 0.07))])
    soil = maprange(nt, noise(nt, co, 4.0, 6, 0.6), 0.47, 0.6)
    col = mix_col(nt, soil, leaf, (0.02, 0.015, 0.01))
    mosspatch = maprange(nt, noise(nt, co, 0.25, 5, 0.6), 0.5, 0.62)
    mcol = ramp(nt, noise(nt, co, 20.0, 8, 0.65),
                [(0.3, (0.02, 0.04, 0.008)), (0.6, (0.06, 0.11, 0.02)), (0.85, (0.13, 0.18, 0.03))])
    col = mix_col(nt, mosspatch, col, mcol)
    feed(nt, sock(b, 'Base Color'), col)
    feed(nt, sock(b, 'Roughness'), mix_f(nt, soil, 0.85, 0.62))
    h = math_(nt, 'ADD', math_(nt, 'MULTIPLY', sock(v1, 'Distance', True), 0.6),
              math_(nt, 'MULTIPLY', noise(nt, co, 30.0, 6, 0.6), 0.4))
    feed(nt, sock(b, 'Normal'), bump(nt, h, 0.5, 0.03))
    return m


def make_mist_mat():
    m, nt = new_mat("Mist")
    out = N(nt, 'ShaderNodeOutputMaterial')
    vs = N(nt, 'ShaderNodeVolumeScatter')
    setin(vs, 'Color', (0.86, 0.9, 1.0))
    setin(vs, 'Anisotropy', 0.6)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    mp = N(nt, 'ShaderNodeMapping')
    L(nt, co, sock(mp, 'Vector'))
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, co, sock(sep, 'Vector'))
    base = maprange(nt, sock(sep, 'Z', True), 0.0, 13.0, 0.032, 0.004)
    var = maprange(nt, noise(nt, sock(mp, 'Vector', True), 0.07, 3, 0.55), 0.3, 0.7, 0.55, 1.45)
    feed(nt, sock(vs, 'Density'), math_(nt, 'MULTIPLY', base, var))
    L(nt, sock(vs, 'Volume', True), sock(out, 'Volume'))
    try:
        m.cycles.homogeneous_volume = False
    except Exception:
        pass
    return m, sock(mp, 'Location')


# ---- shot 2 materials


def make_val(nt, v=0.0):
    n = N(nt, 'ShaderNodeValue')
    n.outputs[0].default_value = v
    return n.outputs[0]


def make_flame_mat():
    m, nt = new_mat("EngineFlame")
    out = N(nt, 'ShaderNodeOutputMaterial')
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    mp = N(nt, 'ShaderNodeMapping')
    L(nt, co, sock(mp, 'Vector'))
    sep = N(nt, 'ShaderNodeSeparateXYZ')
    L(nt, co, sock(sep, 'Vector'))
    along = maprange(nt, sock(sep, 'Z', True), -1.0, 0.0, 0.0, 1.0)      # 1 at the nozzle, 0 at the tip
    lw = N(nt, 'ShaderNodeLayerWeight')
    setin(lw, 'Blend', 0.4)
    core = math_(nt, 'SUBTRACT', 1.0, sock(lw, 'Facing', True), clamp=True)
    turb = maprange(nt, noise(nt, sock(mp, 'Vector', True), 3.5, 3, 0.6, 0.8), 0.3, 0.7, 0.55, 1.25)
    fac = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', along, core), turb, clamp=True)
    col = ramp(nt, along, [(0.0, (1.0, 0.3, 0.06)), (0.55, (1.0, 0.6, 0.24)), (1.0, (1.0, 0.93, 0.8))])
    val = make_val(nt, 0.0)
    em = N(nt, 'ShaderNodeEmission')
    feed(nt, sock(em, 'Color'), col)
    feed(nt, sock(em, 'Strength'), math_(nt, 'MULTIPLY', val, math_(nt, 'MULTIPLY', fac, along)))
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    mx = N(nt, 'ShaderNodeMixShader')
    feed(nt, mx.inputs[0], fac)
    L(nt, sock(tr, 'BSDF', True), mx.inputs[1])
    L(nt, sock(em, 'Emission', True), mx.inputs[2])
    L(nt, sock(mx, 'Shader', True), sock(out, 'Surface'))
    return m, val, sock(mp, 'Location')


def make_trail_mat():
    m, nt = new_mat("TrailGlow")
    out = N(nt, 'ShaderNodeOutputMaterial')
    lw = N(nt, 'ShaderNodeLayerWeight')
    setin(lw, 'Blend', 0.5)
    core = math_(nt, 'POWER', math_(nt, 'SUBTRACT', 1.0, sock(lw, 'Facing', True), clamp=True), 2.0)
    val = make_val(nt, 0.0)
    em = N(nt, 'ShaderNodeEmission')
    setin(em, 'Color', (1.0, 0.74, 0.45))
    feed(nt, sock(em, 'Strength'), math_(nt, 'MULTIPLY', val, core))
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    mx = N(nt, 'ShaderNodeMixShader')
    feed(nt, mx.inputs[0], math_(nt, 'MULTIPLY', core, math_(nt, 'MINIMUM', val, 0.9)))
    L(nt, sock(tr, 'BSDF', True), mx.inputs[1])
    L(nt, sock(em, 'Emission', True), mx.inputs[2])
    L(nt, sock(mx, 'Shader', True), sock(out, 'Surface'))
    return m, val


def make_trail_mist_mat():
    m, nt = new_mat("TrailMist")
    out = N(nt, 'ShaderNodeOutputMaterial')
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    lw = N(nt, 'ShaderNodeLayerWeight')
    setin(lw, 'Blend', 0.5)
    soft = math_(nt, 'POWER', math_(nt, 'SUBTRACT', 1.0, sock(lw, 'Facing', True), clamp=True), 1.5)
    wisp = maprange(nt, noise(nt, co, 0.6, 4, 0.6, 0.5), 0.3, 0.75, 0.2, 1.0)
    val = make_val(nt, 0.0)
    fac = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', soft, wisp), val, clamp=True)
    tl = N(nt, 'ShaderNodeBsdfTranslucent')
    setin(tl, 'Color', (0.92, 0.9, 0.86))
    em = N(nt, 'ShaderNodeEmission')
    setin(em, 'Color', (1.0, 0.7, 0.45))
    setin(em, 'Strength', 0.25)
    add = N(nt, 'ShaderNodeAddShader')
    L(nt, sock(tl, 'BSDF', True), add.inputs[0])
    L(nt, sock(em, 'Emission', True), add.inputs[1])
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    mx = N(nt, 'ShaderNodeMixShader')
    feed(nt, mx.inputs[0], fac)
    L(nt, sock(tr, 'BSDF', True), mx.inputs[1])
    L(nt, sock(add, 'Shader', True), mx.inputs[2])
    L(nt, sock(mx, 'Shader', True), sock(out, 'Surface'))
    return m, val


def make_puff_mat(name):
    m, nt = new_mat(name)
    out = N(nt, 'ShaderNodeOutputMaterial')
    vs = N(nt, 'ShaderNodeVolumeScatter')
    setin(vs, 'Color', (0.9, 0.9, 0.95))
    setin(vs, 'Anisotropy', 0.45)
    co = sock(N(nt, 'ShaderNodeTexCoord'), 'Object', True)
    val = make_val(nt, 0.0)
    wisp = maprange(nt, noise(nt, co, 1.8, 4, 0.6, 0.6), 0.35, 0.7, 0.0, 1.0)
    feed(nt, sock(vs, 'Density'), math_(nt, 'MULTIPLY', val, wisp))
    L(nt, sock(vs, 'Volume', True), sock(out, 'Volume'))
    try:
        m.cycles.homogeneous_volume = False
    except Exception:
        pass
    return m, val


log("materials")
M_ARMOR = make_robot_mat("RobotArmor", (0.09, 0.115, 0.11), 0.56)
M_JOINT = make_robot_mat("RobotJoint", (0.05, 0.05, 0.05), 0.42)
M_EYE = make_simple_mat("RobotEye", (0.004, 0.004, 0.005), 0.2)
M_GLASS, EMIT_SOCK = make_glass_mat()
M_MOSS = make_moss_mat()
M_ROCK = make_rock_mat()
M_BARK = make_bark_mat()
M_LEAF = make_leaf_mat("Leaf", (0.03, 0.07, 0.01), (0.06, 0.13, 0.02), (0.12, 0.17, 0.03), (0.3, 0.42, 0.06), 0.38)
M_FERN = make_leaf_mat("Fern", (0.02, 0.06, 0.008), (0.05, 0.12, 0.015), (0.1, 0.16, 0.025), (0.25, 0.4, 0.05), 0.32)
M_GRASS = make_leaf_mat("Grass", (0.05, 0.08, 0.015), (0.1, 0.13, 0.03), (0.18, 0.17, 0.05), (0.3, 0.35, 0.08), 0.3)
M_FAR = make_leaf_mat("FarFoliage", (0.01, 0.02, 0.006), (0.02, 0.035, 0.01), (0.03, 0.05, 0.012), (0.08, 0.12, 0.02), 0.2)
M_GROUND = make_ground_mat()
M_MIST, MIST_LOC = make_mist_mat()
M_BLOCK = make_simple_mat("CanopyMass", (0.02, 0.04, 0.015), 0.9)
M_DEAD = make_leaf_mat("DeadLeaf", (0.12, 0.05, 0.015), (0.25, 0.12, 0.03), (0.4, 0.25, 0.06), (0.5, 0.28, 0.06), 0.35)
M_SOIL = make_simple_mat("Soil", (0.05, 0.035, 0.02), 0.95)
M_BIRD = make_simple_mat("Bird", (0.03, 0.025, 0.02), 0.7)
M_FLAME, FLAME_VAL, FLAME_SCROLL = make_flame_mat()
M_TRAIL, TRAIL_VAL = make_trail_mat()
M_TRAILMIST, TRAILMIST_VAL = make_trail_mist_mat()
M_RING1, RING1_VAL = make_puff_mat("WindRing1")
M_RING2, RING2_VAL = make_puff_mat("WindRing2")

# ------------------------------------------------------------------ mesh helpers


def TRS(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(scale))


def mesh_from_bm(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth and len(me.polygons):
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if mat is not None:
        me.materials.append(mat)
    me.update()
    return me


def obj_from_bm(name, bm, mat=None, coll=None, smooth=True):
    me = mesh_from_bm(name, bm, mat, smooth)
    ob = bpy.data.objects.new(name, me)
    (coll if coll is not None else scene.collection).objects.link(ob)
    return ob


def inst(name, data, loc, rot=(0, 0, 0), scale=1.0, coll=None):
    ob = bpy.data.objects.new(name, data)
    ob.location = Vector(loc)
    ob.rotation_euler = Euler(rot)
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else tuple(scale)
    (coll if coll is not None else scene.collection).objects.link(ob)
    return ob


def bm_box(loc, size, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=TRS(loc, rot, size))
    return bm


def bm_cyl(p0, p1, r0, r1=None, segs=32, bm=None):
    r1 = r0 if r1 is None else r1
    p0 = Vector(p0)
    p1 = Vector(p1)
    v = p1 - p0
    q = v.normalized().to_track_quat('Z', 'Y')
    bm = bm if bm is not None else bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r0, radius2=r1,
                          depth=v.length, matrix=Matrix.LocRotScale((p0 + p1) * 0.5, q, None))
    return bm


def bm_sphere(loc, r, scale=(1, 1, 1), segs=32):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r, matrix=TRS(loc, (0, 0, 0), scale))
    return bm


def bm_dome(loc, radii, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001], context='VERTS')
    bmesh.ops.transform(bm, matrix=TRS(loc, rot, radii), verts=bm.verts)
    return bm


def bm_torus(loc, R, r, rot=(0, 0, 0), seg=48, sides=16):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(sides):
            t = 2 * math.pi * j / sides
            ring.append(bm.verts.new(((R + r * math.cos(t)) * math.cos(a),
                                      (R + r * math.cos(t)) * math.sin(a), r * math.sin(t))))
        rings.append(ring)
    for i in range(seg):
        for j in range(sides):
            a = rings[i][j]
            b = rings[(i + 1) % seg][j]
            c = rings[(i + 1) % seg][(j + 1) % sides]
            d = rings[i][(j + 1) % sides]
            bm.faces.new((a, b, c, d))
    bmesh.ops.transform(bm, matrix=TRS(loc, rot), verts=bm.verts)
    return bm


ROBOT_PARTS = set()


def part(name, bm, mat, bevel=0.05, segs=3, sub=2, G=None, smooth=True, solid=0.0):
    if G is not None:
        bmesh.ops.transform(bm, matrix=G, verts=bm.verts)
    ob = obj_from_bm(name, bm, mat, C_ROBOT, smooth)
    if solid:
        s = ob.modifiers.new("Solid", 'SOLIDIFY')
        s.thickness = solid
        s.offset = 1.0
        s.use_even_offset = True
    if bevel > 0:
        bv = ob.modifiers.new("Bevel", 'BEVEL')
        bv.width = bevel
        bv.segments = segs
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(40)
    if sub > 0:
        sd = ob.modifiers.new("Subsurf", 'SUBSURF')
        sd.levels = sub
        sd.render_levels = sub
    ROBOT_PARTS.add(ob.name)
    return ob


# ------------------------------------------------------------------ the robot
log("robot")
A, J = M_ARMOR, M_JOINT
V = Vector

part("Pelvis", bm_box((0, 0.35, 1.5), (1.9, 1.3, 0.9)), A, 0.08)
part("Codpiece", bm_box((0, -0.32, 1.45), (0.8, 0.3, 0.7)), A, 0.05)
part("Abdomen1", bm_cyl((0, 0.3, 1.85), (0, 0.3, 2.2), 0.78), J, 0.03, 2, 1)
part("Abdomen2", bm_cyl((0, 0.28, 2.2), (0, 0.26, 2.5), 0.86, 0.9), J, 0.03, 2, 1)
part("Chest", bm_box((0, 0.2, 3.35), (2.8, 1.9, 2.0)), A, 0.14)
part("ChestUpper", bm_box((0, 0.08, 4.02), (2.55, 1.75, 0.55)), A, 0.08)
part("BackPack", bm_box((0, 1.1, 3.55), (1.9, 0.6, 1.5)), A, 0.08)
for s in (-1, 1):
    part(f"Pec{s}", bm_box((s * 0.98, -0.8, 3.45), (0.78, 0.16, 0.95), (-0.08, 0, s * 0.18)), A, 0.04)
    part(f"HipSkirt{s}", bm_box((s * 0.95, 0.0, 1.45), (0.55, 1.1, 0.75), (0, s * 0.25, 0)), A, 0.05)

# chest core window
part("CoreCollar", bm_cyl((0, -0.68, 3.3), (0, -0.9, 3.3), 0.56), J, 0.03, 2, 1)
part("CoreRing", bm_torus((0, -0.95, 3.3), 0.47, 0.1, (math.pi / 2, 0, 0)), J, 0, 0, 1)
glass_ob = obj_from_bm("CoreGlass", bm_cyl((0, -0.88, 3.3), (0, -0.92, 3.3), 0.4, segs=48), M_GLASS, C_ROBOT)

# neck
part("Neck1", bm_cyl((0, 0.15, 4.3), (0, 0.15, 4.6), 0.5), J, 0.03, 2, 1)
part("Neck2", bm_cyl((0, 0.12, 4.58), (0, 0.12, 4.83), 0.42), J, 0.03, 2, 1)
part("Neck3", bm_cyl((0, 0.1, 4.8), (0, 0.1, 5.05), 0.36), J, 0.03, 2, 1)
for s in (-1, 1):
    part(f"NeckCable{s}", bm_cyl((s * 0.32, -0.12, 4.28), (s * 0.24, -0.06, 5.0), 0.06, segs=12), J, 0, 0, 1)

# helmet (bowed forward, turned slightly toward camera)
P = Matrix.Translation(V((0, 0.1, 4.85)))
G_HEAD = P @ Matrix.Rotation(0.12, 4, 'Z') @ Matrix.Rotation(0.2, 4, 'X') @ P.inverted()
part("Helmet", bm_box((0, 0.02, 5.45), (1.35, 1.45, 1.05)), A, 0.16, G=G_HEAD)
part("Jaw", bm_box((0, -0.38, 4.98), (1.0, 0.75, 0.38)), A, 0.06, G=G_HEAD)
part("VisorRidge", bm_box((0, -0.72, 5.6), (1.5, 0.3, 0.17), (0.25, 0, 0)), A, 0.05, G=G_HEAD)
part("Crest", bm_box((0, 0.1, 6.02), (0.2, 1.25, 0.22)), A, 0.05, G=G_HEAD)
part("Antenna", bm_cyl((0.45, 0.4, 5.9), (0.6, 0.6, 6.5), 0.035, segs=12), J, 0, 0, 1, G=G_HEAD)
for s in (-1, 1):
    part(f"EyeSlit{s}", bm_box((s * 0.28, -0.735, 5.4), (0.32, 0.09, 0.065), (0, 0, s * -0.08)), M_EYE, 0.015, 2, 0, G=G_HEAD)
    part(f"Ear{s}", bm_cyl((s * 0.66, 0.05, 5.4), (s * 0.84, 0.05, 5.4), 0.24), J, 0.03, 2, 1, G=G_HEAD)

# shoulders + arms + hands
for s in (-1, 1):
    S = V((s * 1.75, 0.15, 3.85))
    E = V((s * 2.3, -0.6, 2.1))
    W = V((s * 2.38, -1.8, 0.6))
    part(f"ShoulderJ{s}", bm_sphere(S, 0.55), J, 0, 0, 1)
    layers = [((s * 1.72, 0.2, 4.28), (0.98, 0.92, 0.62), s * 0.15),
              ((s * 1.9, 0.2, 3.98), (0.92, 0.88, 0.52), s * 0.45),
              ((s * 2.04, 0.2, 3.7), (0.82, 0.8, 0.42), s * 0.75)]
    for i, (c, rad, ry) in enumerate(layers):
        part(f"Pauldron{s}_{i}", bm_dome(c, rad, (0, ry, 0)), A, 0.0, 0, 1, solid=0.07)
    part(f"UpperArm{s}", bm_cyl(S, E, 0.36, 0.33), J, 0.03, 2, 1)
    part(f"ArmSleeve{s}", bm_cyl(S.lerp(E, 0.2), S.lerp(E, 0.75), 0.44, 0.42), A, 0.03, 2, 1)
    part(f"Elbow{s}", bm_sphere(E, 0.43), J, 0, 0, 1)
    part(f"ElbowPlate{s}", bm_box(E + V((0, 0.38, 0.05)), (0.55, 0.25, 0.6)), A, 0.05)
    part(f"Forearm{s}", bm_cyl(E, W, 0.47, 0.38), A, 0.04, 2, 1)
    for t in (0.28, 0.62):
        a0 = E.lerp(W, t - 0.04)
        a1 = E.lerp(W, t + 0.04)
        part(f"ForearmBand{s}_{t}", bm_cyl(a0, a1, 0.5 - 0.09 * t), J, 0.02, 2, 1)
    part(f"Wrist{s}", bm_sphere(W, 0.32), J, 0, 0, 1)
    part(f"Palm{s}", bm_box((s * 2.42, -2.3, 0.32), (0.8, 0.85, 0.38), (0, 0, s * 0.08)), A, 0.06)
    for o in (-0.28, -0.095, 0.095, 0.28):
        x = s * 2.42 + o
        p0, p1, p2 = V((x, -2.62, 0.34)), V((x, -2.98, 0.3)), V((x, -3.25, 0.13))
        part(f"Finger{s}_{o}_a", bm_cyl(p0, p1, 0.09, segs=16), J, 0.02, 2, 1)
        part(f"Finger{s}_{o}_b", bm_cyl(p1, p2, 0.085, segs=16), J, 0.02, 2, 1)
        part(f"Knuckle{s}_{o}_a", bm_sphere(p0, 0.105, segs=16), J, 0, 0, 1)
        part(f"Knuckle{s}_{o}_b", bm_sphere(p1, 0.1, segs=16), J, 0, 0, 1)
        part(f"Tip{s}_{o}", bm_sphere(p2, 0.085, segs=16), J, 0, 0, 1)
    t0, t1, t2 = V((s * 2.0, -2.15, 0.36)), V((s * 1.88, -2.45, 0.3)), V((s * 1.78, -2.72, 0.14))
    part(f"Thumb{s}_a", bm_cyl(t0, t1, 0.1, segs=16), J, 0.02, 2, 1)
    part(f"Thumb{s}_b", bm_cyl(t1, t2, 0.09, segs=16), J, 0.02, 2, 1)
    part(f"ThumbK{s}", bm_sphere(t1, 0.11, segs=16), J, 0, 0, 1)

# legs: left knee down, right leg bent up
H = V((-0.72, 0.45, 1.3)); K = V((-0.85, -0.6, 0.42)); AN = V((-0.85, 1.35, 0.38))
part("HipL", bm_sphere(H, 0.45), J, 0, 0, 1)
part("ThighL", bm_cyl(H, K, 0.55, 0.5), A, 0.04, 2, 1)
part("KneeL", bm_sphere(K, 0.5), J, 0, 0, 1)
part("KneeCapL", bm_box((-0.85, -1.05, 0.55), (0.72, 0.3, 0.75), (0.25, 0, 0)), A, 0.06)
part("ShinL", bm_cyl(K, AN, 0.5, 0.4), A, 0.04, 2, 1)
part("ShinPlateL", bm_box(K.lerp(AN, 0.5) + V((0, 0, 0.42)), (0.6, 1.4, 0.18)), A, 0.05)
part("AnkleL", bm_sphere(AN, 0.33), J, 0, 0, 1)
part("FootL", bm_box((-0.85, 1.95, 0.32), (0.72, 0.95, 0.5), (0.55, 0, 0)), A, 0.06)

H = V((0.75, 0.45, 1.3)); K = V((0.95, -1.3, 1.95)); AN = V((1.0, -1.45, 0.48))
part("HipR", bm_sphere(H, 0.45), J, 0, 0, 1)
part("ThighR", bm_cyl(H, K, 0.55, 0.5), A, 0.04, 2, 1)
part("KneeR", bm_sphere(K, 0.5), J, 0, 0, 1)
part("KneeGuardR", bm_box((0.97, -1.72, 2.1), (0.75, 0.3, 0.85), (-0.25, 0, 0)), A, 0.06)
part("ShinR", bm_cyl(K, AN, 0.48, 0.4), A, 0.04, 2, 1)
part("ShinPlateR", bm_box(K.lerp(AN, 0.5) + V((0, -0.42, 0)), (0.62, 0.18, 1.2)), A, 0.05)
part("AnkleR", bm_sphere(AN, 0.33), J, 0, 0, 1)
part("FootR", bm_box((1.0, -1.95, 0.24), (0.82, 1.25, 0.46)), A, 0.06)

# ------------------------------------------------------------------ rivets + overgrowth on the robot (ray cast onto subdivided surfaces)
log("rivets + robot overgrowth")
bpy.context.view_layer.update()
DG = bpy.context.evaluated_depsgraph_get()


def cast(o, d, dist=60.0):
    hit, loc, nor, idx, ob, mtx = scene.ray_cast(DG, V(o), V(d).normalized(), distance=dist)
    return hit, V(loc), V(nor), (ob.name if (hit and ob is not None) else "")


rivet_hits = []
for x in [-1.2 + 2.4 * i / 8 for i in range(9)]:
    for z in (4.12, 2.6):
        rivet_hits.append(cast((x, -5, z), (0, 1, 0)))
for x in (-1.28, 1.28):
    for z in [2.7 + 1.3 * i / 4 for i in range(5)]:
        rivet_hits.append(cast((x, -5, z), (0, 1, 0)))
for s in (-1, 1):
    for dx in (-0.3, 0.3):
        for dz in (-0.36, 0.36):
            rivet_hits.append(cast((s * 0.98 + dx, -5, 3.45 + dz), (0, 1, 0)))
    for k in range(12):
        a = 2 * math.pi * k / 12
        rivet_hits.append(cast((s * 1.72 + 0.75 * math.cos(a), 0.2 + 0.7 * math.sin(a), 9), (0, 0, -1)))
    E = V((s * 2.3, -0.6, 2.1)); W = V((s * 2.38, -1.8, 0.6))
    for t in (0.2, 0.4, 0.55, 0.75, 0.9):
        p = E.lerp(W, t)
        rivet_hits.append(cast((p.x, p.y, p.z + 3.0), (0, 0, -1)))
for x in (-0.6, -0.3, 0.0, 0.3, 0.6):
    rivet_hits.append(cast((x, -5, 5.62), (0, 1, 0)))

plant_hits = []
yy = -3.5
while yy < 2.3:
    xx = -3.2
    while xx < 3.2:
        jx, jy = RND.uniform(-0.08, 0.08), RND.uniform(-0.08, 0.08)
        h = cast((xx + jx, yy + jy, 9.0), (0, 0, -1))
        if h[0] and h[3] in ROBOT_PARTS and h[2].z > 0.55 and not h[3].startswith("EyeSlit"):
            plant_hits.append(h)
        xx += 0.17
    yy += 0.17

# where the bird lands: top front of the right pauldron
_ph = cast((1.9, -0.2, 9.0), (0, 0, -1))
PERCH = (_ph[1] if (_ph[0] and _ph[3] in ROBOT_PARTS) else V((1.9, -0.2, 4.85))) + V((0, 0, 0.02))

ATTACH = []  # (object, host robot part name): everything that rides on the robot

rivet_bm = bmesh.new()
bmesh.ops.create_uvsphere(rivet_bm, u_segments=12, v_segments=6, radius=0.045, matrix=TRS((0, 0, 0), (0, 0, 0), (1, 1, 0.5)))
RIVET_ME = mesh_from_bm("RivetMesh", rivet_bm, J)
for i, (hit, loc, nor, name) in enumerate(rivet_hits):
    if not hit or name not in ROBOT_PARTS:
        continue
    ob = inst(f"Rivet_{i}", RIVET_ME, loc, coll=C_ROBOT)
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = nor.normalized().to_track_quat('Z', 'Y')
    ATTACH.append((ob, name))


# ------------------------------------------------------------------ plant meshes


def make_fern_mesh(name, seed, nfr=8, Lr=1.0, mat=None):
    rnd = random.Random(seed)
    bm = bmesh.new()
    side = V((1, 0, 0))
    for f in range(nfr):
        yaw = 2 * math.pi * f / nfr + rnd.uniform(-0.3, 0.3)
        pitch = rnd.uniform(0.55, 1.15)
        Lf = Lr * rnd.uniform(0.7, 1.1)
        droop = rnd.uniform(0.55, 0.95)
        Rz = Matrix.Rotation(yaw, 3, 'Z')
        st = 18
        pts = [V((0.0, Lf * (k / st) * math.cos(pitch),
                  Lf * (k / st) * math.sin(pitch) - droop * Lf * (k / st) ** 2 * 0.8)) for k in range(st + 1)]
        for k in range(st):
            p0, p1 = pts[k], pts[k + 1]
            fwd = (p1 - p0).normalized()
            up = side.cross(fwd).normalized()
            t = k / st
            wr = 0.007 * (1 - t) + 0.002
            q = [p0 + side * wr, p1 + side * wr * 0.8, p1 - side * wr * 0.8, p0 - side * wr]
            bm.faces.new([bm.verts.new(Rz @ v) for v in q])
            if k == 0:
                continue
            l = Lf * 0.24 * math.sin(math.pi * min(1.0, t * 1.04)) * (1.0 - 0.3 * t) + 0.012
            w = l * 0.26
            for sg in (-1.0, 1.0):
                sd = side * sg
                b0 = p0 + fwd * w * 0.55
                m1 = p0 + sd * l * 0.5 + fwd * w * 0.75 + up * l * 0.05
                tip = p0 + sd * l + fwd * l * 0.32 - up * l * (0.12 + 0.25 * t)
                m2 = p0 + sd * l * 0.5 - fwd * w * 0.15 + up * l * 0.05
                b1 = p0 - fwd * w * 0.35
                bm.faces.new([bm.verts.new(Rz @ v) for v in (b0, m1, tip, m2, b1)])
    return mesh_from_bm(name, bm, mat, smooth=False)


def make_tuft_mesh(name, seed, n=28, Hh=0.35, mat=None):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        tilt = rnd.uniform(0.1, 0.7)
        h = Hh * rnd.uniform(0.5, 1.1)
        w = rnd.uniform(0.006, 0.012)
        dirh = V((math.cos(a), math.sin(a), 0))
        sd = V((-math.sin(a), math.cos(a), 0))
        base = dirh * rnd.uniform(0, 0.04)
        prev = None
        for k in range(5):
            t = k / 4
            p = base + dirh * (math.sin(tilt) * h * t + 0.4 * h * t * t * tilt) + \
                V((0, 0, math.cos(tilt) * h * t - 0.25 * h * t * t * tilt))
            ww = w * (1 - t) + 0.0005
            vl = bm.verts.new(p - sd * ww)
            vr = bm.verts.new(p + sd * ww)
            if prev is not None:
                bm.faces.new((prev[0], prev[1], vr, vl))
            prev = (vl, vr)
    return mesh_from_bm(name, bm, mat, smooth=False)


def make_cluster_mesh(name, seed, n=200, R=1.0, flat=0.62, lsz=(0.075, 0.12), mat=None):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        while True:
            v = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
            if 1e-4 < v.length <= 1.0:
                break
        v = v.normalized() * (v.length ** 0.45)
        c = V((v.x * R, v.y * R, v.z * R * flat))
        Ll = rnd.uniform(*lsz)
        w = Ll * 0.45
        nd = V((v.x * 0.7 + rnd.uniform(-0.5, 0.5), v.y * 0.7 + rnd.uniform(-0.5, 0.5), 1.0 + v.z * 0.5)).normalized()
        rot = nd.to_track_quat('Z', 'Y').to_matrix() @ Matrix.Rotation(rnd.uniform(0, 2 * math.pi), 3, 'Z')
        pts = [(0, 0), (w * 0.5, Ll * 0.22), (w * 0.55, Ll * 0.55), (w * 0.25, Ll * 0.85), (0, Ll),
               (-w * 0.25, Ll * 0.85), (-w * 0.55, Ll * 0.55), (-w * 0.5, Ll * 0.22)]
        vs = []
        for (x, y) in pts:
            z = -abs(x) * 0.35 - (y / Ll) ** 2 * Ll * 0.18
            vs.append(bm.verts.new(c + rot @ V((x, y - Ll * 0.25, z))))
        bm.faces.new(vs)
    return mesh_from_bm(name, bm, mat, smooth=False)


def make_blob_mesh(name, seed, sub=3, amp=0.3, mat=None, flat=1.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * mnoise.noise(n * 1.3 + V((seed, 0, 0))) + amp * 0.35 * mnoise.noise(n * 4.0 + V((0, seed, 0)))
        v.co = V((n.x * k, n.y * k, n.z * k * flat))
    return mesh_from_bm(name, bm, mat, smooth=True)


def make_single_leaf_mesh(name, mat):
    bm = bmesh.new()
    Ll, w = 1.0, 0.45
    pts = [(0, 0), (w * 0.5, Ll * 0.22), (w * 0.55, Ll * 0.55), (w * 0.25, Ll * 0.85), (0, Ll),
           (-w * 0.25, Ll * 0.85), (-w * 0.55, Ll * 0.55), (-w * 0.5, Ll * 0.22)]
    vs = [bm.verts.new((x, y - Ll * 0.5, -abs(x) * 0.35 + 0.08 * math.sin(math.pi * y / Ll))) for (x, y) in pts]
    bm.faces.new(vs)
    return mesh_from_bm(name, bm, mat, smooth=False)


FERNS_BIG = [make_fern_mesh(f"FernBig{i}", 100 + i, 8, 1.0 + 0.15 * i, M_FERN) for i in range(3)]
FERNS_SMALL = [make_fern_mesh(f"FernSmall{i}", 200 + i, 6, 0.45, M_FERN) for i in range(2)]
TUFTS = [make_tuft_mesh(f"Tuft{i}", 300 + i, 30, 0.32, M_GRASS) for i in range(2)]
CLUSTERS = [make_cluster_mesh(f"LeafCluster{i}", 400 + i, 220, 1.0, 0.62, (0.075, 0.12), M_LEAF) for i in range(3)]
MOSS_CLUMP = make_blob_mesh("MossClumpMesh", 500, 2, 0.25, M_MOSS, 0.35)

# robot overgrowth
for i, (hit, loc, nor, name) in enumerate(plant_hits):
    r = RND.random()
    yaw = RND.uniform(0, 2 * math.pi)
    ob = None
    if r < 0.55:
        sc = RND.uniform(0.08, 0.2)
        ob = inst(f"RMoss_{i}", MOSS_CLUMP, loc - nor * 0.02, (RND.uniform(-0.2, 0.2), RND.uniform(-0.2, 0.2), yaw),
                  (sc, sc, sc * RND.uniform(0.7, 1.3)), C_PLANTS)
    elif r < 0.6:
        ob = inst(f"RTuft_{i}", TUFTS[i % 2], loc - nor * 0.01, (0, 0, yaw), RND.uniform(0.4, 0.8), C_PLANTS)
    elif r < 0.625 and loc.z > 1.8:
        ob = inst(f"RFern_{i}", FERNS_SMALL[i % 2], loc - nor * 0.01, (0, 0, yaw), RND.uniform(0.5, 0.9), C_PLANTS)
    if ob is not None:
        ATTACH.append((ob, name))

# two saplings: on the left pauldron and on the helmet (one object each so they ride their own part)
sap_targets = [V((-1.7, 0.3)), V((0.15, -0.1))]
for k, tgt in enumerate(sap_targets):
    best = None
    for h in plant_hits:
        d = (V((h[1].x, h[1].y)) - tgt).length
        if h[2].z > 0.7 and (best is None or d < best[0]):
            best = (d, h)
    if best is None:
        continue
    base = best[1][1]
    top = base + V((RND.uniform(-0.1, 0.1), RND.uniform(-0.1, 0.1), 0.7 + 0.2 * k))
    stem = obj_from_bm(f"SaplingStem{k}", bm_cyl(base - V((0, 0, 0.05)), top, 0.018, 0.008, 8), M_BARK, C_PLANTS)
    lv = inst(f"SaplingLeaves{k}", CLUSTERS[k], top, (0, 0, RND.uniform(0, 6.28)), (0.32, 0.32, 0.4), C_PLANTS)
    ATTACH.append((stem, best[1][3]))
    ATTACH.append((lv, best[1][3]))

# engine nozzles under the backpack (added after the overgrowth pass so nothing grows in them)
for s in (-1, 1):
    part(f"EngineNozzle{s}", bm_cyl((s * 0.55, 1.25, 2.85), (s * 0.55, 1.25, 2.45), 0.2, 0.27), J, 0.02, 2, 1)

# ------------------------------------------------------------------ sun / gap geometry (gap in canopy)
T1 = V((0.7, -0.5, 4.1))           # where the shaft lands (robot right chest/shoulder)
T0 = V((2.6, -2.6, 0.2))           # forest layout only (same as shot 1)
D1 = V((0.6, 0.32, 0.73)).normalized()
G = T1 + D1 * ((18.0 - T1.z) / D1.z)  # gap point in the canopy (z = 18)
D0 = (G - T0).normalized()


def sun_blocked(p, rad):
    p = V(p)
    for s in (0.0, 0.25, 0.5, 0.75, 1.0):
        tz = T0.z + (T1.z - T0.z) * s
        if p.z < tz - 0.5:
            continue
        d = D0.lerp(D1, s).normalized()
        q = G + d * ((p.z - G.z) / d.z)
        if math.hypot(p.x - q.x, p.y - q.y) < rad + 0.9 + 1.7 * s:
            return True
    return False


def seg_dist(p, a, b):
    p, a, b = V(p), V(a), V(b)
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


C0 = V((3.4, -17.5, 1.9))
C1 = V((1.2, -11.5, 2.3))
CMID = C0.lerp(C1, 0.5)
ROBOT_VIEW_PTS = [V((0, -0.4, 5.5)), V((0, -0.9, 3.3)), V((1.8, 0.2, 4.2)), V((-1.8, 0.2, 4.2)), V((0, -1.5, 1.2))]


def cam_dist2d(x, y):
    return seg_dist(V((x, y, 0)), V((C0.x, C0.y - 2.0, 0)), V((C1.x, C1.y, 0)))


def in_robot_view(p, rad):
    for cam in (C0, CMID, C1):
        for t in ROBOT_VIEW_PTS:
            if seg_dist(p, cam, t) < rad + 0.6:
                return True
    return False


# ------------------------------------------------------------------ ground


def ground_h(x, y):
    h = 0.45 * mnoise.noise(V((x * 0.06, y * 0.06, 0.3))) + 0.12 * mnoise.noise(V((x * 0.25, y * 0.25, 1.7)))
    r = math.sqrt(x * x + (y + 0.5) ** 2)
    fall = min(1.0, max(0.0, (r - 3.5) / 4.0))
    return h * fall + 0.2 * math.exp(-(r / 2.5) ** 2)


log("ground")
gbm = bmesh.new()
bmesh.ops.create_grid(gbm, x_segments=240, y_segments=240, size=1.0)
hx = max(abs(v.co.x) for v in gbm.verts) or 1.0
for v in gbm.verts:
    x = v.co.x / hx * 60.0
    y = v.co.y / hx * 60.0 + 8.0
    v.co = V((x, y, ground_h(x, y)))
obj_from_bm("Ground", gbm, M_GROUND, C_FOREST)

# ------------------------------------------------------------------ trees


def trunk_center(z, lean, seed):
    return (lean[0] * z + 0.15 * math.sin(z * 0.25 + seed), lean[1] * z + 0.15 * math.cos(z * 0.21 + seed * 1.3))


def make_trunk_mesh(name, Hh, r, seed, lean, mat):
    rnd = random.Random(seed)
    bm = bmesh.new()
    segs = 40
    zs = [-0.5, -0.2, 0.0, 0.08, 0.18, 0.3, 0.45, 0.62, 0.82, 1.05, 1.35, 1.7, 2.1, 2.6, 3.2, 3.9]
    z = 4.7
    while z < Hh:
        zs.append(z)
        z += 0.8
    zs.append(Hh)
    nl = rnd.randint(4, 6)
    ph = rnd.uniform(0, 6.28)
    rings = []
    for z in zs:
        zc = max(z, 0.0)
        t = zc / Hh
        cx, cy = trunk_center(zc, lean, seed)
        ring = []
        for i in range(segs):
            th = 2 * math.pi * i / segs
            lobe = max(0.0, math.cos(nl * (th + ph))) ** 2
            flare = 1.0 + 1.7 * math.exp(-zc / 0.6) * (0.2 + 0.8 * lobe) + 0.25 * math.exp(-zc / 2.5)
            wob = 1.0 + 0.07 * mnoise.noise(V((math.cos(th) * 1.3 + seed, math.sin(th) * 1.3, zc * 0.35)))
            rr = r * (1.0 - 0.4 * t) * flare * wob
            ring.append(bm.verts.new((cx + rr * math.cos(th), cy + rr * math.sin(th), z)))
        rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for k in range(rnd.randint(2, 4)):
        zb = rnd.uniform(4.0, min(13.0, Hh - 2.0))
        th = rnd.uniform(0, 2 * math.pi)
        rad = r * (1 - 0.4 * zb / Hh)
        d = V((math.cos(th), math.sin(th), rnd.uniform(0.2, 0.6))).normalized()
        cx, cy = trunk_center(zb, lean, seed)
        p0 = V((cx, cy, zb)) + V((math.cos(th), math.sin(th), 0)) * rad * 0.5
        p1 = p0 + d * (rad * 0.5 + rnd.uniform(0.5, 1.4))
        bm_cyl(p0, p1, rad * 0.32, rad * 0.12, 12, bm)
    return mesh_from_bm(name, bm, mat, smooth=True), nl, ph


log("trees")
TRUNK_CANDIDATES = [
    (4.0, -12.54, 0.5), (-0.83, -9.55, 0.5), (5.6, -6.5, 0.6), (-6.0, -3.5, 0.7),
    (6.5, -1.5, 0.75), (-3.5, 9.0, 0.8), (3.0, 11.5, 0.7), (-9.0, 12.0, 0.9),
    (9.5, 10.0, 0.85), (0.0, 18.0, 0.8), (-6.0, 20.0, 0.75), (6.0, 22.0, 0.9),
    (-13.0, 4.0, 0.85), (13.0, 6.0, 0.8), (-15.0, -6.0, 0.8), (14.0, -5.0, 0.75),
    (-10.0, -9.5, 0.7), (11.0, -11.0, 0.7), (-3.0, 24.0, 0.9), (12.0, 18.0, 0.8),
]
TREES = []
for (x, y, r) in TRUNK_CANDIDATES:
    if len(TREES) >= 16:
        break
    seed = len(TREES) * 7 + 3
    lean = (RND.uniform(-0.02, 0.02), RND.uniform(-0.02, 0.02))
    blocked = False
    for k in range(53):
        z = k * 0.5
        cx, cy = trunk_center(z, lean, seed)
        if sun_blocked((x + cx, y + cy, z), r * (1.0 - 0.4 * z / 26.0)):
            blocked = True
            break
    if blocked:
        continue
    TREES.append((x, y, r, seed, lean))

branch_bm = bmesh.new()
for ti, (x, y, r, seed, lean) in enumerate(TREES):
    gz = ground_h(x, y)
    me, nl, ph = make_trunk_mesh(f"Trunk{ti}", 26.0, r, seed, lean, M_BARK)
    inst(f"Trunk{ti}", me, (x, y, gz), coll=C_FOREST)

    # surface roots continuing from the buttress lobes
    cu = bpy.data.curves.new(f"Roots{ti}", 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    cu.resolution_u = 8
    rr = random.Random(seed + 99)
    for k in range(nl):
        ang = -ph + (2 * math.pi * k) / nl + rr.uniform(-0.15, 0.15)
        length = rr.uniform(2.5, 5.0)
        npts = 7
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(npts - 1)
        px, py = x + math.cos(ang) * r * 1.4, y + math.sin(ang) * r * 1.4
        a = ang
        for j, bp in enumerate(sp.bezier_points):
            t = j / (npts - 1)
            rad = r * 0.38 * (1.0 - t) + 0.025
            bp.co = (px, py, ground_h(px, py) + rad * (0.45 - 0.9 * t) + 0.12 * (1.0 - t))
            bp.radius = rad
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
            a += rr.uniform(-0.35, 0.35)
            px += math.cos(a) * length / (npts - 1)
            py += math.sin(a) * length / (npts - 1)
    cu.materials.append(M_BARK)
    inst(f"Roots{ti}", cu, (0, 0, 0), coll=C_FOREST)

    # branches carrying foliage at mid height
    if y < 14.0:
        for k in range(rr.randint(3, 6)):
            zb = rr.uniform(5.0, 11.0)
            th = rr.uniform(0, 2 * math.pi)
            cx, cy = trunk_center(zb, lean, seed)
            rad = r * (1 - 0.4 * zb / 26.0)
            dirh = V((math.cos(th), math.sin(th), 0))
            start = V((x + cx, y + cy, gz + zb)) + dirh * rad * 0.7
            end = start + dirh * rr.uniform(2.0, 4.5) + V((0, 0, rr.uniform(0.3, 1.2)))
            sc = rr.uniform(1.2, 2.1)
            cpos = end + V((0, 0, 0.2))
            if seg_dist(cpos, C0 - V((0, 2, 0)), C1) < sc * 1.1 + 1.5:
                continue
            if in_robot_view(cpos, sc * 1.05) or sun_blocked(cpos, sc * 1.05):
                continue
            bm_cyl(start, end, 0.09 * r / 0.6 + 0.03, 0.03, 10, branch_bm)
            twig = end + V((rr.uniform(-0.8, 0.8), rr.uniform(-0.8, 0.8), rr.uniform(0.2, 0.7)))
            bm_cyl(end, twig, 0.03, 0.012, 6, branch_bm)
            inst(f"BranchLeaves{ti}_{k}", CLUSTERS[(ti + k) % 3], cpos, (rr.uniform(-0.2, 0.2), rr.uniform(-0.2, 0.2), rr.uniform(0, 6.28)),
                 (sc, sc, sc * 0.8), C_FOREST)
            inst(f"BranchLeavesB{ti}_{k}", CLUSTERS[(ti + k + 1) % 3], (cpos + twig) * 0.5 + V((0, 0, 0.3)),
                 (0, 0, rr.uniform(0, 6.28)), sc * 0.6, C_FOREST)
obj_from_bm("Branches", branch_bm, M_BARK, C_FOREST)

# fallen mossy log
log_me, _, _ = make_trunk_mesh("FallenLog", 7.0, 0.42, 77, (0.0, 0.0), M_BARK)
inst("FallenLog", log_me, (-6.5, 4.5, ground_h(-6.5, 4.5) + 0.25), (0, math.radians(88), 0.3), coll=C_FOREST)

# high canopy
log("canopy")
cr = random.Random(55)
for i in range(420):
    p = V((cr.uniform(-35, 40), cr.uniform(-30, 45), cr.uniform(14, 24)))
    sc = cr.uniform(2.2, 3.8)
    if sun_blocked(p, sc * 0.95):
        continue
    inst(f"Canopy{i}", CLUSTERS[i % 3], p, (cr.uniform(-0.3, 0.3), cr.uniform(-0.3, 0.3), cr.uniform(0, 6.28)),
         (sc, sc, sc * 0.75), C_FOREST)

# far forest silhouettes in the mist
far_stem_bm = bmesh.new()
fr = random.Random(66)
for i in range(34):
    a = fr.uniform(0, 2 * math.pi)
    rad = fr.uniform(34, 58)
    x, y = math.cos(a) * rad, 8 + math.sin(a) * rad
    sc = fr.uniform(5, 11)
    inst(f"FarBlob{i}", make_blob_mesh(f"FarBlobMesh{i}", 600 + i, 3, 0.3, M_FAR) if i < 6 else bpy.data.meshes[f"FarBlobMesh{i % 6}"],
         (x, y, fr.uniform(6, 16)), (0, 0, fr.uniform(0, 6.28)), (sc, sc, sc * 0.8), C_FOREST)
for i in range(26):
    a = fr.uniform(0, 2 * math.pi)
    rad = fr.uniform(20, 48)
    x, y = math.cos(a) * rad, 8 + math.sin(a) * rad
    r = fr.uniform(0.3, 0.6)
    if cam_dist2d(x, y) < 6.0 or sun_blocked((x, y, 10.0), r) or sun_blocked((x, y, 16.0), r):
        continue
    bm_cyl((x, y, -0.5), (x + fr.uniform(-0.5, 0.5), y + fr.uniform(-0.5, 0.5), 30.0), r, r * 0.6, 12, far_stem_bm)
obj_from_bm("FarStems", far_stem_bm, M_BARK, C_FOREST)

# ------------------------------------------------------------------ rocks, ferns, tufts, ground moss
log("ground cover")


def near_trunk(x, y, pad):
    for (tx, ty, r, _, _) in TREES:
        if math.hypot(x - tx, y - ty) < r * 1.8 + pad:
            return True
    return False


def in_robot_footprint(x, y):
    return -3.0 < x < 3.0 and -3.4 < y < 2.4


ROCK_MESHES = [make_blob_mesh(f"RockMesh{i}", 700 + i, 3, 0.28, M_ROCK) for i in range(4)]
rk = random.Random(77)
rock_spots = [(-3.3, -0.4), (3.4, 0.9), (1.6, 2.6), (-1.8, 2.9), (-3.6, -3.6)]
while len(rock_spots) < 24:
    x, y = rk.uniform(-14, 14), rk.uniform(-12, 22)
    if in_robot_footprint(x, y) or cam_dist2d(x, y) < 2.0 or near_trunk(x, y, 0.5):
        continue
    rock_spots.append((x, y))
for i, (x, y) in enumerate(rock_spots):
    sc = rk.uniform(0.3, 1.1)
    inst(f"Rock{i}", ROCK_MESHES[i % 4], (x, y, ground_h(x, y) - sc * 0.25),
         (rk.uniform(-0.3, 0.3), rk.uniform(-0.3, 0.3), rk.uniform(0, 6.28)),
         (sc * rk.uniform(0.9, 1.4), sc, sc * rk.uniform(0.5, 0.75)), C_FOREST)

fe = random.Random(88)
placed = 0
tries = 0
while placed < 280 and tries < 4000:
    tries += 1
    x, y = fe.uniform(-15, 15), fe.uniform(-17, 22)
    if in_robot_footprint(x, y) or cam_dist2d(x, y) < 1.3 or near_trunk(x, y, 0.2):
        continue
    sc = fe.uniform(0.6, 1.4)
    inst(f"Fern{placed}", FERNS_BIG[placed % 3], (x, y, ground_h(x, y) - 0.03),
         (fe.uniform(-0.15, 0.15), fe.uniform(-0.15, 0.15), fe.uniform(0, 6.28)), sc, C_PLANTS)
    placed += 1

for i in range(220):
    x, y = fe.uniform(-12, 12), fe.uniform(-15, 16)
    if cam_dist2d(x, y) < 0.8 or near_trunk(x, y, 0.0):
        continue
    if in_robot_footprint(x, y) and fe.random() < 0.6:
        continue
    inst(f"Tuft{i}", TUFTS[i % 2], (x, y, ground_h(x, y) - 0.02), (0, 0, fe.uniform(0, 6.28)), fe.uniform(0.6, 1.3), C_PLANTS)

for i in range(60):
    a = fe.uniform(0, 2 * math.pi)
    rr_ = fe.uniform(1.5, 4.5)
    x, y = math.cos(a) * rr_ * 1.2, math.sin(a) * rr_ - 0.5
    sc = fe.uniform(0.2, 0.5)
    inst(f"GroundMoss{i}", MOSS_CLUMP, (x, y, ground_h(x, y) - sc * 0.12), (0, 0, fe.uniform(0, 6.28)),
         (sc * 1.4, sc, sc * 0.8), C_PLANTS)

# ------------------------------------------------------------------ canopy shadow mass (invisible to camera, real for light) with the gap
log("atmosphere + lights")
blk = bmesh.new()
radii = [2.2, 2.6, 3.2, 4.2, 6.0, 9.0, 14.0, 22.0, 34.0, 50.0, 75.0, 95.0]
segs = 64
rings = [[blk.verts.new((rd * math.cos(2 * math.pi * i / segs), rd * math.sin(2 * math.pi * i / segs), 0.0))
          for i in range(segs)] for rd in radii]
for a, b in zip(rings[:-1], rings[1:]):
    for i in range(segs):
        j = (i + 1) % segs
        blk.faces.new((a[i], a[j], b[j], b[i]))
blocker = obj_from_bm("CanopyShadowMass", blk, M_BLOCK, C_FX, smooth=False)
blocker.location = G
blocker.scale = (1.0, 1.0, 1.0)
blocker.visible_camera = False
blocker.visible_glossy = False
blocker.visible_transmission = False

# mist volume
mbm = bmesh.new()
bmesh.ops.create_cube(mbm, size=1.0, matrix=TRS((2.5, 7.5, 6.5), (0, 0, 0), (95, 95, 15)))
mist = obj_from_bm("Mist", mbm, M_MIST, C_FX, smooth=False)

# world: golden morning sky (the end state of shot 1)
world = bpy.data.worlds.new("MorningSky")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
wnt = world.node_tree
for n in list(wnt.nodes):
    wnt.nodes.remove(n)
wtc = N(wnt, 'ShaderNodeTexCoord')
wsep = N(wnt, 'ShaderNodeSeparateXYZ')
L(wnt, sock(wtc, 'Generated', True), sock(wsep, 'Vector'))
wgrad = maprange(wnt, sock(wsep, 'Z', True), -0.05, 0.5)
wmix = mix_col(wnt, wgrad, (0.75, 0.6, 0.42), (0.4, 0.42, 0.5), return_node=True)
wbg = N(wnt, 'ShaderNodeBackground')
setin(wbg, 'Strength', 1.0)
wout = N(wnt, 'ShaderNodeOutputWorld')
L(wnt, sock(wmix, 'Result_Color', True), sock(wbg, 'Color'))
L(wnt, sock(wbg, 'Background', True), sock(wout, 'Surface'))


def dir_to_euler(d):
    return (-d).to_track_quat('-Z', 'Y').to_euler()


# sun: golden, shaft through the gap onto the robot
sun_d = bpy.data.lights.new("Sun", 'SUN')
sun_d.angle = math.radians(1.0)
sun_d.energy = 6.5
sun_d.color = (1.0, 0.7, 0.4)
sun = bpy.data.objects.new("Sun", sun_d)
sun.rotation_euler = dir_to_euler(D1)
C_FX.objects.link(sun)

# sky fill under the canopy
fill_d = bpy.data.lights.new("SkyFill", 'AREA')
fill_d.shape = 'DISK'
fill_d.size = 36.0
fill_d.energy = 520.0
fill_d.color = (0.9, 0.85, 0.75)
fill = bpy.data.objects.new("SkyFill", fill_d)
fill.location = (2.0, 0.0, 15.5)
fill.visible_camera = False
C_FX.objects.link(fill)

# chest core light
core_d = bpy.data.lights.new("CoreLight", 'POINT')
core_d.color = (0.6, 0.92, 1.0)
for attr in ("shadow_soft_size", "radius"):
    try:
        setattr(core_d, attr, 0.12)
        break
    except Exception:
        pass
core = bpy.data.objects.new("CoreLight", core_d)
core.location = (0.0, -1.25, 3.3)
core.visible_camera = False
C_FX.objects.link(core)

# camera: low, looking up
cam_d = bpy.data.cameras.new("Camera")
cam_d.lens = 28.0
cam_d.sensor_width = 36.0
cam_d.clip_start = 0.1
cam_d.clip_end = 300.0
cam = bpy.data.objects.new("Camera", cam_d)
C_FX.objects.link(cam)
scene.camera = cam
target = bpy.data.objects.new("CamTarget", None)
C_FX.objects.link(target)
con = cam.constraints.new('TRACK_TO')
con.target = target
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
cam_d.dof.use_dof = True
cam_d.dof.focus_object = target
cam_d.dof.aperture_fstop = 2.8
cam_d.dof.aperture_blades = 7

# ------------------------------------------------------------------ engines: flames + lights
log("engines")
fbm = bm_cyl((0, 0, 0), (0, 0, -1), 1.0, 0.04, 24)
FLAME_ME = mesh_from_bm("FlameMesh", fbm, M_FLAME, smooth=True)


def eng_light(name, loc):
    d = bpy.data.lights.new(name, 'POINT')
    d.color = (1.0, 0.6, 0.3)
    d.energy = 0.0
    for attr in ("shadow_soft_size", "radius"):
        try:
            setattr(d, attr, 0.35)
            break
        except Exception:
            pass
    ob = bpy.data.objects.new(name, d)
    ob.location = V(loc)
    C_FX.objects.link(ob)
    return ob


ENGINES = []  # (flame, light, group, radius, length, light power)
for s in (-1, 1):
    fl = inst(f"FlameBack{s}", FLAME_ME, (s * 0.55, 1.25, 2.45), coll=C_FX)
    li = eng_light(f"EngineLightBack{s}", (s * 0.55, 1.35, 1.9))
    ENGINES.append((fl, li, "TorsoG", 0.26, 2.4, 1400.0))
sole_n = V((0.0, math.sin(0.55), -math.cos(0.55)))
soleL = V((-0.85, 1.95, 0.32)) + sole_n * 0.25
fl = inst("FlameFootL", FLAME_ME, soleL, (0.55, 0, 0), coll=C_FX)
li = eng_light("EngineLightFootL", soleL + sole_n * 0.4)
ENGINES.append((fl, li, "FootGL", 0.3, 1.5, 700.0))
soleR = V((1.0, -1.95, 0.02))
fl = inst("FlameFootR", FLAME_ME, soleR, coll=C_FX)
li = eng_light("EngineLightFootR", soleR + V((0, 0, -0.4)))
ENGINES.append((fl, li, "FootGR", 0.3, 1.5, 700.0))
for fl, li, g, rr_, ln, pw in ENGINES:
    fl.visible_shadow = False
    fl.scale = (0.001, 0.001, 0.001)

# ------------------------------------------------------------------ rig: parent empties, no armature
log("rig")
RIG, PIV = {}, {}


def make_group(name, pivot, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.3
    C_ROBOT.objects.link(e)
    PIV[name] = V(pivot)
    if parent is not None:
        e.parent = RIG[parent]
        e.location = V(pivot) - PIV[parent]
    else:
        e.location = V(pivot)
    RIG[name] = e
    return e


make_group("RigRoot", (0, 0.3, 5.5))
RIG["RigRoot"].rotation_mode = 'QUATERNION'
make_group("PelvisG", (0, 0.35, 1.5), "RigRoot")
make_group("TorsoG", (0, 0.3, 1.95), "PelvisG")
make_group("HeadG", (0, 0.1, 4.85), "TorsoG")
for s in (-1, 1):
    make_group(f"ShoulderG{s}", (s * 1.75, 0.15, 3.85), "TorsoG")
    make_group(f"ElbowG{s}", (s * 2.3, -0.6, 2.1), f"ShoulderG{s}")
LEGS = {"L": (V((-0.72, 0.45, 1.3)), V((-0.85, -0.6, 0.42)), V((-0.85, 1.35, 0.38))),
        "R": (V((0.75, 0.45, 1.3)), V((0.95, -1.3, 1.95)), V((1.0, -1.45, 0.48)))}
for sd, (Hp, Kp, Ap) in LEGS.items():
    make_group(f"ThighG{sd}", Hp, "PelvisG")
    make_group(f"ShinG{sd}", Kp, f"ThighG{sd}")
    make_group(f"FootG{sd}", Ap, f"ShinG{sd}")

HEAD_P = ("Helmet", "Jaw", "VisorRidge", "Crest", "Antenna", "EyeSlit", "Ear")
UPPER_P = sorted(("ShoulderJ", "Pauldron", "UpperArm", "ArmSleeve"), key=len, reverse=True)
LOWER_P = sorted(("ElbowPlate", "Elbow", "ForearmBand", "Forearm", "Wrist", "Palm", "Finger", "Knuckle", "Tip",
                  "ThumbK", "Thumb"), key=len, reverse=True)
LEG_G = {"ThighL": "ThighGL", "KneeL": "ThighGL", "KneeCapL": "ThighGL",
         "ShinL": "ShinGL", "ShinPlateL": "ShinGL", "AnkleL": "ShinGL", "FootL": "FootGL",
         "ThighR": "ThighGR", "KneeR": "ThighGR", "KneeGuardR": "ShinGR",
         "ShinR": "ShinGR", "ShinPlateR": "ShinGR", "AnkleR": "ShinGR", "FootR": "FootGR"}
PELVIS_N = {"Pelvis", "Codpiece", "Abdomen1", "HipL", "HipR"}


def group_for(n):
    if n in LEG_G:
        return LEG_G[n]
    if n in PELVIS_N or n.startswith("HipSkirt"):
        return "PelvisG"
    if n.startswith(HEAD_P):
        return "HeadG"
    for p in UPPER_P:
        if n.startswith(p):
            return f"ShoulderG{-1 if n[len(p):].startswith('-1') else 1}"
    for p in LOWER_P:
        if n.startswith(p):
            return f"ElbowG{-1 if n[len(p):].startswith('-1') else 1}"
    return "TorsoG"


def attach(ob, g):
    # rest pose of every group is a pure translation to its pivot
    ob.parent = RIG[g]
    ob.matrix_parent_inverse = Matrix.Translation(-PIV[g])


for n in sorted(ROBOT_PARTS):
    attach(bpy.data.objects[n], group_for(n))
attach(glass_ob, "TorsoG")
attach(core, "TorsoG")
for ob, host in ATTACH:
    attach(ob, group_for(host))
for fl, li, g, rr_, ln, pw in ENGINES:
    attach(fl, g)
    attach(li, g)

# ------------------------------------------------------------------ animation helpers


def set_interp(kind):
    try:
        PREFS.edit.keyframe_new_interpolation_type = kind
    except Exception:
        pass


def kf(owner, path, keys, interp='LINEAR'):
    set_interp(interp)
    for f, v in keys:
        setattr(owner, path, v)
        owner.keyframe_insert(path, frame=f)


FR = list(range(1, 241, 2)) + [240]   # every rendered frame (on twos) + the last
FRSET = set(FR)


def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def kf_s(owner, path, fn, frames=FR):
    kf(owner, path, [(f, fn(f)) for f in frames], 'LINEAR')


def rk(g, path, keys):
    ob = RIG[g]
    if path == "location":
        rest = ob.location.copy()
        keys = [(f, rest + V(v)) for f, v in keys]
    kf(ob, path, keys, 'BEZIER')


def wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


log("animation: body")
# pelvis rises slowly, a heavy settle when it reaches full height
rk("PelvisG", "location", [(1, (0, 0, 0)), (40, (0, 0, 0)), (62, (0, -0.1, 0.2)), (92, (0, -0.35, 1.4)),
                           (130, (0, -0.2, 2.4)), (137, (0, -0.2, 2.34)), (148, (0, -0.2, 2.4))])
rk("TorsoG", "rotation_euler", [(1, (0, 0, 0)), (40, (0, 0, 0)), (72, (0.17, 0, 0)), (108, (0.08, 0, 0)),
                                (132, (-0.03, 0, 0)), (165, (-0.1, 0, 0)), (185, (-0.04, 0, 0))])
# head lifts from its bow toward the canopy gap
rk("HeadG", "rotation_euler", [(1, (0, 0, 0)), (40, (0, 0, 0)), (70, (0.06, 0, 0)), (120, (-0.28, 0, 0.06)),
                               (145, (-0.42, 0, 0.12)), (168, (-0.62, 0, 0.16)), (190, (-0.5, 0, 0.12))])
for s in (-1, 1):
    rk(f"ShoulderG{s}", "rotation_euler", [(1, (0, 0, 0)), (40, (0, 0, 0)), (58, (-0.06, 0, 0)),
                                           (95, (0.22, 0, s * 0.06)), (130, (0.4, 0, s * 0.15)),
                                           (168, (0.42, 0, s * 0.15)), (192, (0.85, 0, s * 0.22))])
    rk(f"ElbowG{s}", "rotation_euler", [(1, (0, 0, 0)), (40, (0, 0, 0)), (60, (-0.08, 0, 0)), (100, (0.25, 0, 0)),
                                        (130, (0.15, 0, 0)), (168, (0.15, 0, 0)), (192, (-0.05, 0, 0))])

# legs: 2-bone IK in the YZ plane against the evaluated pelvis, so the feet stay planted
log("animation: leg IK")
LEG_IK = {}
for sd, (Hp, Kp, Ap) in LEGS.items():
    th = (Kp.y - Hp.y, Kp.z - Hp.z)
    sh = (Ap.y - Kp.y, Ap.z - Kp.z)
    base = math.atan2(Ap.z - Hp.z, Ap.y - Hp.y)
    a_th = math.atan2(th[1], th[0])
    LEG_IK[sd] = (a_th, math.atan2(sh[1], sh[0]), math.hypot(*th), math.hypot(*sh),
                  1.0 if wrap(a_th - base) > 0 else -1.0)


def ankle_target(sd, p):
    if sd == "L":
        ps = smooth(p)
        return (lerp(1.35, 1.2, ps), lerp(0.38, 0.77, ps)), -0.55 * ps
    w = clamp01((p - 0.45) / 0.35)
    return (lerp(-1.45, -1.0, smooth(w)), lerp(0.48, 0.62, p) + 0.3 * math.sin(math.pi * w)), 0.0


def solve_leg(sd, hyz, ayz):
    a_th, a_sh, l1, l2, sign = LEG_IK[sd]
    dy, dz = ayz[0] - hyz[0], ayz[1] - hyz[1]
    d = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, math.hypot(dy, dz)))
    base = math.atan2(dz, dy)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    angK = base + sign * a
    ky, kz = hyz[0] + l1 * math.cos(angK), hyz[1] + l1 * math.sin(angK)
    ay, az = hyz[0] + d * math.cos(base), hyz[1] + d * math.sin(base)
    return wrap(angK - a_th), wrap(math.atan2(az - kz, ay - ky) - a_sh)


hips = {"L": {}, "R": {}}
for f in FR:
    scene.frame_set(f)
    for sd in ("L", "R"):
        hips[sd][f] = RIG[f"ThighG{sd}"].matrix_world.translation.copy()

for sd in ("L", "R"):
    pmax = 0.0
    prev = [0.0, 0.0, 0.0]
    th_k, kn_k, ft_k = [], [], []
    for f in FR:
        hp = hips[sd][f]
        pmax = max(pmax, clamp01((hp.z - 1.3) / 2.4))
        ayz, foot_total = ankle_target(sd, pmax)
        t1, tot = solve_leg(sd, (hp.y, hp.z), ayz)
        vals = [t1, tot - t1, foot_total - tot]
        vals = [pv + wrap(v - pv) for v, pv in zip(vals, prev)]
        prev = vals
        th_k.append((f, (vals[0], 0, 0)))
        kn_k.append((f, (vals[1], 0, 0)))
        ft_k.append((f, (vals[2], 0, 0)))
    kf(RIG[f"ThighG{sd}"], "rotation_euler", th_k)
    kf(RIG[f"ShinG{sd}"], "rotation_euler", kn_k)
    kf(RIG[f"FootG{sd}"], "rotation_euler", ft_k)

# launch: the whole robot rides up the sunbeam (fast ease-in), leaning into its flight path
log("animation: launch")
P0 = PIV["RigRoot"].copy()
P1 = P0 + V((0, 0, 4.0))


def shaft(z):
    return T1 + D1 * ((z - T1.z) / D1.z)


P2 = shaft(12.5)
P3 = shaft(34.0)


def bez(t):
    u = 1 - t
    return P0 * (u * u * u) + P1 * (3 * u * u * t) + P2 * (3 * u * t * t) + P3 * (t * t * t)


def dbez(t):
    u = 1 - t
    return (P1 - P0) * (3 * u * u) + (P2 - P1) * (6 * u * t) + (P3 - P2) * (3 * t * t)


def launch_s(f):
    return clamp01((f - 169) / 71.0) ** 2.4


def root_loc(f):
    return bez(launch_s(f))


def root_quat(f):
    s = launch_s(f)
    q = V((0, 0, 1)).rotation_difference(dbez(s).normalized())
    return Quaternion().slerp(q, 0.75 * min(1.0, s * 4.0))


LAUNCH_FR = [f for f in FR if f >= 169]
kf_s(RIG["RigRoot"], "location", root_loc, LAUNCH_FR)
kf_s(RIG["RigRoot"], "rotation_quaternion", root_quat, LAUNCH_FR)

# evaluate the finished body animation for things that ride on it
log("animation: evaluate rig")
GM = {g: {} for g in RIG}
for f in [f for f in FR if f <= 131]:
    scene.frame_set(f)
    for g, ob in RIG.items():
        GM[g][f] = ob.matrix_world.copy()
scene.frame_set(169)
feet_mid = (bpy.data.objects["FlameFootL"].matrix_world.translation +
            bpy.data.objects["FlameFootR"].matrix_world.translation) * 0.5
TRAIL_LOCAL = feet_mid - P0

# ------------------------------------------------------------------ engine ignition
IGN = [(139, 0.0), (141, 0.25), (143, 0.05), (145, 0.5), (147, 0.15), (149, 0.7), (151, 0.35), (153, 0.9), (155, 0.75)]
BURN = [(157, 1.0), (169, 1.05), (179, 1.8), (195, 2.2), (240, 2.3)]


def ENG(f):
    if f < 139:
        return 0.0
    if f < 157:
        v = 0.0
        for kf_, kv in IGN:
            if kf_ <= f:
                v = kv
        return v
    for (fa, va), (fb, vb) in zip(BURN[:-1], BURN[1:]):
        if f <= fb:
            base = lerp(va, vb, (f - fa) / (fb - fa))
            break
    else:
        base = BURN[-1][1]
    return base * (1.0 + 0.07 * math.sin(f * 2.3) + 0.05 * mnoise.noise(V((f * 0.31, 4.2, 0.0))))


for fl, li, g, rr_, ln, pw in ENGINES:
    def fsc(f, rr_=rr_, ln=ln):
        e = ENG(f)
        w = rr_ * (0.55 + 0.45 * min(e, 1.4)) if e > 0 else 0.001
        return (w, w, max(0.001, ln * e))
    kf_s(fl, "scale", fsc)
    kf_s(li.data, "energy", lambda f, pw=pw: pw * ENG(f))
kf_s(FLAME_VAL, "default_value", lambda f: 40.0 * min(ENG(f), 1.6))
kf_s(FLAME_SCROLL, "default_value", lambda f: (0.0, 0.0, -0.18 * f))

# chest core: steady glow, brightening as the engines take
kf_s(EMIT_SOCK, "default_value", lambda f: 12.0 + 5.0 * min(ENG(f), 1.0))
kf_s(core_d, "energy", lambda f: 7.0 * (12.0 + 5.0 * min(ENG(f), 1.0)))

# slow mist drift (as in shot 1)
kf(MIST_LOC, "default_value", [(1, (0.0, 0.0, 0.0)), (240, (1.6, 0.4, 0.0))])

# ------------------------------------------------------------------ wind rings (ignition + launch)
log("fx: wind rings")
ring_z = ground_h(0.0, 0.1) + 0.3
for name, mat, val, t0, dur, kmax, dpeak in (("WindRing1", M_RING1, RING1_VAL, 140, 45, 7.5, 0.55),
                                              ("WindRing2", M_RING2, RING2_VAL, 171, 40, 9.5, 0.8)):
    rob = obj_from_bm(name, bm_torus((0, 0, 0), 1.4, 0.55, (0, 0, 0), 48, 12), mat, C_FX, smooth=True)
    rob.location = (0.0, 0.1, ring_z)

    def rsc(f, t0=t0, dur=dur, kmax=kmax):
        x = clamp01((f - t0) / dur)
        k = 0.5 + (kmax - 0.5) * (1 - (1 - x) ** 2.2)
        return (k, k, 0.55 + 0.06 * k)

    def rden(f, t0=t0, dur=dur, dpeak=dpeak):
        if f < t0:
            return 0.0
        if f < t0 + 6:
            return dpeak * (f - t0) / 6.0
        return dpeak * clamp01(1.0 - (f - t0 - 6) / (dur + 15.0))

    kf_s(rob, "scale", rsc)
    kf_s(val, "default_value", rden)

# ------------------------------------------------------------------ light trail
log("fx: trail")
tr_frames = list(range(169, 241))
tr_pos = [root_loc(f) + root_quat(f) @ TRAIL_LOCAL for f in tr_frames]
cum = [0.0]
for a, b in zip(tr_pos[:-1], tr_pos[1:]):
    cum.append(cum[-1] + (b - a).length)
total = max(cum[-1], 1e-3)
pts = [tr_pos[0]]
for p in tr_pos[1:]:
    if (p - pts[-1]).length > 0.15:
        pts.append(p)
if (tr_pos[-1] - pts[-1]).length > 1e-4:
    pts.append(tr_pos[-1])
CUM_AT = {f: c / total for f, c in zip(tr_frames, cum)}


def trail_curve(name, pts, radii, mat):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    cu.resolution_u = 2
    try:
        cu.bevel_factor_mapping_end = 'SPLINE'
    except Exception:
        pass
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for bp, p, rr_ in zip(sp.points, pts, radii):
        bp.co = (p.x, p.y, p.z, 1.0)
        bp.radius = rr_
    try:
        sp.use_smooth = True
    except Exception:
        pass
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    C_FX.objects.link(ob)
    ob.visible_shadow = False
    return ob, cu


n_pts = len(pts)
frac = [i / max(1, n_pts - 1) for i in range(n_pts)]
_, cu_core = trail_curve("TrailCore", pts, [0.35 - 0.2 * t for t in frac], M_TRAIL)
_, cu_mist = trail_curve("TrailMist", pts, [1.5 - 0.8 * t for t in frac], M_TRAILMIST)
for cu_ in (cu_core, cu_mist):
    kf_s(cu_, "bevel_factor_end", lambda f: CUM_AT.get(f, 0.0) if f >= 169 else 0.0)


def trail_glow(f):
    if f < 171:
        return 0.0
    if f < 177:
        return 24.0 * (f - 171) / 6.0
    return lerp(24.0, 9.0, (f - 177) / 63.0)


def trail_mist(f):
    if f < 171:
        return 0.0
    if f < 181:
        return 0.85 * (f - 171) / 10.0
    return lerp(0.85, 0.4, (f - 181) / 59.0)


kf_s(TRAIL_VAL, "default_value", trail_glow)
kf_s(TRAILMIST_VAL, "default_value", trail_mist)

# ------------------------------------------------------------------ the bird
log("fx: bird")
bbm = bmesh.new()
bmesh.ops.create_uvsphere(bbm, u_segments=16, v_segments=8, radius=0.07, matrix=TRS((0, 0, 0), (0, 0, 0), (0.75, 1.6, 0.8)))
bmesh.ops.create_uvsphere(bbm, u_segments=12, v_segments=6, radius=0.042, matrix=TRS((0, 0.115, 0.04)))
bm_cyl((0, 0.145, 0.04), (0, 0.19, 0.03), 0.013, 0.002, 8, bbm)
bmesh.ops.create_cube(bbm, size=1.0, matrix=TRS((0, -0.15, 0.01), (0.15, 0, 0), (0.07, 0.11, 0.012)))
BIRD_ME = mesh_from_bm("BirdMesh", bbm, M_BIRD, smooth=True)
bird = bpy.data.objects.new("Bird", BIRD_ME)
C_FX.objects.link(bird)
wings = {}
for s in (-1, 1):
    wbm = bmesh.new()
    wp = [(0, 0.05, 0), (0.1, 0.06, 0.005), (0.24, 0.015, 0), (0.2, -0.05, 0), (0.08, -0.07, 0), (0, -0.04, 0)]
    wbm.faces.new([wbm.verts.new((s * x, y, z)) for x, y, z in wp])
    wob = bpy.data.objects.new(f"BirdWing{s}", mesh_from_bm(f"BirdWingMesh{s}", wbm, M_BIRD, smooth=False))
    C_FX.objects.link(wob)
    wob.parent = bird
    wob.location = (s * 0.035, 0.01, 0.025)
    wings[s] = wob

BA = V((-7.0, -8.0, 9.5))
BB = V((10.0, -11.0, 11.5))
BC1 = (BA + PERCH) * 0.5 + V((0, 0, 1.5))
BC2 = PERCH + V((1.5, -1.0, 1.2))
BIRD_FR = [f for f in FR if f <= 89]


def bird_pos(f):
    if f <= 25:
        t = (f - 1) / 24.0
        e = 1 - (1 - t) ** 2
        return BA * ((1 - e) ** 2) + BC1 * (2 * (1 - e) * e) + PERCH * (e * e)
    if f <= 44:
        return PERCH.copy()
    e = clamp01((f - 44) / 36.0) ** 1.6
    return PERCH * ((1 - e) ** 2) + BC2 * (2 * (1 - e) * e) + BB * (e * e)


face_cam = math.atan2(-(2.6 - PERCH.x), (-14.3 - PERCH.y))
yaws = []
prev_y = None
for f in BIRD_FR:
    if 25 < f <= 44:
        y_ = face_cam
    else:
        d = bird_pos(min(f + 1, 89)) - bird_pos(max(f - 1, 1))
        y_ = math.atan2(-d.x, d.y) if d.length > 1e-4 else (prev_y if prev_y is not None else 0.0)
    if prev_y is not None:
        y_ = prev_y + wrap(y_ - prev_y)
    prev_y = y_
    yaws.append((f, (0.0, 0.0, y_)))
kf_s(bird, "location", bird_pos, BIRD_FR)
kf(bird, "rotation_euler", yaws, 'LINEAR')
kf(bird, "scale", [(1, (1.5, 1.5, 1.5)), (85, (1.5, 1.5, 1.5)), (87, (0.001, 0.001, 0.001))], 'CONSTANT')
for s, wob in wings.items():
    def wing_rot(f, s=s):
        if 25 < f <= 44:
            return (0.0, s * 0.25, -s * 1.35)          # folded along the body
        if 19 <= f <= 25:
            return (0.0, -s * 0.15, 0.0)               # spread for landing
        flap = 0.85 if ((f - 1) // 2) % 2 == 0 else -0.6
        return (0.0, -s * flap, 0.0)
    kf_s(wob, "rotation_euler", wing_rot, BIRD_FR)

# ------------------------------------------------------------------ moss, soil and leaves falling off the armour
log("fx: falling debris")
LEAF_GREEN_ME = make_single_leaf_mesh("LeafSingleGreen", M_LEAF)
LEAF_DEAD_ME = make_single_leaf_mesh("LeafSingleDead", M_DEAD)
SOIL_ME = make_blob_mesh("SoilChunkMesh", 900, 2, 0.35, M_SOIL, 0.8)
DR = random.Random(4242)
cands = [h for h in plant_hits if h[1].z > 0.8]
DR.shuffle(cands)
for k, (hit, loc, nor, host) in enumerate(cands[:40]):
    g = group_for(host)
    if k < 16:
        ob = inst(f"DebrisMoss{k}", MOSS_CLUMP, loc, (0, 0, 0), DR.uniform(0.1, 0.2), C_FX)
        rad, heavy = 0.05, True
    elif k < 28:
        ob = inst(f"DebrisSoil{k}", SOIL_ME, loc, (0, 0, 0), DR.uniform(0.05, 0.11), C_FX)
        rad, heavy = 0.04, True
    else:
        ob = inst(f"DebrisLeaf{k}", LEAF_GREEN_ME if k % 2 else LEAF_DEAD_ME, loc, (0, 0, 0), DR.uniform(0.16, 0.24), C_FX)
        rad, heavy = 0.01, False
    lp = (loc + nor * 0.03) - PIV[g]

    def att(f, g=g, lp=lp):
        return GM[g][f] @ lp

    tr = DR.uniform(50, 124)
    fr0 = min(f for f in FR if f >= tr)
    rot0 = V((DR.uniform(-0.3, 0.3), DR.uniform(-0.3, 0.3), DR.uniform(0, 6.28)))
    w = V((DR.uniform(-5, 5), DR.uniform(-5, 5), DR.uniform(-3, 3)))
    locs = [(1, att(1))]
    rots = [(1, tuple(rot0))]
    for f in FR:
        if 39 <= f < fr0:
            locs.append((f, att(f)))
    p = att(fr0)
    v = (att(fr0) - att(fr0 - 2)) * 12.0
    out = V((p.x, p.y - 0.3, 0.0))
    out = out.normalized() if out.length > 1e-4 else V((1, 0, 0))
    v = v + out * DR.uniform(0.5, 1.4) + V((0, 0, DR.uniform(0.0, 0.9)))
    ang = rot0.copy()
    landed = False
    f = fr0
    while f <= 240:
        if f in FRSET:
            locs.append((f, p.copy()))
            rots.append((f, tuple(ang)))
            if landed:
                break
        dt = 1.0 / 24.0
        if heavy:
            a = V((0, 0, -9.81)) - v * 0.3
        else:
            a = V((0, 0, -9.81)) - v * 6.0 + V((math.sin(f * 0.5 + k), math.cos(f * 0.43 + k), 0)) * 3.0
        if not landed:
            v = v + a * dt
            p = p + v * dt
            ang = ang + w * dt * (1.0 if heavy else 0.6)
            gz = ground_h(p.x, p.y) + rad
            if p.z < gz:
                p.z = gz
                if heavy and v.z < -1.5:
                    v = V((v.x * 0.5, v.y * 0.5, -v.z * 0.25))
                    w = w * 0.5
                else:
                    landed = True
        f += 1
    kf(ob, "location", locs, 'LINEAR')
    kf(ob, "rotation_euler", rots, 'LINEAR')

# ------------------------------------------------------------------ ground leaves blown outward by the engine rings
log("fx: ground leaves")
GL = random.Random(5151)
placed = 0
tries = 0
while placed < 70 and tries < 2000:
    tries += 1
    a = GL.uniform(0, 2 * math.pi)
    r = GL.uniform(2.2, 9.0)
    x, y = math.cos(a) * r * 1.1, math.sin(a) * r - 0.4
    if y > 4.0 or near_trunk(x, y, 0.3) or cam_dist2d(x, y) < 1.0:
        continue
    i = placed
    placed += 1
    z0 = ground_h(x, y) + 0.015
    rot0 = V((GL.uniform(-0.2, 0.2), GL.uniform(-0.2, 0.2), GL.uniform(0, 6.28)))
    ob = inst(f"GroundLeaf{i}", LEAF_DEAD_ME if i % 3 else LEAF_GREEN_ME, (x, y, z0), tuple(rot0), GL.uniform(0.16, 0.26), C_FX)
    rr_ = math.hypot(x, y + 0.3)
    tw = (140 + (rr_ - 1.0) * 4.5) if i % 2 == 0 else (171 + (rr_ - 1.0) * 3.5)
    out = V((x, y + 0.3, 0)).normalized()
    perp = V((-out.y, out.x, 0))
    vr = GL.uniform(4, 8) * max(0.3, 1 - rr_ / 12) * (1.3 if i % 2 else 1.0)
    vz = GL.uniform(2.5, 5.5) * max(0.35, 1 - rr_ / 12)
    vt = GL.uniform(0.7, 1.2)
    tau = 0.5
    ph = GL.uniform(0, 6.28)
    wv = V((GL.uniform(-9, 9), GL.uniform(-9, 9), GL.uniform(-6, 6)))
    locs = [(1, V((x, y, z0)))]
    rots = [(1, tuple(rot0))]
    for f in FR:
        if f < tw - 2:
            continue
        t = max(0.0, (f - tw) / 24.0)
        e = 1 - math.exp(-t / tau)
        dist = vr * tau * e
        z = z0 + (vz + vt) * tau * e - vt * t
        wob = 0.25 * math.sin(t * 5 + ph) * (1 - math.exp(-t))
        pxy = V((x, y, 0)) + out * dist + perp * wob
        gz = ground_h(pxy.x, pxy.y) + 0.015
        done = t > 0.2 and z <= gz
        z = max(z, gz)
        ang = rot0 + wv * (0.8 * (1 - math.exp(-t / 0.8)))
        locs.append((f, V((pxy.x, pxy.y, z))))
        rots.append((f, tuple(ang)))
        if done:
            break
    kf(ob, "location", locs, 'LINEAR')
    kf(ob, "rotation_euler", rots, 'LINEAR')

# ------------------------------------------------------------------ leaves spiralling down through the sunbeam
log("fx: spiral leaves")
SL = random.Random(6262)
for i in range(54):
    ambient = i < 24
    if i % 6 == 0:
        c = V((SL.uniform(-2.0, 5.0), SL.uniform(-9.0, -4.0), 0.0))
    else:
        zc = SL.uniform(5.0, 15.0)
        c = shaft(zc) + V((SL.uniform(-3.5, 3.5), SL.uniform(-3.5, 3.5), 0.0))
        c.z = 0.0
    R = SL.uniform(0.25, 0.8)
    w = SL.uniform(2.5, 4.5) * SL.choice((-1, 1))
    vt = SL.uniform(0.9, 1.5)
    ph = SL.uniform(0, 6.28)

    def fall(t, vt=vt):
        return vt * (t - 0.4 * (1 - math.exp(-t / 0.4)))

    if ambient:
        ts = -SL.uniform(0.0, 120.0)
        z0 = SL.uniform(4.0, 14.0) + fall((1 - ts) / 24.0)
    else:
        ts = SL.uniform(168.0, 210.0)
        z0 = SL.uniform(12.0, 17.0)
    ob = inst(f"SpiralLeaf{i}", LEAF_GREEN_ME if i % 2 else LEAF_DEAD_ME, (c.x, c.y, z0), (0, 0, ph),
              SL.uniform(0.22, 0.32), C_FX)
    locs, rots = [], []
    for f in FR:
        if f > 1 and f < ts - 2:
            continue
        t = max(0.0, (f - ts) / 24.0)
        px = c.x + R * math.cos(ph + w * t)
        py = c.y + R * math.sin(ph + w * t)
        z = z0 - fall(t)
        gz = ground_h(px, py) + 0.015
        done = z <= gz
        z = max(z, gz)
        locs.append((f, V((px, py, z))))
        rots.append((f, (0.7 * math.sin(w * t + ph), 0.5 * math.cos(w * t * 1.3), ph + w * t)))
        if done:
            break
    kf(ob, "location", locs, 'LINEAR')
    kf(ob, "rotation_euler", rots, 'LINEAR')

# ------------------------------------------------------------------ camera: low, tiny tremble, tilts to follow the launch
log("animation: camera")
CS = V((2.8, -15.0, ground_h(2.8, -15.0) + 1.0))
CE = V((2.5, -14.2, ground_h(2.5, -14.2) + 0.9))
TA = V((0.1, -0.3, 3.6))
TB = V((0.1, -0.2, 5.4))
TC = V((0.4, 0.1, 6.6))


def shake_amp(f):
    if f < 40:
        return 0.0
    if f < 52:
        return 0.02 * (f - 40) / 12.0
    if f < 130:
        return 0.02
    if f < 139:
        return 0.012
    if f < 170:
        return 0.035
    return 0.06 * math.exp(-(f - 170) / 35.0) + 0.012


def shake(f, seed):
    return V((mnoise.noise(V((f * 0.47, seed, 0.0))), mnoise.noise(V((seed, f * 0.47, 3.1))),
              mnoise.noise(V((7.7, seed, f * 0.47)))))


def tgt_base(f):
    if f <= 40:
        return TA.copy()
    if f <= 130:
        return TA.lerp(TB, smooth((f - 40) / 90.0))
    if f <= 169:
        return TB.lerp(TC, smooth((f - 130) / 39.0))
    s = launch_s(f)
    st = 0.42 * (1 - math.exp(-s / 0.42))
    return TC + (bez(st) - P0)


kf_s(cam, "location", lambda f: CS.lerp(CE, smooth((f - 1) / 239.0)) + shake(f, 1.3) * shake_amp(f))
kf_s(target, "location", lambda f: tgt_base(f) + shake(f, 8.1) * (shake_amp(f) * 4.0))
set_interp('BEZIER')
scene.frame_set(1)

exec(open('/Users/dtribe/Desktop/PROJECTS/MattPaint/fast/blender/look_inject.py').read())

# ------------------------------------------------------------------ render settings
log("render settings")
scene.render.engine = 'CYCLES'
try:
    cp = PREFS.addons['cycles'].preferences
    cp.compute_device_type = 'METAL'
    try:
        cp.refresh_devices()
    except Exception:
        pass
    cp.get_devices()
    found = False
    for d in cp.devices:
        d.use = (d.type == 'METAL')
        found = found or d.use
    scene.cycles.device = 'GPU' if found else 'CPU'
    log(f"devices: {[(d.name, d.type, d.use) for d in cp.devices]} -> {scene.cycles.device}")
except Exception as e:
    log(f"GPU setup failed ({e}), using CPU")
    scene.cycles.device = 'CPU'


def cset(attr, val):
    try:
        setattr(scene.cycles, attr, val)
    except Exception:
        pass


cset("samples", 64)
cset("use_adaptive_sampling", True)
cset("seed", 7)
cset("use_animated_seed", False)
cset("use_denoising", True)
cset("denoiser", 'OPENIMAGEDENOISE')
cset("denoising_use_gpu", True)
cset("max_bounces", 6)
cset("diffuse_bounces", 4)
cset("glossy_bounces", 4)
cset("transmission_bounces", 6)
cset("volume_bounces", 1)
cset("transparent_max_bounces", 8)
cset("caustics_reflective", False)
cset("caustics_refractive", False)
cset("blur_glossy", 1.0)
cset("sample_clamp_indirect", 8.0)
cset("volume_step_rate", 4.0)
cset("volume_max_steps", 512)

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 240
scene.frame_step = 2
scene.render.film_transparent = False
try:
    scene.render.use_persistent_data = True
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_depth = '8'
scene.render.use_file_extension = True
scene.render.use_overwrite = True

try:
    scene.view_settings.view_transform = 'AgX'
except Exception:
    pass
for look in ('AgX - Medium High Contrast', 'Medium High Contrast'):
    try:
        scene.view_settings.look = look
        break
    except Exception:
        continue
scene.view_settings.exposure = 0.3

# ------------------------------------------------------------------ timing handlers
_T = {"t": time.time()}


def _pre(scn, *a):
    _T["t"] = time.time()


def _post(scn, *a):
    print(f"FRAME {scn.frame_current} {time.time() - _T['t']:.1f}", flush=True)


bpy.app.handlers.render_pre.append(_pre)
bpy.app.handlers.render_post.append(_post)

log(f"scene built: {len(bpy.data.objects)} objects")

# ------------------------------------------------------------------ render
if FRAME is not None:
    scene.frame_set(FRAME)
    scene.render.filepath = os.path.join(OUTDIR, f"frame_{FRAME:04d}")
    bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = os.path.join(OUTDIR, "frame_####")
    bpy.ops.render.render(animation=True)

log("done")
