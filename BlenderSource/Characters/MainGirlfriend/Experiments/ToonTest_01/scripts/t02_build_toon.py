"""ToonTest_01 step 2 (Blender, background): build the toon test scene in a COPY of MainGirlfriend_Face_v2.blend.

usage:
  Blender -b --factory-startup <Experiments/ToonTest_01/MG_ToonTest_01.blend> --python t02_build_toon.py
The .blend given must be the experiment copy (the script refuses to run on files under Models/).
Steps: hair (Models/create_character_hair.py, run as is), proportion fit to r30 (4.12 heads: head group scaled about
the chin, body stretched in Z), r30 face ratios for eyes / nose / mouth, toon materials (Shader to RGB + ramps),
inverted-hull outlines (Solidify, flipped normals, back-face culled brown material), sun light, orthographic cameras.
Saves the copy. All colours come from ../spec/r30_face_spec.json.
"""
import json
import math
import os
import runpy
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
MODELS = os.path.abspath(os.path.join(EXP, "..", "..", "Models"))
assert os.path.abspath(bpy.data.filepath).startswith(EXP), "run on the experiment copy only"
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
HEADS = SPEC["heads_tall"]


def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


def world_bbox(objs):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type not in ("MESH", "CURVE"):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


# ------------------------------------------------------------------ 1. hair
runpy.run_path(os.path.join(MODELS, "create_character_hair.py"), run_name="__main__")

col = lambda n: bpy.data.collections.get(n)
HEAD_COLLS = ("MainGirlfriend_Eyes", "MainGirlfriend_FaceDetails", "MainGirlfriend_Hair")
head_objs = [bpy.data.objects["Blockout_Head"]] + [o for n in HEAD_COLLS if col(n) for o in col(n).all_objects]
body_objs = [o for o in col("MainGirlfriend_Blockout").all_objects if o.name != "Blockout_Head"]

# ------------------------------------------------------------------ 2. proportions (approximate, blockout level)
head = bpy.data.objects["Blockout_Head"]
hv = [head.matrix_world @ v.co for v in head.data.vertices]
chin = min((p for p in hv if p.y < -0.05), key=lambda p: p.z)
lo, hi = world_bbox([o for o in head_objs if o.type in ("MESH", "CURVE")])
top = hi.z
total = top                                           # soles at 0
head_h = top - chin.z
s = total / (HEADS * head_h)                          # head scale
k = (total - s * head_h) / chin.z                     # body stretch so that the height stays the same
print("PROPORTION before: heads %.2f, head_h %.3f, chin %.3f -> s %.3f, k %.3f" % (total / head_h, head_h, chin.z, s, k))
pivot = Vector((0, chin.y, chin.z)); new_pivot = Vector((0, chin.y, chin.z * k))
M_head = Matrix.Translation(new_pivot) @ Matrix.Scale(s, 4) @ Matrix.Translation(-pivot)
M_body = Matrix.Diagonal((1, 1, k, 1))
for o in head_objs:
    if o.parent is None:
        o.matrix_world = M_head @ o.matrix_world
for o in body_objs:
    if o.parent is None:
        o.matrix_world = M_body @ o.matrix_world
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. face ratios toward r30 (eyes / nose / mouth)
lo, hi = world_bbox([o for o in head_objs if o.type in ("MESH", "CURVE")])
hb = [M_head @ p for p in hv]
chin_z = new_pivot.z; head_h = hi.z - chin_z
eye_roots = [bpy.data.objects[n] for n in ("Eye_Root.L", "Eye_Root.R")]
face_w_rows = [p for p in hb if abs(p.z - (chin_z + head_h * (SPEC["eye_centre_from_chin_over_head"] - 0.08))) < 0.01 and p.y < 0]
face_w = (max(p.x for p in face_w_rows) - min(p.x for p in face_w_rows)) if face_w_rows else 0.3
target_eye_z = chin_z + head_h * SPEC["eye_centre_from_chin_over_head"]
eyes_now = world_bbox([o for o in col("MainGirlfriend_Eyes").all_objects if o.name.startswith("Eye_White")])
eye_w_now = (eyes_now[1].x - eyes_now[0].x - (2 * min(abs(r.matrix_world.translation.x) for r in eye_roots) - 0)) / 2
ew = [world_bbox([bpy.data.objects[f"Eye_White.{s_}"]]) for s_ in "LR"]
eye_w_now = sum(b[1].x - b[0].x for b in ew) / 2
target_eye_w = SPEC["eye_width_over_face_width"] * face_w
es = target_eye_w / eye_w_now
gap = SPEC["eye_gap_over_eye_width"] * target_eye_w
print("EYES face_w %.3f eye_w %.3f -> %.3f (x%.2f), eye z -> %.3f" % (face_w, eye_w_now, target_eye_w, es, target_eye_z))
for r in eye_roots:
    sign = 1 if r.location.x > 0 else -1
    t = r.matrix_world.translation.copy()
    new_t = Vector((sign * (gap / 2 + target_eye_w / 2), t.y, target_eye_z))
    r.matrix_world = Matrix.Translation(new_t) @ Matrix.Scale(es, 4) @ Matrix.Translation(-t) @ r.matrix_world
for n, ratio in (("Face_Nose", SPEC["nose_from_chin_over_head"]), ("Face_Mouth_Root", SPEC["mouth_from_chin_over_head"])):
    o = bpy.data.objects.get(n)
    if o:
        t = o.matrix_world.translation.copy()
        o.matrix_world = Matrix.Translation((0, 0, chin_z + head_h * ratio - t.z)) @ o.matrix_world
for n in ("Face_Brow_Root.L", "Face_Brow_Root.R"):
    o = bpy.data.objects.get(n)
    if o:
        t = o.matrix_world.translation.copy()
        sign = 1 if t.x > 0 else -1
        bz = chin_z + head_h * ((SPEC["chin_y"] - (SPEC["brow"]["R"][1] + SPEC["brow"]["R"][3]) / 2) / SPEC["head_height_px"])
        o.matrix_world = Matrix.Translation((sign * (gap / 2 + target_eye_w / 2) - t.x, 0, bz - t.z)) @ o.matrix_world
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 4. toon materials
def toon_mat(name, stops, spec=None, emission=None, alpha=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emission is not None:
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = srgb(emission)
        if alpha is None:
            nt.links.new(em.outputs[0], out.inputs[0])
        else:
            tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
            mix.inputs[0].default_value = alpha
            nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
            if hasattr(m, "surface_render_method"):
                m.surface_render_method = "BLENDED"
        return m
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse"); diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "LINEAR"
    els = ramp.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position, els[0].color = stops[0][0], srgb(stops[0][1])
    for p, c in stops[1:]:
        e = els.new(p); e.color = srgb(c)
    nt.links.new(diff.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs["Color"], bw.inputs[0]); nt.links.new(bw.outputs[0], ramp.inputs[0])
    colour = ramp.outputs["Color"]
    if spec:   # hair highlight: band on world-up facing normals, toward the camera
        geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        band = nt.nodes.new("ShaderNodeValToRGB"); be = band.color_ramp.elements
        be[0].position, be[0].color = spec["lo"], (0, 0, 0, 1); be[1].position, be[1].color = spec["lo"] + 0.04, (1, 1, 1, 1)
        e = be.new(spec["hi"] - 0.04); e.color = (1, 1, 1, 1); e = be.new(spec["hi"]); e.color = (0, 0, 0, 1)
        lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.35
        fac = nt.nodes.new("ShaderNodeMath"); fac.operation = "MULTIPLY"
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
        nt.links.new(geo.outputs["Normal"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], band.inputs[0])
        nt.links.new(lw.outputs["Facing"], inv.inputs[1])
        nt.links.new(band.outputs["Color"], fac.inputs[0]); nt.links.new(inv.outputs[0], fac.inputs[1])
        nt.links.new(fac.outputs[0], mix.inputs["Factor"]); nt.links.new(colour, mix.inputs["A"])
        mix.inputs["B"].default_value = srgb(spec["colour"])
        colour = mix.outputs["Result"]
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(colour, em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
    return m


S = SPEC["skin"]; HC = SPEC["hair"]
SKIN_SHADOW = (238, 172, 150)                 # r30 face shade under the bangs (Hair_Shadow_Face) / body shadow mix
skin = toon_mat("TT_Skin", [(0.0, SKIN_SHADOW), (0.30, SKIN_SHADOW), (0.38, S["shadow"]), (0.62, S["base"]), (0.70, S["light"]), (1.0, S["light"])])
hair = toon_mat("TT_Hair", [(0.0, (70, 36, 32)), (0.30, (70, 36, 32)), (0.40, (104, 55, 48)), (0.60, HC["base"]), (0.68, (150, 88, 76)), (1.0, (150, 88, 76))],
                spec=dict(lo=0.55, hi=0.80, colour=(214, 150, 138)))
clip = toon_mat("TT_Clip", [(0.0, (205, 196, 200)), (0.45, (205, 196, 200)), (0.55, SPEC["hairclip_colour"]["base"]), (1.0, SPEC["hairclip_colour"]["base"])])
flat = dict(
    MG_Eye_White=(250, 246, 246), MG_Eye_Pupil=(28, 10, 12), MG_Eye_Highlight=(255, 255, 255), MG_Eye_Lash=(45, 20, 18),
    MG_Eye_UpperLid=(45, 20, 18), MG_Eye_LowerLid=(120, 60, 52), MG_Eye_OuterLine=(45, 20, 18), MG_Eye_Crease=(150, 85, 72),
    MG_Face_Brow=(120, 66, 56), MG_Face_Lash=(45, 20, 18), MG_Face_LowerLash=(90, 45, 40), MG_Face_LipLine=(190, 95, 85),
    MG_Face_MouthInside=(150, 60, 60), MG_Face_Nose=(232, 170, 150), MG_Face_Teeth=(250, 248, 245), MG_Face_Tongue=(220, 120, 115))
for n, c in flat.items():
    toon_mat("TT_" + n, None, emission=c)
blush = toon_mat("TT_MG_Face_Blush", None, emission=(250, 170, 160), alpha=0.35)

# iris: r30 iris texture, planar UV along the gaze
iris_img = bpy.data.images.load(os.path.join(EXP, "r30", "tex_iris_R.png"), check_existing=True)
im = bpy.data.materials.new("TT_Eye_Iris"); im.use_nodes = True
nt = im.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = iris_img
em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])

def planar_uv(o, mirror=False):
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    co = [o.matrix_world @ v.co for v in me.vertices]
    x0, x1 = min(c.x for c in co), max(c.x for c in co); z0, z1 = min(c.z for c in co), max(c.z for c in co)
    for poly in me.polygons:
        for li in poly.loop_indices:
            c = co[me.loops[li].vertex_index]
            u = (c.x - x0) / (x1 - x0)
            uv[li].uv = ((1 - u) if mirror else u, (c.z - z0) / (z1 - z0))

def assign(o, mat):
    o.data.materials.clear(); o.data.materials.append(mat)

for o in list(bpy.data.objects):
    if o.type not in ("MESH", "CURVE"):
        continue
    n = o.name
    if n.startswith("Eye_Iris"):
        planar_uv(o, mirror=n.endswith(".L")); assign(o, im)
    elif n.startswith("Eye_Pupil") or n.startswith("Eye_Highlight"):
        o.hide_render = True                                     # baked into the r30 iris texture
    elif n.startswith(("Blockout_", "Face_Ear")):
        assign(o, skin)
    elif "Hair" in n and "Clip" not in n:
        assign(o, hair)
    elif "Clip" in n:
        assign(o, clip)
    elif o.material_slots and o.material_slots[0].material:
        src = o.material_slots[0].material.name
        tm = bpy.data.materials.get("TT_" + src)
        if tm:
            assign(o, tm)

# ------------------------------------------------------------------ 5. outlines (inverted hull)
def outline_mat(name, c):
    m = toon_mat(name, None, emission=c)
    m.use_backface_culling = True
    return m
line_skin = outline_mat("TT_Line_Skin", (150, 88, 70))           # r30 face line (203,153,136) reads darker at 1 px
line_hair = outline_mat("TT_Line_Hair", (66, 30, 26))            # r30 hair line
for o in bpy.data.objects:
    if o.type != "MESH" or o.hide_render:
        continue
    is_hair = "Hair" in o.name and "Clip" not in o.name
    if not (o.name.startswith(("Blockout_", "Face_Ear")) or is_hair or "Clip" in o.name):
        continue
    mat = line_hair if is_hair or "Clip" in o.name else line_skin
    o.data.materials.append(mat)
    sol = o.modifiers.new("TT_Outline", "SOLIDIFY")
    sol.thickness = 0.0016 if is_hair else 0.0011
    sol.offset = 1.0; sol.use_flip_normals = True; sol.use_rim = False
    sol.material_offset = len(o.data.materials) - 1
    sol.use_even_offset = True

# ------------------------------------------------------------------ 6. light, world, cameras
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o)
sun = bpy.data.lights.new("TT_Sun", "SUN"); sun.energy = 3.0
so = bpy.data.objects.new("TT_Sun", sun); bpy.context.scene.collection.objects.link(so)
so.rotation_euler = (math.radians(60), 0, math.radians(-20))       # from the front, above, slightly from screen left
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
lo, hi = world_bbox([o for o in head_objs if o.type in ("MESH", "CURVE")])
info = dict(chin_z=chin_z, top_z=hi.z, head_h=hi.z - chin_z, total=hi.z, s=s, k=k)
json.dump(info, open(os.path.join(EXP, "spec", "blender_fit.json"), "w"), indent=1)
bpy.ops.wm.save_mainfile()
print("BUILD_OK", info)
