"""ToonTest_01 step 47 (Blender, background, read only): horizontal sections through one eye (Basis pose).

usage: Blender -b <file.blend> --python t47_eye_sections.py -- <tag> [side=R]
Writes spec/eye_f6_sections_<tag>_<side>.json: for z = iris centre + (-4, -2, 0, +2, +4) mm, the segments (x, y pairs, m)
where Blockout_Head, Eye_Ball.<s>, Eye_Lids.<s> (upper / lower sheet) and Eye_Lash.<s> (band) cross that height.
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag = args[0]
s = args[1] if len(args) > 1 else "R"
O = bpy.data.objects
ib = E.TGT[s]["iris_bbox"]
zc = float(E.Z((ib[1] + ib[3]) / 2))
xc = float(E.X((ib[0] + ib[2]) / 2))
dg = bpy.context.evaluated_depsgraph_get()


def segs(o, z, face_filter=None):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = o.matrix_world
    V = np.array([tuple(mw @ v.co) for v in me.vertices])
    out = []
    for f in me.polygons:
        if face_filter and not face_filter(f):
            continue
        vs = list(f.vertices)
        P = V[vs]
        d = P[:, 2] - z
        if d.min() > 0 or d.max() < 0:
            continue
        pts = []
        for i in range(len(vs)):
            a, b = P[i], P[(i + 1) % len(vs)]
            da, db = d[i], d[(i + 1) % len(vs)]
            if (da <= 0 < db) or (db <= 0 < da):
                t = da / (da - db)
                q = a + t * (b - a)
                pts.append((round(float(q[0]), 5), round(float(q[1]), 5)))
        if len(pts) == 2 and abs(pts[0][0] - xc) < 0.07 and abs(pts[1][0] - xc) < 0.07:
            out.append(pts)
    ev.to_mesh_clear()
    return out


lids = O[f"Eye_Lids.{s}"]
nc = len(lids.data.vertices) // 14
lash = O[f"Eye_Lash.{s}"]
nbr = int(lash["mmg_band_cols"]) * int(lash["mmg_band_rows"])
res = dict(tag=tag, side=s, iris_centre_x=xc, iris_centre_z=zc, levels={})
for dz in (-4, -2, 0, 2, 4):
    z = zc + dz / 1000
    res["levels"][str(dz)] = dict(
        head=segs(O["Blockout_Head"], z),
        ball=segs(O[f"Eye_Ball.{s}"], z),
        lid_up=segs(lids, z, lambda f: min(f.vertices) < nc * 7),
        lid_lo=segs(lids, z, lambda f: min(f.vertices) >= nc * 7),
        lash=segs(lash, z, lambda f: max(f.vertices) < nbr),
    )
json.dump(res, open(os.path.join(E.EXP, "spec", f"eye_f6_sections_{tag}_{s}.json"), "w"))
print("SECTIONS_OK", tag, s, {k: len(v) for k, v in res["levels"]["0"].items()})
