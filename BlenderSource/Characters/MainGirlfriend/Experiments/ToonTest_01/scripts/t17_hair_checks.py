"""ToonTest_01 step 17 (Blender, background): checks for a hair_bob_01 v5 file (read only, the .blend is not saved).

usage: Blender -b <MG_ToonTest_01_v5?.blend> --python t17_hair_checks.py -- <tag>
Writes spec/hair_checks_<tag>.json and renders/<tag>_ear_*.png:
  penetration   hair vertices inside head / ears / neck / torso (volume: its outer surface only; the inner shell is
                meant to sit inside the head). Normal test, confirmed by ray parity.
  ends_forward  most forward (-Y) hair point below the chin, and the lowest hair point
  ear_visible   per ear and view (side, 3/4): visible ear pixels with hair / without hair (id renders: hair and clip
                red, ears green, head skin blue)
  head_skin_34  visible head-skin pixels in the 3/4 views (side of the head left open)
  eye_visible   per view: visible eye / lash / brow pixels with hair / without hair (eye parts yellow)
  temple_cover  share of the temple skin patch (theta 50..80 deg, z 1.36..1.50, each side) hidden by hair, per view
                (front, 3/4, side; only patch points the camera can see past the head itself); *_upper: z >= 1.40 only
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hair_v2_common as H  # noqa: E402

assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1]
out = {}

hair = [o for o in bpy.data.collections[H.COLL].objects if o.type == "MESH" and not o.name.endswith("_ref")]
ref = bpy.data.objects["hair_bob_01__Volume_outer_ref"]
BODY = {n: H.bvh_of([n]) for n in ("Blockout_Head", "Face_Ear.L", "Face_Ear.R", "Blockout_Neck", "Blockout_Torso")}
from mathutils import Vector as _V


def inside(bvh, p):
    """ray parity along a few directions (all must agree), for candidates of the normal test"""
    votes = 0
    for d in (_V((1, 0.013, 0.007)), _V((-0.011, 1, 0.017)), _V((0.009, -0.015, 1))):
        d.normalize(); q, n = p.copy(), 0
        for _ in range(64):
            h = bvh.ray_cast(q, d, 2.0)
            if h[0] is None:
                break
            n += 1; q = h[0] + d * 1e-5
        votes += n % 2
    return votes >= 2


pen = {}
for o in hair:
    src = ref if o.name == "hair_bob_01__Volume" else o
    pts = [src.matrix_world @ v.co for v in src.data.vertices]
    res = {}
    for n, bvh in BODY.items():
        c = 0
        for p in pts:
            loc, nrm, _, _ = bvh.find_nearest(p, 0.05)
            if loc is not None and (p - loc).dot(nrm) < -1e-4 and inside(bvh, p):
                c += 1
        res[n] = c
    pen[o.name] = res
out["penetration"] = pen
chin = H.FIT["chin_z"]
below = [o.matrix_world @ v.co for o in hair for v in o.data.vertices if (o.matrix_world @ v.co).z < chin]
out["ends_forward_min_y"] = round(min(p.y for p in below), 4)
out["ends_lowest_z"] = round(min(p.z for p in below), 4)

# id renders
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "checks"}
exec(open(p).read().split("FACE = (700")[0], g)
sc = bpy.context.scene


def flat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = col
    nt.links.new(e.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    return m


RED, GREEN, BLUE = flat("ID_R", (1, 0, 0, 1)), flat("ID_G", (0, 1, 0, 1)), flat("ID_B", (0, 0, 1, 1))
YELLOW = flat("ID_Y", (1, 1, 0, 1))
ids = {o.name: RED for o in hair}
ids["acc_head_hairclip_x_01"] = RED
ids["Face_Ear.L"] = GREEN; ids["Face_Ear.R"] = GREEN; ids["Blockout_Head"] = BLUE
for o in bpy.data.objects:
    if o.type == "MESH" and not o.hide_render and (o.name.startswith("Eye_") or o.name.startswith("Face_Brow")
                                                   or "Lashes" in o.name):
        ids[o.name] = YELLOW
saved = {}
for n, m in ids.items():
    o = bpy.data.objects[n]; saved[n] = [s.material for s in o.material_slots]
    for s in o.material_slots:
        s.material = m
    for md in o.modifiers:
        if md.name == "TT_Outline":
            md.show_render = False
BOX = (480, 0, 1580, 1000)


def count(path, rgb, box=None):
    img = bpy.data.images.load(path); a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[::-1]
    m = (a[..., 3] > 0.5) & (np.abs(a[..., 0] - rgb[0]) < 0.25) & (np.abs(a[..., 1] - rgb[1]) < 0.25) & (np.abs(a[..., 2] - rgb[2]) < 0.25)
    if box:                                                   # box in full-canvas px, image is BOX at half scale
        x0, y0, x1, y1 = [int(round((v - o) * 0.5)) for v, o in zip(box, (BOX[0], BOX[1], BOX[0], BOX[1]))]
        m = m[y0:y1, x0:x1]
    bpy.data.images.remove(img)
    return int(m.sum())


views = {"front": 0, "side_L": 90, "side_R": -90, "34_L": 35, "34_R": -35}
ear = {}
skin = {}
eye = {}

for vname, yaw in views.items():
    g["shoot"](f"ear_{vname}", BOX, yaw, 0.5)
    pth = os.path.join(EXP, "renders", f"{tag}_ear_{vname}.png")
    ear[vname] = {"with_hair": count(pth, (0, 1, 0))}
    eye[vname] = {"with_hair": count(pth, (1, 1, 0))}
    if vname.startswith("34"):
        skin[vname] = count(pth, (0, 0, 1))
    for o in hair + [bpy.data.objects["acc_head_hairclip_x_01"]]:
        o.hide_render = True
    g["shoot"](f"ear_{vname}_nohair", BOX, yaw, 0.5)
    pth2 = os.path.join(EXP, "renders", f"{tag}_ear_{vname}_nohair.png")
    ear[vname]["no_hair"] = count(pth2, (0, 1, 0))
    ear[vname]["visible_share"] = round(ear[vname]["with_hair"] / max(1, ear[vname]["no_hair"]), 3)
    eye[vname]["no_hair"] = count(pth2, (1, 1, 0))
    eye[vname]["visible_share"] = round(eye[vname]["with_hair"] / max(1, eye[vname]["no_hair"]), 3)
    os.remove(pth2)
    for o in hair + [bpy.data.objects["acc_head_hairclip_x_01"]]:
        o.hide_render = False
out["ear_visible"] = ear
out["head_skin_34_px"] = skin
out["eye_visible"] = eye
import math
from mathutils import Vector
HAIRB = H.bvh_of([o.name for o in hair] + ["acc_head_hairclip_x_01"]); HEADB = H.bvh_of(["Blockout_Head", "Face_Ear.L", "Face_Ear.R"])
cover = {}
for side, sg in (("L", 1), ("R", -1)):
    pts = []
    for th in range(50, 81, 2):
        for k in range(29):
            z = 1.36 + 0.005 * k; t = math.radians(sg * th)
            d = Vector((math.sin(t), -math.cos(t), 0)); o = Vector((0, H.AX_Y, z))
            h = HEADB.ray_cast(o + d, -d, 1.0)
            if h[0] is not None:
                pts.append((h[0], h[1]))
    for vname, yaw in (("front", 0), ("34", 35), ("side", 90)):
        t = math.radians(sg * yaw); to_cam = -Vector((-math.sin(t), math.cos(t), 0))
        seen = hid = 0
        for p, n in pts:
            q = p + n * 0.0008
            if HEADB.ray_cast(q, to_cam, 2.0)[0] is not None:
                continue                                       # the head itself is in the way
            seen += 1
            hid += HAIRB.ray_cast(q, to_cam, 2.0)[0] is not None
        cover[f"{vname}_{side}"] = round(hid / max(1, seen), 3)
        up = [(p, n) for p, n in pts if p.z >= 1.40]              # above the outer eye corner (temple proper)
        seen = hid = 0
        for p, n in up:
            q = p + n * 0.0008
            if HEADB.ray_cast(q, to_cam, 2.0)[0] is not None:
                continue
            seen += 1; hid += HAIRB.ray_cast(q, to_cam, 2.0)[0] is not None
        cover[f"{vname}_{side}_upper"] = round(hid / max(1, seen), 3)
out["temple_cover"] = cover
json.dump(out, open(os.path.join(EXP, "spec", f"hair_checks_{tag}.json"), "w"), indent=1)
print("CHECKS", json.dumps(out))
