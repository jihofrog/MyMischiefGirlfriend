"""ToonTest_01 step 30 (Blender, background, the .blend is not saved): why the B upper lid looks smudged.

usage: Blender -b <MG_ToonTest_01_v6b_eye.blend | v6c> --python t30_eye_lid_diag.py -- <tag>
Renders the left upper lid close up (front x4, 3/4 x3, same camera / sun as t03) once per switch, one element changed at
a time: renders/<tag>_lid_<case>_{front,34}.png
  full          as built
  no_lash       Eye_Lash hidden
  no_skirt      lash band without its edge fold down to the eyeball
  no_lids       Eye_Lids hidden
  no_outline    every TT_Outline hull off
  lash_flat     lash band one flat dark colour (alpha cut kept): the painted colours vs the shape
  lash_blend    lash alpha blended instead of cut at 0.5
  ball_flat     eyeball picture replaced by flat white (painted shadow under the lash)
  lash_fwd      lash band 0.6 mm further forward (z-fighting test)
  id            flat ids: lash red, skirt magenta, eyeball green, lids blue, head grey, crease yellow
"""
import os
import sys

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "lid_diag"}
exec(open(p).read().split("FACE = (700")[0], g)
FRONT = (1070, 405, 1270, 525)
SIDE = (880, 380, 1160, 540)


def shoot(case):
    g["shoot"](f"lid_{case}_front", FRONT, 0, 4.0)
    g["shoot"](f"lid_{case}_34", SIDE, 35, 3.0)


O = bpy.data.objects
lash = O["Eye_Lash.L"]
lids = O["Eye_Lids.L"]
ball = O["Eye_Ball.L"]
nb = lash.get("mmg_band_cols")


def flat(name, col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = col
    nt.links.new(e.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    return m


def tex_node(m):
    return next(n for n in m.node_tree.nodes if n.type == "TEX_IMAGE")


def skirt_faces(o):
    """faces of the lash band touching the skirt row (row 0 of each band column), from the build layout"""
    rows = int(o.get("mmg_band_rows", 7))
    ncol = int(o.get("mmg_band_cols", (len(o.data.vertices) - 36) // 7))      # v6b: band columns, then 6 x 6 lower lash
    sk = {i * rows for i in range(ncol)}
    return [f.index for f in o.data.polygons if any(v in sk for v in f.vertices)]


for o in O:                                                   # hair off: the lid itself is the subject
    if o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip"):
        o.hide_render = True
shoot("full")
lash.hide_render = True
shoot("no_lash")
lash.hide_render = False

me0 = lash.data
me1 = me0.copy()
bm = bmesh.new()
bm.from_mesh(me1)
bm.faces.ensure_lookup_table()
sf = set(skirt_faces(lash))
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sf], context="FACES_ONLY")
bm.to_mesh(me1)
bm.free()
lash.data = me1
shoot("no_skirt")
lash.data = me0

lids.hide_render = True
shoot("no_lids")
lids.hide_render = False

outl = [o.modifiers["TT_Outline"] for o in O if hasattr(o, "modifiers") and "TT_Outline" in o.modifiers]
for md in outl:
    md.show_render = False
shoot("no_outline")
for md in outl:
    md.show_render = True

lm = lash.material_slots[0].material
m2 = lm.copy()
em = next(n for n in m2.node_tree.nodes if n.type == "EMISSION")
for l in list(em.inputs["Color"].links):
    m2.node_tree.links.remove(l)
em.inputs["Color"].default_value = E.srgb((45, 20, 18))
lash.material_slots[0].material = m2
shoot("lash_flat")
m3 = lm.copy()
nt = m3.node_tree
mix = next(n for n in nt.nodes if n.type == "MIX_SHADER")
nt.links.new(tex_node(m3).outputs["Alpha"], mix.inputs[0])
if hasattr(m3, "surface_render_method"):
    m3.surface_render_method = "BLENDED"
lash.material_slots[0].material = m3
shoot("lash_blend")
lash.material_slots[0].material = lm

bmat = ball.material_slots[0].material
b2 = bmat.copy()
em = next(n for n in b2.node_tree.nodes if n.type == "EMISSION")
mul = next(n for n in b2.node_tree.nodes if n.type == "MIX" and n.blend_type == "MULTIPLY")
for l in list(mul.inputs["A"].links):
    b2.node_tree.links.remove(l)
mul.inputs["A"].default_value = (0.92, 0.9, 0.9, 1)
ball.material_slots[0].material = b2
shoot("ball_flat")
ball.material_slots[0].material = bmat

kb = lash.data.shape_keys.key_blocks["Basis"] if lash.data.shape_keys else None
co0 = [v.co.copy() for v in lash.data.vertices]
if kb:
    k0 = [d.co.copy() for d in kb.data]
    for d in kb.data:
        d.co.y -= 0.0006
for v in lash.data.vertices:
    v.co.y -= 0.0006
lash.data.update()
shoot("lash_fwd")
for v, c in zip(lash.data.vertices, co0):
    v.co = c
if kb:
    for d, c in zip(kb.data, k0):
        d.co = c
lash.data.update()

# id: which object paints each pixel
ids = {"lash": flat("D_Red", (1, 0, 0, 1)), "skirt": flat("D_Mag", (1, 0, 1, 1)), "ball": flat("D_Green", (0, 1, 0, 1)),
       "lids": flat("D_Blue", (0, 0, 1, 1)), "head": flat("D_Grey", (0.5, 0.5, 0.5, 1)), "crease": flat("D_Yel", (1, 1, 0, 1))}
saved = {o.name: [s.material for s in o.material_slots] for o in O if o.type == "MESH"}
for o in O:
    if o.type != "MESH":
        continue
    for i, s in enumerate(o.material_slots):
        if o.name.startswith("Eye_Lash"):
            m = s.material.copy()
            em = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
            for l in list(em.inputs["Color"].links):
                m.node_tree.links.remove(l)
            em.inputs["Color"].default_value = (1, 0, 0, 1)
            s.material = m
        elif o.name.startswith("Eye_Ball"):
            s.material = ids["ball"]
        elif o.name.startswith("Eye_Lids"):
            s.material = ids["lids"]
        else:
            s.material = ids["head"]
# skirt in magenta: second material slot on the skirt faces
lash.data.materials.append(ids["skirt"])
for fi in sf:
    lash.data.polygons[fi].material_index = len(lash.data.materials) - 1
for md in outl:
    md.show_render = False
shoot("id")
print("LID_DIAG_DONE", tag, "skirt faces", len(sf))
