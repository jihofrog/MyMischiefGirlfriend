"""ToonTest_01 step 41 (Blender, background, the .blend is not saved): v6e renders at 0 / 35 / 45 / 60 / 90 deg.

usage: Blender -b <file.blend> --python t41_eye_v6e_render.py -- <tag> [quick]
Same orthographic camera / sun as t03 (light fixed to the camera). Boxes follow the projected eye centres.
renders/<tag>_e6_*.png:
  face_<a>            whole face with hair
  eyes_<a>            both eyes, no hair (x2)
  eyeL_<a>            left eye, no hair (x3)
  struct_<a>          left eye, no hair, shaded flat colours: skin grey, lid sheets blue, eyeball green, lashes red
  sil_<a>, silhead_<a>  60 / 90: eyeball yellow + head blue / head alone (eyeball outside the face outline)
  expr_<pose>_<a>     a = 0 and 35, both eyes with hair: Neutral, Blink50, Blink, EyeSmile, SmileEyeSmile, Surprise,
                      GazeL, GazeR
and spec/eye_e6_section_<tag>.json: top view section through the left iris centre, front-most surface per part.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
quick = "quick" in args
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "e6"}
exec(open(p).read().split("FACE = (700")[0], g)
O = bpy.data.objects
HAIR = [o for o in O if (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip")) and not o.hide_render]
ANG = (0, 35, 45, 60, 90)
AXY = 0.03


def centre(s):
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    return np.array([x, y, z])


CL, CR = centre("L"), centre("R")


def px_of(pnt, a):
    t = math.radians(a)
    return 1030 + E.PPM * (pnt[0] * math.cos(t) + (pnt[1] - AXY) * math.sin(t)), float(E.PY(pnt[2]))


def box(cx, cy, w, h):
    return (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))


def shoot(name, b, a, sc=1.0):
    g["shoot"]("e6_" + name, b, a, sc)


def hair(show):
    for o in HAIR:
        o.hide_render = not show


def keys(w):
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = w.get(k.name, 0.0)
    bpy.context.view_layer.update()


def gaze(v):
    E.set_gaze(v)


keys({})
gaze(0)
for a in ANG:
    hair(True)
    shoot(f"face_{a}", (600, 0, 1460, 860), a)
    hair(False)
    xl, yl = px_of(CL, a)
    xr, yr = px_of(CR, a)
    shoot(f"eyes_{a}", box((xl + xr) / 2, (yl + yr) / 2, 560, 220), a, 2.0)
    shoot(f"eyeL_{a}", box(xl, yl, 260, 170), a, 3.0)
hair(True)
POSES = (("Neutral", {}, 0), ("Blink50", {"Blink": 0.5}, 0), ("Blink", {"Blink": 1.0}, 0), ("EyeSmile", {"EyeSmile": 1.0}, 0),
         ("SmileEyeSmile", {"Smile": 1.0, "EyeSmile": 1.0}, 0), ("Surprise", {"Surprise": 1.0}, 0),
         ("GazeL", {}, 0.15), ("GazeR", {}, -0.15))
for a in ((0, 35) if not quick else (35,)):
    xl, yl = px_of(CL, a)
    xr, yr = px_of(CR, a)
    for pn, w, gz in POSES:
        keys(w)
        gaze(gz)
        shoot(f"expr_{pn}_{a}", box((xl + xr) / 2, (yl + yr) / 2 + 20, 560, 260), a, 1.4)
keys({})
gaze(0)
if quick:
    sys.exit(0)

# ------------------------------------------------------------------ structure colours / silhouette ids (no hair)
hair(False)


def mat(name, col, emit=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    if emit:
        sh = nt.nodes.new("ShaderNodeEmission")
        sh.inputs["Color"].default_value = col
    else:
        sh = nt.nodes.new("ShaderNodeBsdfDiffuse")
        sh.inputs["Color"].default_value = col
    nt.links.new(sh.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    return m


vis = [o for o in O if o.type in ("MESH", "CURVE") and not o.hide_render and o.visible_get()]
saved = {o.name: [s.material for s in o.material_slots] for o in vis}
outl = [o.modifiers["TT_Outline"] for o in vis if hasattr(o, "modifiers") and "TT_Outline" in o.modifiers]


def assign(mode):
    cols = {"skin": (0.55, 0.55, 0.55, 1), "lid": (0.15, 0.3, 0.95, 1), "ball": (0.1, 0.85, 0.2, 1), "lash": (0.9, 0.1, 0.1, 1),
            "other": (0.3, 0.3, 0.3, 1)}
    if mode == "sil":
        cols = {"skin": (0, 0, 1, 1), "lid": (0, 0, 1, 1), "ball": (1, 1, 0, 1), "lash": (1, 0, 1, 1), "other": (0, 0, 0, 1)}
    ms = {k: mat(f"E6_{mode}_{k}", c, emit=(mode != "struct")) for k, c in cols.items()}
    for o in vis:
        n = o.name
        r = ("ball" if n.startswith("Eye_Ball") else "lid" if n.startswith("Eye_Lids") else "lash" if n.startswith("Eye_Lash")
             else "skin" if n.startswith("Blockout_Head") or n.startswith("Face_Ear") else "other")
        o.hide_render = (mode == "silhead" and r in ("ball", "lash"))
        for s_ in o.material_slots:
            s_.material = ms["skin" if mode == "silhead" and r == "lid" else r]


for md in outl:
    md.show_render = False
assign("struct")
for a in ANG:
    xl, yl = px_of(CL, a)
    shoot(f"struct_{a}", box(xl, yl, 260, 170), a, 3.0)
for mode in ("sil", "silhead"):
    assign(mode)
    for a in (35, 45, 60, 90):
        shoot(f"{mode}_{a}", (600, 200, 1460, 760), a)
for o in vis:
    o.hide_render = False
    for s_, m in zip(o.material_slots, saved[o.name]):
        s_.material = m
for md in outl:
    md.show_render = True

# top view section through the left iris centre (front-most surface per part along y)
roles = {"skin": ["Blockout_Head"], "lid": ["Eye_Lids.L"], "lash": ["Eye_Lash.L"], "ball": ["Eye_Ball.L"]}
sec = {"centre": CL.tolist()}
for r, ns in roles.items():
    b = E.bvh_of(ns)
    pts = []
    for x in np.arange(0.0, 0.135, 0.0005):
        y, _ = E.front_hit(b, x, CL[2])
        pts.append((float(x), None if y is None else float(y)))
    sec[r] = pts
json.dump(sec, open(os.path.join(EXP, "spec", f"eye_e6_section_{tag}.json"), "w"))
print("E6_RENDER_DONE", tag)
