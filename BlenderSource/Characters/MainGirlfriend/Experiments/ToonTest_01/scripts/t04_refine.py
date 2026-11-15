"""ToonTest_01 step 4 (Blender, background): one refinement pass on the toon test, saved as a new file.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01.blend> --python t04_refine.py
Writes MG_ToonTest_01_v2.blend next to it (the v1 file is left as it is):
- blush: radial alpha fade (planar UV) instead of a flat rectangle
- nose: shrunk to a small soft dot (r30 nose is ~10 x 17 px)
- mouth: the open-smile parts hidden, a small closed mouth line added (r30 Mouth_Closed 43 x 6 px)
- hair: r30 base / highlight colours, fake strand shading (stretched wave texture, URP-reproducible as a strand map)
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
PPM = SPEC["head_height_px"] / FIT["head_h"]


def srgb(c):
    c = [v / 255.0 for v in c]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


def planar_uv(o):
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    co = [o.matrix_world @ v.co for v in me.vertices]
    x0, x1 = min(c.x for c in co), max(c.x for c in co); z0, z1 = min(c.z for c in co), max(c.z for c in co)
    for poly in me.polygons:
        for li in poly.loop_indices:
            c = co[me.loops[li].vertex_index]
            uv[li].uv = ((c.x - x0) / max(x1 - x0, 1e-6), (c.z - z0) / max(z1 - z0, 1e-6))


# ---- blush: radial fade
bm = bpy.data.materials.new("TT_Blush_Radial"); bm.use_nodes = True
nt = bm.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); uvn = nt.nodes.new("ShaderNodeUVMap")
sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0)
scl = nt.nodes.new("ShaderNodeVectorMath"); scl.operation = "MULTIPLY"; scl.inputs[1].default_value = (1.0, 1.6, 0)
ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
e[0].position, e[0].color = 0.0, (0.42, 0.42, 0.42, 1); e[1].position, e[1].color = 0.5, (0, 0, 0, 1)
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = srgb((248, 160, 150))
tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(uvn.outputs[0], sub.inputs[0]); nt.links.new(sub.outputs[0], scl.inputs[0]); nt.links.new(scl.outputs[0], ln.inputs[0])
nt.links.new(ln.outputs["Value"], ramp.inputs[0]); nt.links.new(ramp.outputs["Color"], mix.inputs[0])
nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
if hasattr(bm, "surface_render_method"):
    bm.surface_render_method = "BLENDED"
for n in ("Face_Blush.L", "Face_Blush.R"):
    o = bpy.data.objects[n]; planar_uv(o); o.data.materials.clear(); o.data.materials.append(bm)

# ---- nose: small soft dot
nose = bpy.data.objects["Face_Nose"]
c = nose.matrix_world.translation.copy()
nose.scale = (nose.scale[0] * 0.45, nose.scale[1], nose.scale[2] * 0.45)
nm = bpy.data.materials.new("TT_Nose_Dot"); nm.use_nodes = True
nt = nm.node_tree; nt.nodes.clear(); out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = srgb((240, 186, 168)); nt.links.new(em.outputs[0], out.inputs[0])
nose.data.materials.clear(); nose.data.materials.append(nm)

# ---- mouth: hide the open smile, add a small closed line
for o in bpy.data.objects:
    if o.name.startswith("Face_Mouth_Smile"):
        o.hide_render = True
root = bpy.data.objects["Face_Mouth_Root"]
p = root.matrix_world.translation
head = bpy.data.objects["Blockout_Head"]
w = (SPEC["mouth_closed"][2] - SPEC["mouth_closed"][0]) / PPM
th = max(2.2 / PPM, 0.0011)
me = bpy.data.meshes.new("TT_Mouth_Closed"); b = bmesh.new()
N = 12
rows = []
for j, off in enumerate((-th / 2, th / 2)):
    rows.append([b.verts.new((-w / 2 + w * i / N, -0.5, p.z + off - 0.0012 * (1 - (2 * i / N - 1) ** 2))) for i in range(N + 1)])
for i in range(N):
    b.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
b.to_mesh(me); b.free()
mouth = bpy.data.objects.new("TT_Mouth_Closed", me)
for coll in root.users_collection:
    coll.objects.link(mouth)
sw = mouth.modifiers.new("SW", "SHRINKWRAP"); sw.target = head; sw.wrap_method = "PROJECT"; sw.use_project_y = True
sw.use_negative_direction = True; sw.use_positive_direction = True; sw.offset = 0.0008
mm = bpy.data.materials.new("TT_Mouth_Line"); mm.use_nodes = True
nt = mm.node_tree; nt.nodes.clear(); out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = srgb((176, 84, 76)); nt.links.new(em.outputs[0], out.inputs[0])
me.materials.append(mm)

# ---- hair: r30 colours + strand modulation
hm = bpy.data.materials["TT_Hair"]; nt = hm.node_tree
ramp = next(n for n in nt.nodes if n.type == "VALTORGB" and len(n.color_ramp.elements) >= 5)
cols = [(70, 34, 30), (70, 34, 30), (110, 58, 50), SPEC["hair"]["base"], (166, 98, 84), (166, 98, 84)]
for el, cc in zip(ramp.color_ramp.elements, cols):
    el.color = srgb(cc)
mix_hl = next(n for n in nt.nodes if n.type == "MIX")
mix_hl.inputs["B"].default_value = srgb((226, 168, 156))
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (70.0, 70.0, 6.0)
wave = nt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
wave.inputs["Distortion"].default_value = 6.0; wave.inputs["Detail"].default_value = 2.0
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 0.22
nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], wave.inputs["Vector"])
em = next(n for n in nt.nodes if n.type == "EMISSION")
src = em.inputs["Color"].links[0].from_socket
nt.links.new(src, mx.inputs["A"]); nt.links.new(wave.outputs["Color"], mx.inputs["B"])
inv = nt.nodes.new("ShaderNodeInvert"); inv.inputs[0].default_value = 0.35
nt.links.new(wave.outputs["Color"], inv.inputs["Color"]); nt.links.new(inv.outputs[0], mx.inputs["B"])
nt.links.new(mx.outputs["Result"], em.inputs["Color"])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v2.blend"), copy=False)
print("REFINE_OK")
