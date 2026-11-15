"""ToonTest_01 step 22 (Blender, background): hair_bob_01 v5g = v5f + temple link strands. v5f is kept as it is.

usage: Blender -b <MG_ToonTest_01_v5f_finish.blend> --python t22_hair_v5g.py
Writes MG_ToonTest_01_v5g_temple.blend and spec/hair_v5g_stats.json.

Between the bang side lock D and the side hair the temple skin was open from the outer eye corner back to the ear
(3/4 and side views, character left). Link strands (hair_bob_01__TempleLink_L / _R) start under the outer root of
the bang side lock and run down past the outer eye corner. Character left, two strands:
  front strand  narrow (1.1..1.3 cm), past the outer eye corner, ends beside the cheek
  back strand   wider (to 2.4 cm), a lock from the bang root onto the front of the temple layer, ending on it above
                the ear (going further down would bridge the 2.5 cm step from the layer to the cheek and float); the
                temple layer then carries the flow over the ear top to behind the ear, ear front / lobe stay visible
Character right (already covered by the larger bang lock A; two strands only added edges there): one thin strand
just behind the edge of A. Widths, lengths and paths all differ. They lie 3..4 mm off the skin / ear, 2 mm above the volume and the temple layer, below
the bangs at the root; the radius field is smoothed and kept above that clearance, then every vertex is kept >= 5 mm from the ear and
3.5 mm from the head by nearest-point distance (no floating, no penetration).
Same material (streaks, flow highlight), baked AO, brown outline. Nothing else changes.
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(H.EXP)
rng = random.Random(22)
coll = bpy.data.collections[H.COLL]


def dirv(th):
    t = math.radians(th)
    return Vector((math.sin(t), -math.cos(t), 0.0))


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def rho_on(bvh, th, z):
    d = dirv(th); o = Vector((0, H.AX_Y, z))
    h = bvh.ray_cast(o + d * 1.0, -d, 1.0)
    return None if h[0] is None else (h[0] - o).length


def bm_bvh(name):
    o = bpy.data.objects[name]; bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    t = H.bvh_of_bmesh(bm); bm.free(); return t


HEAD = H.bvh_of(["Blockout_Head"]); EARS = H.bvh_of(["Face_Ear.L", "Face_Ear.R"])
VOL = bm_bvh("hair_bob_01__Volume_outer_ref")
SIDES = H.bvh_of(["hair_bob_01__Side_L", "hair_bob_01__Side_R"])
BANGS = bm_bvh("hair_bob_01__Bangs")

# strands, character left (+theta); keys (theta deg, z), width (m) at the keys, taper start (0..1 along)
STRANDS = {
    "L": [
        dict(keys=[(50, 1.525), (55, 1.470), (60, 1.422), (64, 1.388), (67, 1.355)], w=[0.013, 0.016, 0.017, 0.014, 0.007], taper=0.60),
        dict(keys=[(55, 1.532), (61, 1.474), (66, 1.428), (69, 1.398), (71, 1.372)], w=[0.018, 0.024, 0.024, 0.017, 0.006], taper=0.62),
    ],
    "R": [   # the larger bang lock A already covers this temple: one thin strand behind its edge
        dict(keys=[(60, 1.520), (64, 1.470), (69, 1.425), (73, 1.390), (75, 1.366)], w=[0.008, 0.010, 0.010, 0.008, 0.004], taper=0.60),
    ],
}
R0 = 0.155                                                   # radius used to turn angles into arc length


def catmull(ps, n):
    out = []
    seg = len(ps) - 1
    for i in range(n):
        t = i / (n - 1) * seg; k = min(int(t), seg - 1); f = t - k
        p0, p1, p2, p3 = ps[max(k - 1, 0)], ps[k], ps[k + 1], ps[min(k + 2, seg)]
        out.append(tuple(0.5 * ((2 * b) + (-a + c) * f + (2 * a - 5 * b + 4 * c - d) * f * f + (-a + 3 * b - 3 * c + d) * f ** 3)
                         for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


def floor_rho(th, z):
    c = []
    for bvh, off in ((HEAD, 0.003), (EARS, 0.004), (VOL, 0.002), (SIDES, 0.002)):
        r = rho_on(bvh, th, z)
        if r is not None:
            c.append(r + off)
    return max(c) if c else 0.15


def strand(bm, uvl, cl, sd, sign, rand, nr=26, nc=6):
    keys = [(math.radians(th) * R0, z) for th, z in sd["keys"]]
    path = catmull(keys, nr)
    wk = sd["w"]
    grid = []
    for r, (s, z) in enumerate(path):
        t = r / (nr - 1)
        a, b = path[max(r - 1, 0)], path[min(r + 1, nr - 1)]
        ds, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(ds, dz) or 1.0
        ps, pz = -dz / L, ds / L                                  # across the strand (surface coordinates)
        wi = t * (len(wk) - 1); k = min(int(wi), len(wk) - 2)
        w = wk[k] + (wk[k + 1] - wk[k]) * (wi - k)
        w *= 1 - 0.85 * smooth01((t - sd["taper"]) / (1 - sd["taper"]))
        w *= 0.35 + 0.65 * smooth01(t / 0.15)                     # root grows out from under the bang
        row = []
        for j in range(nc):
            u = j / (nc - 1) - 0.5
            ss, zz = s + ps * w * u, z + pz * w * u
            th = sign * math.degrees(ss / R0)
            fl = floor_rho(th, zz)
            rb = rho_on(BANGS, th, zz)
            row.append([th, zz, fl + 0.001 * (1 - abs(u) * 2), fl, rb])   # slight crown across the strand
        grid.append(row)
    for _ in range(25):                                           # drape along the strand, never below the floor
        new = [[g[2] for g in row] for row in grid]
        for r in range(nr):
            for j in range(nc):
                nb = [grid[r2][j][2] for r2 in (r - 1, r + 1) if 0 <= r2 < nr] + [grid[r][j2][2] for j2 in (j - 1, j + 1) if 0 <= j2 < nc]
                new[r][j] = max(grid[r][j][3], (grid[r][j][2] * 2 + sum(nb)) / (2 + len(nb)))
        for r in range(nr):
            for j in range(nc):
                grid[r][j][2] = new[r][j]
    vs = []
    for r, row in enumerate(grid):
        vr = []
        for th, z, rho, fl, rb in row:
            if rb is not None and rho > rb - 0.0015 and rb > fl:      # stay under the bang where it covers the root
                rho = max(fl, rb - 0.0015)
            p = Vector((0, H.AX_Y, z)) + dirv(th) * rho
            for bvh, gap in ((EARS, 0.005), (HEAD, 0.0035)):     # 3D clearance incl. the 1.8 mm shell (ear front leans forward)
                loc, nrm, _, dist = bvh.find_nearest(p, 0.02)
                if loc is not None:
                    side_ = (p - loc).dot(nrm)
                    if side_ < gap:
                        p = loc + nrm * gap
            vr.append(bm.verts.new(p))
        vs.append(vr)
    for r in range(nr - 1):
        for j in range(nc - 1):
            f = bm.faces.new((vs[r][j], vs[r][j + 1], vs[r + 1][j + 1], vs[r + 1][j]))
            for loop, (jj, rr) in zip(f.loops, [(j, r), (j + 1, r), (j + 1, r + 1), (j, r + 1)]):
                loop[uvl].uv = (jj / (nc - 1), rr / (nr - 1)); loop[cl] = (1.0, rand, rr / (nr - 1), 1.0)


objs = []
for side, sign in (("L", 1), ("R", -1)):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
    for sd in STRANDS[side]:
        strand(bm, uvl, cl, sd, sign, rng.random())
    H.orient_outward(bm)
    o = H.mesh_object(f"hair_bob_01__TempleLink_{side}", bm, coll)
    H.apply_solidify(o, 0.0018, -1.0, True)
    for v in o.data.vertices:                                   # the inner shell too: keep it out of the ear / head
        for bvh, gap in ((EARS, 0.0015), (HEAD, 0.0012)):
            loc, nrm, _, dist = bvh.find_nearest(v.co, 0.02)
            if loc is not None and (v.co - loc).dot(nrm) < gap:
                v.co = loc + nrm * gap
    o.data.materials.append(bpy.data.materials["M_hair_bob_01_01"])
    objs.append(o)
others = ["hair_bob_01__Volume", "hair_bob_01__Bangs", "hair_bob_01__Side_L", "hair_bob_01__Side_R", "hair_bob_01__Back"]
H.bake_ao(objs, [o.name for o in objs] + others + ["Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
for o in objs:
    H.add_outline(o, 0.0007)
stats = {o.name: dict(verts=len(o.data.vertices), tris=sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in objs}
json.dump(stats, open(os.path.join(H.EXP, "spec", "hair_v5g_stats.json"), "w"), indent=1)
print("V5G", json.dumps(stats))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5g_temple.blend"))
print("V5G_OK")
