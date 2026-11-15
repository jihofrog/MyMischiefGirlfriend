"""ToonTest_01 step 68 (Blender, background): v6h from v6f_A - a separate eye-tail skin piece over the outer white.

usage: V6H_K=<0..1> V6H_OUT=<file.blend> Blender -b MG_ToonTest_01_v6f_A.blend --python t68_eye_v6h.py
New mesh Eye_TailWrap.<s> (TT_Skin, no shape keys) lies 0.12 mm over the eyeball. Per row of the r30 opening its inner edge
is the outer opening edge pulled toward the iris centre by V6H_K (u -> K u, u = distance from the iris centre toward the
outer corner), so the uncovered white keeps the shape of an eye corner (upper and lower lid lines meet earlier). Outward
it runs 1 mm under the lid sheets and the rim, so the lids and the skin overlap it without a seam. The eyeball is not
changed. The lid sheets and the lash rows on the eyeball are lifted (all keys) until every key blend stays 0.1 mm over
eyeball and piece (t51 blend_lift / t62 lash_lift). Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6f_A.blend"
K = float(os.environ.get("V6H_K", 0.85))
OUT = os.environ["V6H_OUT"]
OFF = 0.00012                        # over the eyeball
TUCK = 0.0010                        # under lids / rim past the r30 opening
O = bpy.data.objects
stats = dict(k=K, offset_mm=OFF * 1000, tuck_mm=TUCK * 1000)


def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


def build(s):
    ib = E.TGT[s]["iris_bbox"]
    sg = 1 if s == "L" else -1
    xc = float(E.X((ib[0] + ib[2]) / 2))
    poly = E.opening_poly(s)
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    zs_all = poly[:, 1]
    z0, z1 = zs_all.min(), zs_all.max()
    rows = []
    for z in np.linspace(z0 + 0.0004, z1 - 0.0004, 48):
        u = np.arange(0.0, 0.08, 0.0001)
        inside = E.signed_dist(np.stack([xc + sg * u, np.full_like(u, z)], 1), poly) < 0
        if not inside.any():
            continue
        uo = u[np.nonzero(inside)[0].max()]          # outer opening edge in this row
        if uo < 0.002:
            continue
        rows.append((z, K * uo, uo + TUCK))
    NC = 10
    V, ok = [], []
    for z, ua, ub in rows:
        for i in range(NC):
            uu = ua + (ub - ua) * i / (NC - 1)
            V.append((xc + sg * uu, 0.0, z))
    V = np.array(V)
    by = ball_y(BALL, V)
    # past the eyeball edge (under the rim) keep the last depth of the row
    for r in range(len(rows)):
        seg = by[r * NC:(r + 1) * NC]
        good = np.isfinite(seg)
        if not good.any():
            seg[:] = np.nan
            continue
        last = seg[good][-1]
        seg[~good] = last
        by[r * NC:(r + 1) * NC] = seg
    keep_row = [np.isfinite(by[r * NC]) for r in range(len(rows))]
    V[:, 1] = by - OFF
    faces = []
    for r in range(len(rows) - 1):
        if not (keep_row[r] and keep_row[r + 1]):
            continue
        for i in range(NC - 1):
            a, b = r * NC + i, r * NC + i + 1
            c, d = (r + 1) * NC + i + 1, (r + 1) * NC + i
            faces.append((a, b, c, d) if s == "R" else (a, d, c, b))
    used = sorted({v for f in faces for v in f})
    remap = {v: k for k, v in enumerate(used)}
    me = bpy.data.meshes.new(f"Eye_TailWrap.{s}")
    me.from_pydata([tuple(V[v]) for v in used], [], [tuple(remap[v] for v in f) for f in faces])
    me.update()
    # faces toward the viewer (-y)
    ny = np.mean([p.normal.y for p in me.polygons])
    if ny > 0:
        for p in me.polygons:
            p.flip()
        me.update()
    for p in me.polygons:
        p.use_smooth = True
    uv = me.uv_layers.new(name="UVMap")
    for lp in me.loops:
        co = me.vertices[lp.vertex_index].co
        uv.data[lp.index].uv = (co.x * 5 + 0.5, co.z * 5 + 0.5)
    me.materials.append(bpy.data.materials["TT_Skin"])
    o = bpy.data.objects.new(f"Eye_TailWrap.{s}", me)
    O[f"Eye_Lids.{s}"].users_collection[0].objects.link(o)
    # check: the piece must stay behind the head skin wherever the skin is in front of the eyeball
    HEAD = E.bvh_of(["Blockout_Head"])
    P = np.array([tuple(v.co) for v in me.vertices])
    hy = ball_y(HEAD, P)
    poke = int(np.sum(np.isfinite(hy) & (P[:, 1] < hy - 0.00002) & (hy < by[used] - 0.00002)))
    stats[f"piece_{s}"] = dict(verts=len(me.vertices), faces=len(me.polygons), rows=len(rows),
                               in_front_of_head_skin=poke)
    return o


for s in E.SIDES:
    build(s)
bpy.context.view_layer.update()

# lid and lash key blends clear of eyeball + piece
src = open(os.path.join(HERE, "t51_eye_v6f.py")).read()
i, j = src.index("def blend_lift"), src.index("# ------------------------------------------------------------------ A: lid boundary")
exec(src[i:j])
src = open(os.path.join(HERE, "t62_eye_v6g.py")).read()
i, j = src.index("def lash_lift"), src.index("for s in E.SIDES:\n    lash_lift")
exec(src[i:j])
for s in E.SIDES:
    B = E.bvh_of([f"Eye_Ball.{s}", f"Eye_TailWrap.{s}"])
    blend_lift(s, B)  # noqa: F821
    lash_lift(s, B)  # noqa: F821

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6H_OK", json.dumps(stats))
