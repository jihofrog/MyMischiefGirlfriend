"""ToonTest_01 step 12 / stage A (Blender, background): hair_bob_01 v2 base volume, shaped from the r30 silhouette.

usage: Blender -b <MG_ToonTest_01_v4_hair.blend> --python t12_hair_volume.py
Writes MG_ToonTest_01_v5a_volume.blend (v4 untouched). In the new file the 38-strand version is kept for comparison as
collection hair_bob_01_s38 (objects / meshes / materials renamed *_s38, excluded from the view layer).

The volume is one shell around the head, open over the face:
  - each horizontal section is a superellipse around the hair axis: side half-width = r30 hair width at that height
    (per side, smoothed), back depth = head + 2..3 cm (round, not puffed), the bob tips curl in under the jaw and nape
    (the front part of the section shrinks toward the neck below the jaw);
  - near the face it never comes closer than 3 mm to the head (smooth max with the head surface);
  - the front opening follows the hairline: closed above the forehead, behind the ears at ear height, then wrapping
    forward under the ears toward the jaw;
  - 12 mm real thickness thinning to 2 mm at the tips (inner surface visible under the chin), brown inverted-hull outline.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(H.EXP)

# ------------------------------------------------------------------ keep the 38-strand version, out of the way
old = bpy.data.collections.get(H.COLL)
old.name = H.COLL + "_s38"
acc = bpy.data.collections.new("acc_head_hairclip_x_01"); bpy.context.scene.collection.children.link(acc)
for n in ("acc_head_hairclip_x_01", "Socket_acc_head"):           # the clip is its own item: kept, not renamed
    o = bpy.data.objects[n]; acc.objects.link(o); old.objects.unlink(o)
for o in list(old.all_objects):
    o.name = o.name + "_s38"
    if o.data is not None:
        o.data.name = o.data.name + "_s38"
for c in old.children:
    c.name = c.name + "_s38"
for n in ("M_hair_bob_01_01", "M_hair_bob_01_02"):
    if bpy.data.materials.get(n):
        bpy.data.materials[n].name = n + "_s38"
bpy.context.view_layer.layer_collection.children[old.name].exclude = True
clip = bpy.data.objects.get("acc_head_hairclip_x_01")
if clip:
    clip.hide_render = True; clip.hide_viewport = True               # re-placed on the new bangs in stage C

coll = bpy.data.collections.new(H.COLL); bpy.context.scene.collection.children.link(coll)

# ------------------------------------------------------------------ section shape
rows = sorted((H.py_z(int(y)), H.px_x(v[0]), H.px_x(v[1])) for y, v in H.TGT["union_rows"].items())


def smooth(vals, w):
    out = []
    for i in range(len(vals)):
        a, b = max(0, i - w), min(len(vals), i + w + 1)
        out.append(sum(vals[a:b]) / (b - a))
    return out


ZS = [r[0] for r in rows]
A_R = list(zip(ZS, smooth([-r[1] for r in rows], 16)))  # character right = -X = r30 screen left; 64 px window
A_L = list(zip(ZS, smooth([r[2] for r in rows], 16)))   # (strand tips in the drawing are not the bob silhouette)
Z_LO, Z_HI = ZS[0], ZS[-1]
BACK = [(1.17, 0.090), (1.185, 0.110), (1.20, 0.128), (1.22, 0.145), (1.25, 0.163), (1.30, 0.178), (1.35, 0.186),
        (1.40, 0.190), (1.45, 0.192), (1.50, 0.184), (1.55, 0.162), (1.575, 0.140), (1.60, 0.112), (1.62, 0.085),
        (1.64, 0.045), (1.655, 0.0)]
FRONT = [(1.10, 0.06), (1.20, 0.07), (1.24, 0.09), (1.30, 0.10), (1.36, 0.12), (1.42, 0.14), (1.55, 0.14), (1.60, 0.11), (1.64, 0.05), (1.655, 0.0)]
OPEN = H.OPEN
P_FRONT, P_BACK = 2.3, 2.0
D_MIN, K_SMAX = 0.003, 0.008


def rho_env(th, z):
    if z < Z_LO or z > Z_HI:
        return 0.0
    a = H.table(A_L if th > 0 else A_R, z)
    c = H.table(FRONT, z) if abs(th) <= 90 else (H.table(BACK, z) if z >= BACK[0][0] else 0.0)
    if a <= 0 or c <= 0:
        return 0.0
    t = math.radians(th); P = P_FRONT if abs(th) <= 90 else P_BACK
    return 1.0 / ((abs(math.sin(t)) / a) ** P + (abs(math.cos(t)) / c) ** P) ** (1.0 / P)


HEAD = H.bvh_of(["Blockout_Head"])                       # ears stay in front of the hair (opening edge behind them)


def r_env(th, ph):
    d = H.polar_dir(th, ph); s = math.sqrt(d.x * d.x + d.y * d.y)
    f = lambda t: t * s - rho_env(th, H.HC.z + t * d.z)
    t, step = 0.6, 0.004
    while t > 0 and f(t) >= 0:
        t -= step
    if t <= 0:
        return 0.0
    lo, hi = t, t + step
    for _ in range(18):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def r_head(th, ph):
    d = H.polar_dir(th, ph)
    hit = HEAD.ray_cast(H.HC, d, 1.0)
    return 0.0 if hit[0] is None else hit[3]


def point(th, ph):
    R = H.smax(r_head(th, ph) + D_MIN, r_env(th, ph), K_SMAX)
    return H.HC + H.polar_dir(th, ph) * R


def z_tip(th):
    return 1.166 + 0.034 * max(0.0, -math.cos(math.radians(th))) ** 2


def phi_tip(th):
    lo, hi = 95.0, 176.0
    zt = z_tip(th)
    for _ in range(22):
        mid = (lo + hi) / 2
        if point(th, mid).z > zt:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


STEP, NR = 5.0, 48                                   # fixed meridians every 5 deg; rows by polar angle
_tip = {}


def phi_tip_c(th):
    k = round(th * 2) / 2
    if k not in _tip:
        _tip[k] = phi_tip(k)
    return _tip[k]


def around(t):                                       # 0 .. 360 from the front through the character's left
    return t if t <= 180 else t - 360


# one opening angle per row (taken on the side meridian); each row keeps the fixed meridians outside the opening
# plus one exact edge point on each side, and neighbouring rows are zipped together in angle order
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
pole = bm.verts.new(point(0, 0))
rows_v = [[(0.0, pole), (360.0, pole)]]
for i in range(1, NR + 1):
    s_ = i / NR
    o = H.table(OPEN, point(90, phi_tip_c(90) * s_).z)
    ts = [o] + [k * STEP for k in range(1, int(360 / STEP)) if o + 0.6 * STEP < k * STEP < 360 - o - 0.6 * STEP] + [360 - o]
    rows_v.append([(t, bm.verts.new(point(around(t), phi_tip_c(around(t)) * s_))) for t in ts])
faces = []


def tri(a, b, c, va, vb, vc):
    if len({a[1], b[1], c[1]}) < 3:
        return
    try:
        f = bm.faces.new((a[1], b[1], c[1]))
    except ValueError:
        return
    faces.append((f, [(a[0] / 360, va), (b[0] / 360, vb), (c[0] / 360, vc)]))


for i in range(NR):
    A, B = rows_v[i], rows_v[i + 1]; va, vb = i / NR, (i + 1) / NR
    ia = ib = 0
    while ia < len(A) - 1 or ib < len(B) - 1:
        if ia < len(A) - 1 and (ib == len(B) - 1 or A[ia + 1][0] <= B[ib + 1][0]):
            tri(A[ia], B[ib], A[ia + 1], va, vb, va); ia += 1
        else:
            tri(A[ia], B[ib], B[ib + 1], va, vb, vb); ib += 1
for f, uvs in faces:
    for loop, (u, v) in zip(f.loops, uvs):
        loop[uvl].uv = (u, v); loop[cl] = (1.0, 0.5, v, 1.0)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=2e-4)          # front seam above the hairline
H.orient_outward(bm)
outer = bm.copy()
vol = H.mesh_object("hair_bob_01__Volume", bm, coll)
vg = vol.vertex_groups.new(name="Thickness")                        # 12 mm, thinning to 2 mm at the bob tips
v_of = {}
for loop in vol.data.loops:
    v_of[loop.vertex_index] = vol.data.uv_layers["UVMap"].data[loop.index].uv[1]
for vi, v in v_of.items():
    k = min(1.0, max(0.0, (v - 0.82) / 0.18))
    vg.add([vi], 1.0 - 0.83 * k * k * (3 - 2 * k), "REPLACE")
H.apply_solidify(vol, 0.012, -1.0, True, vertex_group="Thickness")
outer_me = bpy.data.meshes.new("hair_bob_01__Volume_outer_ref"); outer.to_mesh(outer_me); outer.free()
ref = bpy.data.objects.new(outer_me.name, outer_me); coll.objects.link(ref); ref.hide_render = True; ref.hide_viewport = True

mat = H.hair_material("M_hair_bob_01_01")
vol.data.materials.append(mat)
H.bake_ao([vol], ["hair_bob_01__Volume", "Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
H.add_outline(vol, 0.0012)

me = vol.data
print("VOLUME verts", len(me.vertices), "tris", sum(len(p.vertices) - 2 for p in me.polygons),
      "z", round(min(v.co.z for v in me.vertices), 3), round(max(v.co.z for v in me.vertices), 3),
      "x", round(min(v.co.x for v in me.vertices), 3), round(max(v.co.x for v in me.vertices), 3),
      "y", round(min(v.co.y for v in me.vertices), 3), round(max(v.co.y for v in me.vertices), 3))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5a_volume.blend"))
print("STAGE_A_OK")
