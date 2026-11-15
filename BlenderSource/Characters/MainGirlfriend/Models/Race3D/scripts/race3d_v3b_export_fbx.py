"""Race3D v3b expressions (Blender, background, the .blend is not saved): FBX for the Unity experiment only.

usage: Blender -b Models/Race3D/experiments/MainGirlfriend_Race3D_v3b_Expressions.blend --python race3d_v3b_export_fbx.py -- <out.fbx>
Same rules as race3d_v1_export_fbx.py (Experiments/ToonTest_01/scripts/t29_eye_export_fbx.py unchanged), plus the
expression meshes that the renders switch on per state (tear bead, tear stream, open mouths, brow cards) and every shape
key value at 0. Also writes Models/Race3D/spec/race3d_v3b_unity_proj.json: the eyeball projection (su, tu, sv, tv) and
the iris centre (uc, vc) per eye for the iris scale / pitch of the Unity driver.
"""
import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
assert os.path.basename(bpy.data.filepath) == "MainGirlfriend_Race3D_v3b_Expressions.blend", bpy.data.filepath
T29 = os.path.abspath(os.path.join(HERE, "..", "..", "..", "Experiments", "ToonTest_01", "scripts", "t29_eye_export_fbx.py"))
sys.path.insert(0, os.path.dirname(T29))
import eye_v6_common as E  # noqa: E402

O = bpy.data.objects
proj = {}
for s in E.SIDES:
    ob = O[f"Eye_Ball.{s}"]
    nt = ob.material_slots[0].material.node_tree
    nodes = {l.from_socket.name: l.to_node for l in nt.links
             if l.from_node.type == "SEPXYZ" and l.to_node.type == "MATH" and l.to_node.operation == "MULTIPLY_ADD"}
    su, tu = nodes["X"].inputs[1].default_value, nodes["X"].inputs[2].default_value
    sv, tv = nodes["Z"].inputs[1].default_value, nodes["Z"].inputs[2].default_value
    ib = E.TGT[s]["iris_bbox"]
    c = ob.matrix_world.inverted() @ Vector((float(E.X((ib[0] + ib[2]) / 2)), 0.0, float(E.Z((ib[1] + ib[3]) / 2))))
    proj[s] = dict(su=su, tu=tu, sv=sv, tv=tv, uc=c.x * su + tu, vc=c.z * sv + tv)
json.dump(proj, open(os.path.join(os.path.dirname(HERE), "spec", "race3d_v3b_unity_proj.json"), "w"), indent=1)

for o in O:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks:
            k.value = 0.0
    if o.name.startswith(("Face_Tear", "Face_Mouth_Ex", "Face_BrowCard")):
        o.hide_render = False
        o.hide_set(False)
for o in O:
    if o.name.startswith("Face_Mouth_Smile") and o.type == "MESH":
        o.hide_render = False

src = open(T29).read()
old = "assert os.path.abspath(bpy.data.filepath).startswith(E.EXP)"
assert old in src
src = src.replace(old, "pass")
g = {"__file__": T29, "__name__": "__main__"}
exec(compile(src, T29, "exec"), g)
print("PROJ", json.dumps(proj))
