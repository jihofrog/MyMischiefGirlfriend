"""ToonTest_01 step 67 (Blender, background, the .blend is not saved): which part of the eyeball the far-eye white strip is.

usage: Blender -b MG_ToonTest_01_v6f_A.blend --python t67_eye_v6h_tradeoff.py
Orthographic rays (same camera as t03 / t48, no hair) through the eye box of each eye at 0, +-35, +-45, +-60, +-90.
Every visible eyeball point outside the iris on the outer side gets its iris-ellipse radius rho (front projection, iris
edge = 1). Anything that lies on / over the eyeball and hides the white from rho = U0 outward hides the same eyeball area
in every view, so per U0 the share of the outer white (rho > 1) that would go is listed for the far eye (35 / 45) and for
the front and the near eye. Writes spec/eye_v6h_tradeoff.json and renders/v6h_tradeoff_<s>_<a>.png (visible outer white
coloured by rho: /tmp/v6h_tradeoff_*.npy, picture by t67b).
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

O = bpy.data.objects
AXY = 0.03
HAIR = {o.name for o in O if o.name.startswith(("hair_bob_01", "acc_head_hairclip"))}
for o in O:
    if "TT_Outline" in getattr(o, "modifiers", {}):
        o.modifiers["TT_Outline"].show_viewport = False
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
V, F, owner, names = [], [], [], []
for o in O:
    if o.type != "MESH" or o.hide_render or o.name in HAIR or o.name.startswith("Face_Blush"):
        continue
    vs, fs = E.world_mesh(o, dg)
    k = len(V)
    V += vs
    F += [tuple(i + k for i in f) for f in fs]
    owner += [len(names)] * len(fs)
    names.append(o.name)
BVH = BVHTree.FromPolygons(V, F)
owner = np.array(owner)

GEO = {}
for s in E.SIDES:
    ib = E.TGT[s]["iris_bbox"]
    GEO[s] = dict(sg=1 if s == "L" else -1, xc=float(E.X((ib[0] + ib[2]) / 2)), zc=float(E.Z((ib[1] + ib[3]) / 2)),
                  ax=abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2, az=abs(float(E.Z(ib[1]) - E.Z(ib[3]))) / 2)


def centre(s):
    g = GEO[s]
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), g["xc"], g["zc"])
    return g["xc"], y, g["zc"]


C = {s: centre(s) for s in E.SIDES}
STEP = 0.25 / E.PPM                     # 0.25 px of the x1 face render


def view(s, a):
    """outer white hits of eye s seen at angle a: list of rho"""
    t = math.radians(a)
    x, y, z = C[s]
    sc = x * math.cos(t) + (y - AXY) * math.sin(t)
    d = Vector((-math.sin(t), math.cos(t), 0.0))
    ball = names.index(f"Eye_Ball.{s}")
    g = GEO[s]
    out, img = [], []
    hw, hh = 120 / E.PPM, 85 / E.PPM
    for j, zz in enumerate(np.arange(z + hh, z - hh, -STEP)):
        row = []
        for sx in np.arange(sc - hw, sc + hw, STEP):
            o = Vector((sx * math.cos(t) - 2.0 * math.sin(t), sx * math.sin(t) + 2.0 * math.cos(t) + AXY, zz))
            o = o - d * 4.0
            h = BVH.ray_cast(o, d, 10.0)
            if h[0] is None or owner[h[2]] != ball:
                row.append(-1.0)
                continue
            p = h[0]
            u = g["sg"] * (p.x - g["xc"])
            rho = math.hypot(u / g["ax"], (p.z - g["zc"]) / g["az"])
            if u > 0 and rho > 1.0:
                out.append(rho)
                row.append(rho)
            else:
                row.append(0.0)
        img.append(row)
    return np.array(out), np.array(img)


U0 = (1.02, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4, 1.5)
res = {}
for s, a, role in (("R", 35, "far"), ("L", -35, "far"), ("R", 45, "far"), ("L", -45, "far"), ("L", 0, "front"),
                   ("R", 0, "front"), ("L", 35, "near"), ("R", -35, "near"), ("L", 60, "near"), ("L", 90, "near")):
    r, img = view(s, a)
    n = len(r)
    res[f"{s}_{a}"] = dict(role=role, outer_white_hits=n, rho_p50=round(float(np.median(r)), 3) if n else None,
                           rho_p95=round(float(np.percentile(r, 95)), 3) if n else None,
                           hidden_share={str(u): round(float((r > u).mean()), 3) if n else None for u in U0})
    np.save(os.path.join("/tmp", f"v6h_tradeoff_{s}_{a}.npy"), img)    # pictures: t67b (PIL is not in Blender)
    print(s, a, role, res[f"{s}_{a}"])
json.dump(res, open(os.path.join(E.EXP, "spec", "eye_v6h_tradeoff.json"), "w"), indent=1)
print("TRADEOFF_OK")

