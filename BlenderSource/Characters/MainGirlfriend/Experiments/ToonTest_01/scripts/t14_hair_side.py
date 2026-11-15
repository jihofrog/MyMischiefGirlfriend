"""ToonTest_01 step 14 / stage D, sides only (Blender, background): large side layers on the hair_bob_01 v2 volume.

usage: Blender -b <MG_ToonTest_01_v5c_bangs.blend> --python t14_hair_side.py
Writes MG_ToonTest_01_v5d_side.blend (v5c untouched). Back layers are not made yet.

Per side, two wide thin layers (3 mm) lying on the volume's outer surface:
  front layer   from the volume's front edge back ~30 deg: behind the ear at ear height, wrapping the jaw below it
  outer layer   behind the ear, 112..150 deg
Both end in rounded, narrowing tips at the bob ends. With bang clump A / D (in front of the cheeks) that makes three
large pieces per side. Slightly different angles left / right (the r30 drawing is not symmetric).
"""
import os
import random
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(H.EXP)
rng = random.Random(13)
coll = bpy.data.collections[H.COLL]

vol_ref = bpy.data.objects["hair_bob_01__Volume_outer_ref"]
bmv = bmesh.new(); bmv.from_mesh(vol_ref.data); bmv.transform(vol_ref.matrix_world)
vol_bvh = H.bvh_of_bmesh(bmv)
o_front = lambda z: H.table(H.OPEN, z)
LAYERS = {   # name: (th_a(z), th_b(z), z_top, z_bot, offset(t)) for the character-left side (+theta)
    "front": (lambda z: o_front(z) + 1.5, lambda z: o_front(z) + 30, 1.47, 1.172, lambda t: 0.0045 - 0.0015 * t),
    "outer": (lambda z: 112.0, lambda z: 150.0, 1.50, 1.180, lambda t: 0.003 - 0.001 * t),
}
SKEW = {"L": 0.0, "R": 3.0}          # character right a little further back
objs = []
for side, sign in (("L", 1), ("R", -1)):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap"); cl = bm.loops.layers.color.new("Col")
    for name, (ta, tb, zt, zb, off) in LAYERS.items():
        sk = SKEW[side]
        if sign > 0:
            a, b = (lambda z, f=ta: f(z) + sk), (lambda z, f=tb: f(z) + sk)
        else:
            a, b = (lambda z, f=tb: -(f(z) + sk)), (lambda z, f=ta: -(f(z) + sk))
        H.layer_on_volume(bm, uvl, cl, vol_bvh, a, b, zt, zb, off, rng.random())
    H.orient_outward(bm)
    o = H.mesh_object(f"hair_bob_01__Side_{side}", bm, coll)
    H.apply_solidify(o, 0.003, -1.0, True)
    o.data.materials.append(bpy.data.materials["M_hair_bob_01_01"])
    objs.append(o)

names = ["hair_bob_01__Volume", "hair_bob_01__Bangs"] + [o.name for o in objs]
H.bake_ao([bpy.data.objects[n] for n in names], names + ["Blockout_Head", "Blockout_Neck", "Blockout_Torso", "Face_Ear.L", "Face_Ear.R"])
for o in objs:
    H.add_outline(o, 0.0008)
print("SIDES", {o.name: (len(o.data.vertices), sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in objs})
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H.EXP, "MG_ToonTest_01_v5d_side.blend"))
print("STAGE_D_OK")
