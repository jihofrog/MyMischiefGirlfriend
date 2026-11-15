"""ToonTest_01 step 5 (Blender, background): shared shape changes for the style comparison, saved as v3.

usage: Blender -b <Experiments/ToonTest_01/MG_ToonTest_01_v2.blend> --python t05_jaw_shapekeys.py
- Jaw: the head blockout's lower face narrowed toward the r30 width profile (V-shaped chin, r30_face_spec.json
  face_width_px), only scaling vertices toward the centre line, blended by height.
- Shape keys (feasibility): Blink (eye whites / iris / pupil / highlight squashed to the lower lid line, upper lid and
  lashes moved down), Smile (mouth corners up, lower half of the eyes pushed up = happy squint), MouthOpen (the
  existing open-mouth meshes: basis flattened to the mouth line, key = the modelled open mouth).
Writes MG_ToonTest_01_v3.blend (v2 stays as it is).
"""
import json
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
H, CHIN = FIT["head_h"], FIT["chin_z"]


def smooth(e):
    e = max(0.0, min(1.0, e))
    return e * e * (3 - 2 * e)


# ---------------- jaw
head = bpy.data.objects["Blockout_Head"]
dg = bpy.context.evaluated_depsgraph_get()
ev = head.evaluated_get(dg); me = ev.to_mesh()
pts = [ev.matrix_world @ v.co for v in me.vertices]
ev.to_mesh_clear()
cy = sum(p.y for p in pts) / len(pts)
def width_at(h):
    z = CHIN + h * H
    row = [p for p in pts if abs(p.z - z) < 0.006 and p.y < cy]
    return (max(p.x for p in row) - min(p.x for p in row)) if len(row) > 3 else None
target = {round((SPEC["chin_y"] - int(y)) / SPEC["head_height_px"], 3): w / SPEC["head_height_px"] for y, w in SPEC["face_width_px"].items()}
prof = []
for h, tw in sorted(target.items()):
    cw = width_at(h)
    if cw:
        prof.append((h, min(1.0, tw * H / cw)))
print("JAW profile (h, factor):", [(round(a, 3), round(b, 3)) for a, b in prof])
hs = [p[0] for p in prof]; fs = [p[1] for p in prof]
def factor(h):
    if h <= hs[0]:
        return fs[0]
    if h >= hs[-1]:
        return 1.0
    for i in range(len(hs) - 1):
        if hs[i] <= h <= hs[i + 1]:
            t = (h - hs[i]) / (hs[i + 1] - hs[i]); return fs[i] * (1 - t) + fs[i + 1] * t
    return 1.0
mw = head.matrix_world; mi = mw.inverted()
cx_world = 0.0
for v in head.data.vertices:
    p = mw @ v.co
    h = (p.z - CHIN) / H
    f = factor(h)
    front = smooth((cy - p.y) / 0.05 + 0.5)                 # full effect on the face side, fades toward the back
    f = 1 - (1 - f) * front * smooth((0.42 - h) / 0.12)     # nothing above the cheekbones
    p.x = cx_world + (p.x - cx_world) * f
    v.co = mi @ p
head.data.update()

# ---------------- shape keys
def add_keys(o, names):
    if not o.data.shape_keys:
        o.shape_key_add(name="Basis", from_mix=False)
    return [o.shape_key_add(name=n, from_mix=False) for n in names]

def local_rows(o):
    zs = [v.co.z for v in o.data.vertices]
    return min(zs), max(zs)

for s in "LR":
    for n in (f"Eye_White.{s}", f"Eye_Iris.{s}", f"Eye_Pupil.{s}", f"Eye_Highlight.{s}"):
        o = bpy.data.objects.get(n)
        if not o or o.type != "MESH":
            continue
        z0, z1 = local_rows(o)
        if n.startswith("Eye_White"):
            ref0, ref1 = z0, z1
        blink, smile = add_keys(o, ["Blink", "Smile"])
        for i, v in enumerate(o.data.vertices):
            zl = z0 + (z1 - z0) * 0.12
            blink.data[i].co.z = zl + (v.co.z - zl) * 0.04
            smile.data[i].co.z = max(v.co.z, z0 + (z1 - z0) * 0.38)
    for n in (f"Eye_UpperLid.{s}", f"Eye_UpperLashes.{s}", f"Face_UpperLashes.{s}", f"Eye_OuterLine.{s}"):
        o = bpy.data.objects.get(n)
        if not o or o.type != "MESH":
            continue
        w = bpy.data.objects[f"Eye_White.{s}"]
        wz0, wz1 = local_rows(w)
        drop = (wz1 - wz0) * 0.80
        (blink,) = add_keys(o, ["Blink"])
        for i, v in enumerate(o.data.vertices):
            blink.data[i].co.z = v.co.z - drop
mouth = bpy.data.objects.get("TT_Mouth_Closed")
if mouth:
    (sm,) = add_keys(mouth, ["Smile"])
    xs = [v.co.x for v in mouth.data.vertices]; xm = max(abs(x) for x in xs)
    for i, v in enumerate(mouth.data.vertices):
        t = abs(v.co.x) / xm
        sm.data[i].co.z = v.co.z + 0.0035 * t ** 2
for o in bpy.data.objects:
    if o.name.startswith("Face_Mouth_Smile") and o.type == "MESH":
        z0, z1 = local_rows(o); zc = (z0 + z1) / 2
        orig = [v.co.copy() for v in o.data.vertices]
        if not o.data.shape_keys:
            o.shape_key_add(name="Basis", from_mix=False)
        k = o.shape_key_add(name="MouthOpen", from_mix=False)
        basis = o.data.shape_keys.key_blocks["Basis"]
        for i, v in enumerate(orig):
            basis.data[i].co = Vector((v.x * 0.6, v.y, zc + (v.z - zc) * 0.05))
            k.data[i].co = v
for o in bpy.data.objects:                       # new keys start at 1.0 in Blender 5.x: save the neutral face
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v3.blend"))
print("V3_OK")
