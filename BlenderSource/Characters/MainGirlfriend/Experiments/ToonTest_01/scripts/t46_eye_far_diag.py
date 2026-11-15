"""ToonTest_01 step 46 (Blender, background, the .blend is not saved): which mesh shows in the far eye at 3/4 views.

usage: Blender -b <file.blend> --python t46_eye_far_diag.py -- <tag> [angles...]
Same camera / sun / boxes as t45 (far eye = the eye away from the camera: R for + angles, L for - angles), x4, no hair.
renders/<tag>_f6_id_<a>.png, flat colours (emission, back faces at 35 % brightness):
  head skin grey (0.6), upper lid sheet blue, upper lid skirt (edge thickness) cyan, lower lid sheet violet,
  lower lid skirt pink, eyeball green, lash band (texture alpha) red, lash skirt orange, lower lash yellow, crease
  white, brows / other dark grey
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
ANGS = [int(a) for a in args[1:] if a.lstrip("-").isdigit()] or [35, 45, -35, -45]
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "f6"}
exec(open(p).read().split("FACE = (700")[0], g)
O = bpy.data.objects
AXY = 0.03
COL = dict(skin=(0.6, 0.6, 0.6), up=(0.1, 0.25, 1.0), upsk=(0.0, 0.9, 1.0), lo=(0.55, 0.2, 0.9), losk=(1.0, 0.45, 0.75),
           ball=(0.1, 0.85, 0.2), lash=(0.9, 0.05, 0.05), lashsk=(1.0, 0.5, 0.0), lowlash=(1.0, 0.95, 0.0),
           crease=(1.0, 1.0, 1.0), other=(0.25, 0.25, 0.25))


def id_mat(key, tex=None):
    m = bpy.data.materials.new(f"F6_{key}")
    m.use_nodes = True
    m.blend_method = "HASHED" if tex else "OPAQUE"
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    c = COL[key]
    mix.inputs[6].default_value = (*c, 1)
    mix.inputs[7].default_value = (c[0] * 0.35, c[1] * 0.35, c[2] * 0.35, 1)
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    if tex is None:
        nt.links.new(em.outputs[0], out.inputs[0])
        return m
    ti = nt.nodes.new("ShaderNodeTexImage")
    ti.image = tex
    uvn = nt.nodes.new("ShaderNodeUVMap")
    nt.links.new(uvn.outputs[0], ti.inputs[0])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    ms = nt.nodes.new("ShaderNodeMixShader")
    gt = nt.nodes.new("ShaderNodeMath")
    gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = 0.5
    nt.links.new(ti.outputs["Alpha"], gt.inputs[0])
    nt.links.new(gt.outputs[0], ms.inputs[0])
    nt.links.new(tr.outputs[0], ms.inputs[1])
    nt.links.new(em.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    return m


def lash_image(o):
    for n in o.material_slots[0].material.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            return n.image


for o in O:
    if o.type in ("MESH", "CURVE") and (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head")):
        o.hide_render = True
    if hasattr(o, "modifiers") and "TT_Outline" in o.modifiers:
        o.modifiers["TT_Outline"].show_render = False
NOOUT = "nooutline" in args
if NOOUT:
    args.remove("nooutline")
vis = [o for o in O if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()]
for o in vis:
    if o.name.startswith("Face_Blush"):
        o.hide_render = True          # transparent radial quad: would hide what is behind it in flat colours
M = {k: id_mat(k) for k in COL}
for o in vis:
    n = o.name
    me = o.data
    if o.type != "MESH":
        for s_ in o.material_slots:
            s_.material = M["other"]
        continue
    if n.startswith("Eye_Lids"):
        nc = len(me.vertices) // 14
        me.materials.clear()
        for k in ("up", "upsk", "lo", "losk"):
            me.materials.append(M[k])
        for f in me.polygons:
            vs = list(f.vertices)
            lower = min(vs) >= nc * 7
            rows = [v % 7 for v in vs]
            skirt = min(rows) == 0
            f.material_index = (2 if lower else 0) + (1 if skirt else 0)
    elif n.startswith("Eye_Lash"):
        nb, nr, cs = int(o["mmg_band_cols"]), int(o["mmg_band_rows"]), int(o["mmg_crease_start"])
        img = lash_image(o)
        me.materials.clear()
        for k in ("lash", "lashsk", "lowlash", "crease"):
            me.materials.append(id_mat(k, img) if k in ("lash", "lowlash") else M[k])
        for f in me.polygons:
            vs = list(f.vertices)
            if min(vs) >= cs:
                f.material_index = 3
            elif min(vs) >= nb * nr:
                f.material_index = 2
            else:
                f.material_index = 1 if min(v % nr for v in vs) == 0 else 0
    else:
        key = ("ball" if n.startswith("Eye_Ball") else "skin" if n.startswith(("Blockout_Head", "Face_Ear")) else "other")
        for s_ in o.material_slots:
            s_.material = M[key]


def eye_px(s, a):
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    t = math.radians(a)
    return 1030 + E.PPM * (x * math.cos(t) + (y - AXY) * math.sin(t)), float(E.PY(z))


for a in ANGS:
    s = "R" if a > 0 else "L"
    cx, cy = eye_px(s, a)
    b = (int(cx - 110), int(cy - 85), int(cx + 130), int(cy + 85)) if s == "R" else (int(cx - 130), int(cy - 85), int(cx + 110), int(cy + 85))
    g["shoot"](f"f6_id_{a}", b, a, 4.0)
print("F6_DIAG_DONE", tag)
