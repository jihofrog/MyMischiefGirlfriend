"""ToonTest_01 step 73 (Blender, background, the .blend is not saved): eyeball px past the face outline, per eye and angle.

usage: Blender -b <file.blend> --python t73_eye_v6i_outline.py -- <tag> [view]
Orthographic rays (t03 camera, no hair, 0.5 px of the x1 render) over each eye box at 0, +-15, +-25, +-35, +-45, +-60,
+-90; with "view" the ViewFar keys are set per angle (eye_v6_common.view_key_values). Per eye: visible eyeball hits, and
the ones whose ray, continued through the eyeball, meets nothing else (the eyeball shows past the face outline).
Writes spec/eye_v6i_outline_<tag>.json.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag, view = args[0], "view" in args
O = bpy.data.objects
AXY = 0.03
for o in O:
    if "TT_Outline" in getattr(o, "modifiers", {}):
        o.modifiers["TT_Outline"].show_viewport = False
BOX = json.load(open(os.path.join(E.EXP, "spec", "eye_f6_boxes_v6i.json")))
res = {}
for a in (0, 15, -15, 25, -25, 35, -35, 45, -45, 60, -60, 90, -90):
    vw = E.view_key_values(a) if view else {}
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = vw.get(k.name, 0.0)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    V, F, own, names = [], [], [], []
    for o in O:
        if o.type != "MESH" or o.hide_render or o.name.startswith(("hair_bob_01", "acc_head_hairclip", "Face_Blush")):
            continue
        vs, fs = E.world_mesh(o, dg)
        k = len(V)
        V += vs
        F += [tuple(i + k for i in f) for f in fs]
        own += [len(names)] * len(fs)
        names.append(o.name)
    B = BVHTree.FromPolygons(V, F)
    t = math.radians(a)
    d = Vector((-math.sin(t), math.cos(t), 0.0))
    for s in "LR":
        ball = names.index(f"Eye_Ball.{s}")
        x0, y0, x1, y1 = BOX[f"{s}_{a}"]
        vis = past = 0
        for py in np.arange(y0, y1, 0.5):
            z = float(E.Z(py))
            for px in np.arange(x0, x1, 0.5):
                sx = (px - 1030) / E.PPM
                o = Vector((sx * math.cos(t), sx * math.sin(t) + AXY, z)) - d * 3
                h = B.ray_cast(o, d, 10)
                if h[0] is None or own[h[2]] != ball:
                    continue
                vis += 1
                q = h[0] + d * 0.0005
                while True:
                    h2 = B.ray_cast(q, d, 10)
                    if h2[0] is None:
                        past += 1
                        break
                    if own[h2[2]] != ball:
                        break
                    q = h2[0] + d * 0.0005
        far = (s == "R") == (a > 0) and a != 0
        res[f"{s}_{a}"] = dict(far=far, visible_eyeball=vis, past_outline=past)
        print("OUT", tag, s, a, "far" if far else "near", vis, past)
json.dump(res, open(os.path.join(E.EXP, "spec", f"eye_v6i_outline_{tag}.json"), "w"), indent=1)
print("OUTLINE_OK", tag)
