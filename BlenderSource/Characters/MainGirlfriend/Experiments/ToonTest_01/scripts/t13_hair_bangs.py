"""ToonTest_01 step 13 / stage C (Blender, background): five large bang clumps on the hair_bob_01 v2 volume.

usage: Blender -b <MG_ToonTest_01_v5a_volume.blend> --python t13_hair_bangs.py
Writes MG_ToonTest_01_v5c_bangs.blend (v5a untouched).

Clumps follow the r30 Bangs layer: the layer is cut into five asymmetric clumps by lines from the parting to the two
forehead gaps and the two tip notches; each clump keeps the r30 outline (rows of the layer, smoothed) and is lifted
onto the volume (over the hair) or the forehead (8 mm off the skin) as a thin curved sheet (2.5 mm).
  A  character-right side lock (in front of the cheek)   B1, B2  centre   C  centre-left   D  character-left side lock
The X clip (acc_head_hairclip_x_01, on its socket) is put back on the new surface at the r30 clip centre.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(H.EXP)
rng = random.Random(11)
coll = bpy.data.collections[H.COLL]

PART = (1027, 50)
# clump boundaries in r30 pixels: from the parting through a gap apex / tip notch, then straight down
BOUNDS = [
    [(PART[0], 0), PART, (912, 305), (903, 1000)],             # A | B1   (forehead gap 1)
    [(PART[0], 0), PART, (958, 400), (958, 1000)],             # B1 | B2  (tip notch)
    [(PART[0], 0), PART, (1058, 405), (1060, 1000)],           # B2 | C   (tip notch)
    [(PART[0], 0), PART, (1121, 238), (1150, 400), (1150, 1000)],  # C | D (forehead gap 2)
]
NAMES = ["A", "B1", "B2", "C", "D"]
OFFS = [0.0035, 0.0048, 0.0040, 0.0048, 0.0035]          # alternate layer offsets so neighbours never z-fight


def bound_x(k, y):
    pts = BOUNDS[k]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if y <= y1:
            return x0 + (x1 - x0) * (y - y0) / max(y1 - y0, 1e-6)
    return pts[-1][0]


def clump_rows(k):
    rows = []
    for y in sorted(int(v) for v in H.TGT["bangs_runs"]):
        lo = bound_x(k - 1, y) - 3 if k > 0 else -1e9          # 3 px overlap with the neighbour
        hi = bound_x(k, y) + 3 if k < 4 else 1e9
        segs = [(max(a, lo), min(b, hi)) for a, b in H.TGT["bangs_runs"][str(y)] if min(b, hi) - max(a, lo) >= 2]
        if segs:
            rows.append((y, min(s[0] for s in segs), max(s[1] for s in segs)))
        elif rows:
            break
    # smooth the outline (drawing noise), keep the first / last rows
    sm = []
    for i, (y, xl, xr) in enumerate(rows):
        a, b = max(0, i - 2), min(len(rows), i + 3)
        sm.append((y, sum(r[1] for r in rows[a:b]) / (b - a), sum(r[2] for r in rows[a:b]) / (b - a)))
    return sm


def resample(rows, n):
    out = []
    for i in range(n):
        t = i / (n - 1) * (len(rows) - 1)
        j = min(int(t), len(rows) - 2); f = t - j
        a, b = rows[j], rows[j + 1]
        out.append(tuple(a[c] + (b[c] - a[c]) * f for c in range(3)))
    return out


vol_ref = bpy.data.objects["hair_bob_01__Volume_outer_ref"]
bmv = bmesh.new(); bmv.from_mesh(vol_ref.data); bmv.transform(vol_ref.matrix_world)
proj = H.FrontProjector(H.bvh_of_bmesh(bmv), ["Blockout_Head"])
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
stats = {}
for k, name in enumerate(NAMES):
    rows = clump_rows(k)
    stats[name] = dict(y=[rows[0][0], rows[-1][0]], width_px_mid=round(rows[len(rows) // 2][2] - rows[len(rows) // 2][1]))
    H.sheet_from_rows(bm, uvl, cl, resample(rows, 26), proj, OFFS[k], OFFS[k] + 0.0045, rng.random(), ncol=8)
H.orient_outward(bm)
bangs = H.mesh_object("hair_bob_01__Bangs", bm, coll)
H.apply_solidify(bangs, 0.0025, -1.0, True)
bangs.data.materials.append(bpy.data.materials["M_hair_bob_01_01"])

# X clip back on the surface at the r30 clip centre (its socket keeps the transform)
clip = bpy.data.objects.get("acc_head_hairclip_x_01"); sock = bpy.data.objects.get("Socket_acc_head")
if clip and sock:
    bx = H.SPEC["hairclip"]; cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
    bmb = bmesh.new(); bmb.from_mesh(bangs.data)
    hit = H.bvh_of_bmesh(bmb).ray_cast(Vector((H.px_x(cx), -1.0, H.py_z(cy))), Vector((0, 1, 0)), 2.0); bmb.free()
    if hit[0] is not None:
        n = (hit[1] if hit[1].y < 0 else -hit[1]).normalized()
        n = (n + Vector((0, -1.2, 0))).normalized()                 # face the front like the r30 drawing
        sock.matrix_world = Matrix.Translation(hit[0] + n * 0.008) @ n.to_track_quat("Z", "Y").to_matrix().to_4x4()
        clip.hide_render = False; clip.hide_viewport = False
        loc = hit[0]
        stats["clip"] = [round(v, 4) for v in loc]

H.bake_ao([bangs, bpy.data.objects["hair_bob_01__Volume"]],
          ["hair_bob_01__Volume", "hair_bob_01__Bangs", "Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
H.add_outline(bangs, 0.0008)
me = bangs.data
print("BANGS verts", len(me.vertices), "tris", sum(len(p.vertices) - 2 for p in me.polygons), stats)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5c_bangs.blend"))
print("STAGE_C_OK")
