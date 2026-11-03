# look_inject — runs inside a robot scene script right before it renders (exec'd, shares its globals).
# Matt 2026-11-02: "visually boring, the colors are somewhat dull". Measured: brightness 10-30/100, color 12-25/100.
#   MP_LOOK=bright   brighter, warmer, punchier: exposure up, half the mist, stronger sun and sky, AgX Punchy
#   MP_STAGE=clay    the explainer's "how it's built" step 1: every surface plain clay, no mist, even daylight
#   MP_STAGE=paint   step 2: real materials (rust, moss, bark), no mist, even daylight
#   (no MP_STAGE)    the full lit scene
import os as _os
_look = _os.environ.get("MP_LOOK", "")
_stage = _os.environ.get("MP_STAGE", "")


def _scale_light_energy(obj_name_part, k):
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT' and obj_name_part.lower() in ob.name.lower():
            ob.data.energy *= k
            ad = ob.data.animation_data
            if ad and ad.action:
                for fc in getattr(ad.action, "fcurves", []):
                    if fc.data_path == "energy":
                        for kp in fc.keyframe_points:
                            kp.co[1] *= k; kp.handle_left[1] *= k; kp.handle_right[1] *= k


def _scale_world(k):
    w = scene.world
    if not (w and w.node_tree):
        return
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Strength'].default_value *= k
    ad = w.node_tree.animation_data
    if ad and ad.action:
        for fc in getattr(ad.action, "fcurves", []):
            if "Strength" in fc.data_path or "inputs[1]" in fc.data_path:
                for kp in fc.keyframe_points:
                    kp.co[1] *= k; kp.handle_left[1] *= k; kp.handle_right[1] *= k


def _thin_mist(k):
    for m in bpy.data.materials:
        if not (m.node_tree and "mist" in m.name.lower()):
            continue
        nt = m.node_tree
        for n in nt.nodes:
            if n.type == 'VOLUME_SCATTER':
                d = n.inputs['Density']
                if d.is_linked:
                    src = d.links[0].from_socket
                    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
                    mul.inputs[1].default_value = k
                    nt.links.new(src, mul.inputs[0]); nt.links.new(mul.outputs[0], d)
                else:
                    d.default_value *= k


def _saturate_materials(k):
    """richer rust, moss, bark and leaves: a Hue/Saturation node in front of every Base Color input"""
    for m in bpy.data.materials:
        if not m.node_tree or "mist" in m.name.lower():
            continue
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type != 'BSDF_PRINCIPLED':
                continue
            bc = n.inputs['Base Color']
            hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = k
            hs.inputs['Value'].default_value = 1.12
            if bc.is_linked:
                nt.links.new(bc.links[0].from_socket, hs.inputs['Color'])
            else:
                hs.inputs['Color'].default_value = bc.default_value[:]
            nt.links.new(hs.outputs['Color'], bc)


def _key_light():
    """a big warm soft light from behind the camera, like a film crew's key light: the canopy
    blocks most of the sun, so brightening the sun alone barely reached the robot"""
    cam = scene.camera
    if cam is None:
        return
    import mathutils
    cam_loc = cam.matrix_world.translation.copy()
    fwd = (cam.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))).normalized()
    kd = bpy.data.lights.new("KeyLight", 'AREA'); kd.shape = 'DISK'; kd.size = 14.0
    kd.energy = 9000.0; kd.color = (1.0, 0.86, 0.66)
    ko = bpy.data.objects.new("KeyLight", kd); scene.collection.objects.link(ko)
    ko.location = cam_loc - fwd * 4.0 + mathutils.Vector((3.0, 0, 5.0))
    target = cam_loc + fwd * 14.0
    ko.rotation_euler = (target - ko.location).to_track_quat('-Z', 'Y').to_euler()
    ko.visible_camera = False
    # follow the camera if it moves
    c = ko.constraints.new('CHILD_OF'); c.target = cam
    try:
        c.inverse_matrix = cam.matrix_world.inverted()
    except Exception:
        pass


def _set_look(names):
    for nm in names:
        try:
            scene.view_settings.look = nm
            return nm
        except Exception:
            pass


if _look == "bright" or _stage:
    scene.view_settings.exposure = 1.7
    _set_look(('AgX - Punchy', 'Punchy', 'AgX - High Contrast', 'High Contrast'))
    _thin_mist(0.35)
    _scale_light_energy("sun", 2.0)
    _scale_world(1.8)
    _saturate_materials(1.45)
    _key_light()

if _stage in ("clay", "paint"):
    for ob in bpy.data.objects:                      # no mist in the build-up steps
        if "mist" in ob.name.lower() or (ob.type == 'MESH' and ob.active_material and "mist" in ob.active_material.name.lower()):
            ob.hide_render = True
    scene.view_settings.exposure = 0.9
    _set_look(('AgX - Base Contrast', 'None', 'AgX - Medium Contrast'))

if _stage == "clay":
    clay = bpy.data.materials.new("Clay")
    try:
        clay.use_nodes = True
    except Exception:
        pass
    bsdf = next((n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.62, 0.6, 0.57, 1)
        bsdf.inputs['Roughness'].default_value = 0.75
    for vl in scene.view_layers:
        vl.material_override = clay
    log("look_inject: clay override")

log(f"look_inject: look={_look or '-'} stage={_stage or 'full'}")
