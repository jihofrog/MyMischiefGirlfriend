"""ToonTest_01 step 16 (Blender, background): hair_bob_01 v5e = v5d with two local fixes; everything else kept.

usage: Blender -b <MG_ToonTest_01_v5d_side.blend> --python t16_hair_fix_v5e.py
Writes MG_ToonTest_01_v5e_fix.blend (v5d untouched) and spec/hair_v5e_stats.json. Checks: t17_hair_checks.py.

1. Ends (volume): below the ears the volume wrapped forward around the jaw and curled into a hook under the chin.
   The front wrap (faces below z 1.29 with a corner within 86 deg of the front) is cut away; it is covered by the temple layer.
   Vertices below z 1.275 move horizontally only: the ends hang down from the radius at 1.275 following the r30 width
   profile (bulge at the jaw kept) but never narrowing more than a light taper, plus a weak inward C curl in the last
   2.2 cm; toward the back the taper grows (0.24 -> 0.45) so the back keeps its round inward curl. Inner shell vertices keep their depth under the outer surface.
2. Ears (side layers): the side front layer is replaced by a temple layer that runs from the temple (under the bang
   side lock) over the top and back of the ear, then down beside the cheek and jaw (front edge ~3.5 cm off the skin,
   back edge on the volume) and on down to the ends without turning in under the chin; the front lower part of the
   ear stays visible. It drapes over volume / head / ear with clearance (smoothed, then pushed out again). The outer side layer is rebuilt unchanged on
   the adjusted volume.
Bangs, crown, clip, face, eyes and the toon material are not touched.
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
rng = random.Random(16)
coll = bpy.data.collections[H.COLL]
vol = bpy.data.objects["hair_bob_01__Volume"]; ref = bpy.data.objects["hair_bob_01__Volume_outer_ref"]


def dirv(th):
    t = math.radians(th)
    return Vector((math.sin(t), -math.cos(t), 0.0))


def theta_of(p):
    return math.degrees(math.atan2(p.x, -(p.y - H.AX_Y)))


def rho_on(bvh, th, z):
    d = dirv(th); o = Vector((0, H.AX_Y, z))
    h = bvh.ray_cast(o + d * 1.0, -d, 1.0)
    return None if h[0] is None else (h[0] - o).length


# ------------------------------------------------------------------ 1. ends hang down
bmr = bmesh.new(); bmr.from_mesh(ref.data)
OUTER = H.bvh_of_bmesh(bmr)
Z_REF, Z_END, TAPER, CURL, CURL_H = 1.275, 1.166, 0.24, 0.012, 0.022
CUT_Z, CUT_TH = 1.29, 86.0                 # front wrap under the ear (forward hook) is removed; the temple layer covers it


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def rho_old(th, z):
    for nudge in (0, 1, 2, 4, 6):
        r = rho_on(OUTER, th + math.copysign(nudge, th), z)
        if r is not None:
            return r
    return None


_hw = sorted((H.py_z(int(y)), (v[1] - v[0]) / 2 / H.PPM) for y, v in H.TGT["union_rows"].items())
_hw_sm = [(z, sum(w for _, w in _hw[max(0, i - 8):i + 9]) / len(_hw[max(0, i - 8):i + 9])) for i, (z, _) in enumerate(_hw)]
HW_REF = H.table(_hw_sm, Z_REF)


def profile(th, z):
    """Width ratio below Z_REF: the r30 outline (keeps its bulge at the jaw), but never narrower than a light taper,
    so only the very end turns in."""
    k = min(1.0, (Z_REF - z) / (Z_REF - Z_END))
    return max(H.table(_hw_sm, z) / HW_REF, 1 - taper(th) * k ** 1.6)


def taper(th):
    """sides hang (light taper), the back keeps its round inward curl (more taper, curved)."""
    return TAPER + 0.21 * smooth01((abs(th) - 110) / 50.0)


R_REF = {}
for t2 in range(0, 181):                                   # reference radius at Z_REF per degree, smoothed
    for sgn in (1, -1):
        R_REF[sgn * t2] = rho_old(sgn * max(t2, 80), Z_REF)
R_SM = {}
for k in R_REF:
    vals = [R_REF[k + d] for d in range(-4, 5) if (k + d) in R_REF and R_REF[k + d] is not None]
    R_SM[k] = sum(vals) / len(vals) if vals else None


def r_ref(th):
    k = int(round(th)); k = max(-180, min(180, k))
    if R_SM.get(k) is not None:
        return R_SM[k]
    near = [k2 for k2, v in R_SM.items() if v is not None and (k2 > 0) == (k > 0)]
    return R_SM[min(near, key=lambda k2: abs(k2 - k))] if near else None


def new_pos(p, thickness):
    th = theta_of(p)
    if p.z >= Z_REF:
        return None
    rr = r_ref(th)
    if rr is None:
        return None
    c = smooth01((Z_END + CURL_H - p.z) / CURL_H)
    rho = rr * profile(th, p.z) - CURL * c * c
    return Vector((0, H.AX_Y, p.z)) + dirv(th) * (rho - thickness)


moved, dmax = 0, 0.0
for me, is_vol in ((vol.data, True), (ref.data, False)):
    newco = []
    for v in me.vertices:
        t = 0.0
        if is_vol and v.co.z < Z_REF:
            ro = rho_old(theta_of(v.co), v.co.z)
            rv = Vector((v.co.x, v.co.y - H.AX_Y, 0)).length
            t = min(0.0125, max(0.0, ro - rv)) if ro is not None else 0.0
        newco.append(new_pos(v.co, t))
    for v, q in zip(me.vertices, newco):
        if q is not None:
            d = (q - v.co).length
            v.co = q
            if is_vol and d > 1e-6:
                moved += 1; dmax = max(dmax, d)
    me.update()
bmr.free()
cut = 0
for me in (vol.data, ref.data):
    bm = bmesh.new(); bm.from_mesh(me)
    def in_cut(p):
        return p.z < CUT_Z and abs(theta_of(p)) < CUT_TH
    dead = [f for f in bm.faces if any(in_cut(v.co) for v in f.verts)]          # any corner in the cut
    if me is vol.data:
        cut = len(dead)
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me); bm.free(); me.update()

# ------------------------------------------------------------------ 2. side layers: temple layer + outer layer
for n in ("hair_bob_01__Side_L", "hair_bob_01__Side_R"):
    o = bpy.data.objects[n]; me = o.data
    bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
bmr = bmesh.new(); bmr.from_mesh(ref.data)
VOL = H.bvh_of_bmesh(bmr); bmr.free()
HEAD = H.bvh_of(["Blockout_Head"]); EARS = H.bvh_of(["Face_Ear.L", "Face_Ear.R"]); NECK = H.bvh_of(["Blockout_Neck"])
# front edge of the temple layer, character left (deg from the front) by height: covers the temple, the upper half and
# the back of the ear (ear: z 1.329..1.396, theta 82..100), leaves the front lower half open, then follows the jaw
TF = [(1.172, 87), (1.22, 86), (1.255, 86), (1.28, 85), (1.30, 86), (1.32, 88), (1.335, 91), (1.35, 88), (1.36, 80),
      (1.375, 72), (1.39, 68), (1.42, 62), (1.46, 56), (1.50, 50)]
Z_TOP, Z_BOT = 1.50, 1.172


def base_rho(th, z):
    c = []
    for bvh, off in ((VOL, 0.007), (HEAD, 0.007), (EARS, 0.005), (NECK, 0.03)):
        r = rho_on(bvh, th, z)
        if r is not None:
            c.append(r + off)
    return max(c) if c else 0.12


def floor_rho(th, z):
    c = []
    for bvh, off in ((VOL, 0.002), (HEAD, 0.005), (EARS, 0.004), (NECK, 0.02)):
        r = rho_on(bvh, th, z)
        if r is not None:
            c.append(r + off)
    return max(c) if c else 0.0


def low_rho(th, z, u):
    """Below the ear: from ~3.5 cm off the cheek / jaw (front edge) to the volume (back edge); under the jaw it keeps
    the jaw-line radius, so it hangs instead of turning in under the chin."""
    zj = max(z, 1.255)
    h = rho_on(HEAD, th, zj); e = rho_on(EARS, th, z)
    r_in = max(0.11, (h + 0.035) if h is not None else 0.0, (e + 0.005) if e is not None else 0.0)
    tb = math.copysign(max(abs(th), CUT_TH + 1), th)
    if z < Z_REF:                                        # same analytic hanging profile as the volume (no ray jitter)
        cc = smooth01((Z_END + CURL_H - z) / CURL_H)
        r_out = r_ref(tb) * profile(tb, z) - CURL * cc * cc + 0.007
    else:
        r_out = rho_on(VOL, tb, z)
        r_out = (r_out + 0.007) if r_out is not None else base_rho(th, z)
    c = smooth01((Z_BOT + 0.02 - z) / 0.02)
    return r_in + (r_out - r_in) * u ** 0.4 - 0.010 * c * c


def temple_layer(bm, uvl, cl, sign, skew, rand, nr=36, nc=10, ear_top=0.0):
    grid = []
    for r in range(nr):
        t = r / (nr - 1); z = Z_TOP + (Z_BOT - Z_TOP) * t
        a = H.table(TF, z) + skew + ear_top * ear_top_bump(z)
        b = min(120.0 + skew, max(a + 34, H.table(H.OPEN, z) + 10))      # little overlap with the outer layer
        k = max(0.0, (t - 0.70) / 0.30); k = k * k * (3 - 2 * k)
        q = min(1.0, t / 0.18); q = q * q * (3 - 2 * q)
        cth = (a + b) / 2; h = (b - a) / 2 * (1 - 0.55 * k) * (0.45 + 0.55 * q)
        row = []
        for j in range(nc):
            th = sign * (cth - h + 2 * h * j / (nc - 1))
            w = smooth01((z - 1.33) / 0.03)                       # 1 at / above the ear, 0 below it
            rho = base_rho(th, z) * w + low_rho(th, z, j / (nc - 1)) * (1 - w)
            row.append([th, z, rho, q])
        grid.append(row)
    floor = [[floor_rho(th, z) for th, z, _, _ in row] for row in grid]
    for _ in range(40):            # drape: smooth the radius field, never below the clearance floor (rises over the ear)
        new = [[g[2] for g in row] for row in grid]
        for r in range(nr):
            for j in range(nc):
                nb = [grid[r2][j2][2] for r2, j2 in ((r - 1, j), (r + 1, j), (r, j - 1), (r, j + 1)) if 0 <= r2 < nr and 0 <= j2 < nc]
                new[r][j] = max(floor[r][j], (grid[r][j][2] * 2 + sum(nb)) / (2 + len(nb)))
        for r in range(nr):
            for j in range(nc):
                grid[r][j][2] = new[r][j]
    vs = []
    for r, row in enumerate(grid):
        vr = []
        for j, (th, z, rho, q) in enumerate(row):
            fl = floor[r][j]
            rho = fl + (max(rho, fl) - fl) * (0.35 + 0.65 * q)               # root lies flush
            vr.append(bm.verts.new(Vector((0, H.AX_Y, z)) + dirv(th) * rho))
        vs.append(vr)
    for r in range(nr - 1):
        for j in range(nc - 1):
            f = bm.faces.new((vs[r][j], vs[r][j + 1], vs[r + 1][j + 1], vs[r + 1][j]))
            for loop, (jj, rr) in zip(f.loops, [(j, r), (j + 1, r), (j + 1, r + 1), (j, r + 1)]):
                loop[uvl].uv = (jj / (nc - 1), rr / (nr - 1)); loop[cl] = (1.0, rand, rr / (nr - 1), 1.0)


OUTER_LAYER = (lambda z: 112.0, lambda z: 150.0, 1.50, 1.180, lambda t: 0.003 - 0.001 * t)
SKEW = {"L": 0.0, "R": 2.0}
# the r30 bang lock A already hides more of the right ear; on the left the layer reaches a little further over the top
# front of the ear (3/4 view) without closing the lower half seen from the side
EAR_TOP = {"L": -6.0, "R": 0.0}


def ear_top_bump(z):
    return max(0.0, 1.0 - abs(z - 1.367) / 0.022)          # the r30 bang lock A already hides more of the right ear
sides = []
for side, sign in (("L", 1), ("R", -1)):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
    temple_layer(bm, uvl, cl, sign, SKEW[side], rng.random(), ear_top=EAR_TOP[side])
    ta, tb, zt, zb, off = OUTER_LAYER; sk = SKEW[side] + (0 if side == "L" else 1.0)
    if sign > 0:
        a, b = (lambda z: ta(z) + sk), (lambda z: tb(z) + sk)
    else:
        a, b = (lambda z: -(tb(z) + sk)), (lambda z: -(ta(z) + sk))
    H.layer_on_volume(bm, uvl, cl, VOL, a, b, zt, zb, off, rng.random())
    H.orient_outward(bm)
    o = H.mesh_object(f"hair_bob_01__Side_{side}", bm, coll)
    H.apply_solidify(o, 0.003, -1.0, True)
    o.data.materials.append(bpy.data.materials["M_hair_bob_01_01"])
    sides.append(o)

names = ["hair_bob_01__Volume", "hair_bob_01__Bangs"] + [o.name for o in sides]
H.bake_ao([bpy.data.objects[n] for n in names], names + ["Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
for o in sides:
    H.add_outline(o, 0.0008)

stats = dict(volume_vertices_moved=moved, volume_max_shift_m=round(dmax, 4), volume_faces_cut=cut,
             objects={n: dict(verts=len(bpy.data.objects[n].data.vertices),
                              tris=sum(len(p.vertices) - 2 for p in bpy.data.objects[n].data.polygons)) for n in names})
json.dump(stats, open(os.path.join(H.EXP, "spec", "hair_v5e_stats.json"), "w"), indent=1)
print("V5E", json.dumps(stats))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5e_fix.blend"))
print("V5E_OK")
