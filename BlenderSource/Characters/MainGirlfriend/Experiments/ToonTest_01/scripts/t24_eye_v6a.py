"""ToonTest_01 step 24 (Blender, background): eye method A - the existing eye meshes, only placement / depth / light.

usage: Blender -b MG_ToonTest_01_v5g_temple.blend --python t24_eye_v6a.py
Writes MG_ToonTest_01_v6a_eye.blend and spec/eye_v6a_stats.json (v5g stays as it is). No socket, no new eye parts:
  depth     eye white cap pulled back onto the face: height over the skin d -> 0.5 mm + 0.25 d (centre ~1.6 mm instead
            of ~4.3); lids / lashes / lines keep their height over the white; lower lashes put on the skin (0.45 mm)
  lid       upper lid line given 0.8 mm thickness (Solidify toward the viewer, baked)
  light     eye materials get the same soft sun response as B (0.80 .. 1.0) instead of flat emission
  keys      Blink as before; Smile / EyeSmile: the eye bottom clamped to an arch (highest in the middle) instead of the
            horizontal 38 % line; Surprise; lower lid line converted to a mesh so it follows EyeSmile; brows keyed;
            Shrinkwrap / Solidify baked so the keys reach the FBX (iris / pupil / highlight: at export, t29)
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, kdtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
HEAD = E.bvh_of(["Blockout_Head"])
stats = {}

# curves -> meshes (they get keys and survive the FBX the same way as before)
for s in E.SIDES:
    for n in (f"Eye_LowerLid.{s}", f"Eye_UpperCrease.{s}"):
        o = bpy.data.objects[n]
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.convert(target="MESH")


def skin_y(P):
    return np.array([E.front_hit(HEAD, p[0], p[2])[0] for p in P])


def remap(o, fn):
    mw, mi = o.matrix_world.copy(), o.matrix_world.inverted()
    blocks = list(o.data.shape_keys.key_blocks) if o.data.shape_keys else []
    for kb in blocks:
        P = np.array([tuple(mw @ d.co) for d in kb.data])
        Q = fn(P)
        for d, q in zip(kb.data, Q):
            d.co = mi @ Vector(tuple(q))
    P = np.array([tuple(mw @ v.co) for v in o.data.vertices])
    Q = fn(P)
    for v, q in zip(o.data.vertices, Q):
        v.co = mi @ Vector(tuple(q))
    o.data.update()


# ------------------------------------------------------------------ depth
for s in E.SIDES:
    w = bpy.data.objects[f"Eye_White.{s}"]
    W0 = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
    dW = skin_y(W0) - W0[:, 1]
    ndW = 0.0005 + 0.25 * dW
    kd = kdtree.KDTree(len(W0))
    for i, p in enumerate(W0):
        kd.insert((p[0], 0, p[2]), i)
    kd.balance()

    def white_fn(P):
        ys = skin_y(P)
        return np.stack([P[:, 0], ys - (0.0005 + 0.25 * (ys - P[:, 1])), P[:, 2]], 1)

    def part_fn(P):
        ys = skin_y(P)
        d = ys - P[:, 1]
        out = P.copy()
        for i, p in enumerate(P):
            _, k, dist = kd.find((p[0], 0, p[2]))
            f = float(E.smooth(dist / 0.004))
            nd = (1 - f) * max(0.0003, ndW[k] + d[i] - dW[k]) + f * (0.0004 + 0.25 * d[i])
            out[i, 1] = ys[i] - nd
        return out

    stats[f"white_{s}_before_mm"] = dict(med=round(float(np.median(dW)) * 1000, 2), max=round(float(dW.max()) * 1000, 2))
    remap(w, white_fn)
    W1 = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
    d1 = skin_y(W1) - W1[:, 1]
    stats[f"white_{s}_after_mm"] = dict(med=round(float(np.median(d1)) * 1000, 2), max=round(float(d1.max()) * 1000, 2))
    for n in (f"Eye_UpperLid.{s}", f"Eye_UpperLashes.{s}", f"Face_UpperLashes.{s}", f"Eye_OuterLine.{s}",
              f"Eye_UpperCrease.{s}", f"Eye_LowerLid.{s}"):
        remap(bpy.data.objects[n], part_fn)
    remap(bpy.data.objects[f"Face_LowerLashes.{s}"], lambda P: np.stack([P[:, 0], skin_y(P) - 0.00045, P[:, 2]], 1))
    lid = bpy.data.objects[f"Eye_UpperLid.{s}"]
    md = lid.modifiers.new("v6a_LidThickness", "SOLIDIFY")
    md.thickness = 0.0008
    md.offset = -1.0 if lid.data.polygons[0].normal.y > 0 else 1.0

# ------------------------------------------------------------------ light
for mn in ("TT_MG_Eye_White", "TT_Eye_Iris", "TT_MG_Eye_UpperLid", "TT_MG_Eye_Lash", "TT_MG_Face_Lash",
           "TT_MG_Face_LowerLash", "TT_MG_Eye_OuterLine", "TT_MG_Eye_LowerLid", "TT_MG_Eye_Crease"):
    m = bpy.data.materials.get(mn)
    if m is not None:
        E.add_light_response(m, (0.80, 0.93, 1.0) if mn in ("TT_MG_Eye_White", "TT_Eye_Iris") else (0.85, 0.95, 1.0))

# ------------------------------------------------------------------ keys
for s in E.SIDES:
    w = bpy.data.objects[f"Eye_White.{s}"]
    W = np.array([tuple(w.matrix_world @ v.co) for v in w.data.vertices])
    z0, z1 = W[:, 2].min(), W[:, 2].max()
    xa, xb = W[:, 0].min(), W[:, 0].max()
    xm, hw, H = (xa + xb) / 2, (xb - xa) / 2, z1 - z0
    zc = (z0 + z1) / 2
    rise = lambda x: np.clip(1 - ((x - xm) / hw) ** 2, 0, 1) ** 0.5
    for n in (f"Eye_White.{s}", f"Eye_Iris.{s}", f"Eye_Pupil.{s}", f"Eye_Highlight.{s}"):
        o = bpy.data.objects[n]
        P = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        for pose, a, b in (("EyeSmile", 0.12, 0.45), ("Smile", 0.08, 0.20)):
            Q = P.copy()
            Q[:, 2] = np.maximum(P[:, 2], z0 + H * (a + b * rise(P[:, 0])))
            E.add_key(o, pose, Q)
        Q = P.copy()
        Q[:, 2] = zc + (P[:, 2] - zc) * 1.06
        E.add_key(o, "Surprise", Q)
    arcu = lambda x: np.clip(1 - ((x - xm) / hw) ** 2, 0, 1) ** 0.6
    for n in (f"Eye_UpperLid.{s}", f"Eye_UpperLashes.{s}", f"Face_UpperLashes.{s}", f"Eye_OuterLine.{s}"):
        o = bpy.data.objects[n]
        P = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        for pose, k in (("EyeSmile", 0.10), ("Smile", 0.04)):
            Q = P.copy()
            Q[:, 2] -= k * H * arcu(P[:, 0])
            E.add_key(o, pose, Q)
        Q = P.copy()
        Q[:, 2] += 0.0018
        E.add_key(o, "Surprise", Q)
    for n in (f"Eye_LowerLid.{s}", f"Face_LowerLashes.{s}"):
        o = bpy.data.objects[n]
        P = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        for pose, a, b in (("EyeSmile", 0.12, 0.45), ("Smile", 0.08, 0.20)):
            Q = P.copy()
            Q[:, 2] = np.maximum(P[:, 2], z0 + H * (a + b * rise(P[:, 0])) - 0.0006)
            Q[:, 1] = skin_y(Q) - (skin_y(P) - P[:, 1])
            E.add_key(o, pose, Q)

# iris / pupil / highlight keep their Shrinkwrap onto the white (the gaze slides them over it, as in v5g); the FBX
# export bakes them (t29), where the gaze then becomes a plain move of the iris
fd = [o for c in ("MainGirlfriend_FaceDetails", "MainGirlfriend_Eyes") for o in bpy.data.collections[c].all_objects
      if o.type == "MESH" and any(m.type in ("SHRINKWRAP", "SOLIDIFY") and m.name != "TT_Outline" for m in o.modifiers)
      and not o.name.startswith(("Eye_Iris", "Eye_Pupil", "Eye_Highlight"))]
stats["baked"] = E.bake_modifiers_with_keys(fd)
E.brow_keys(HEAD)
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
eyes = [o for c in ("MainGirlfriend_Eyes",) for o in bpy.data.collections[c].all_objects if o.type == "MESH" and not o.hide_render]
eyes += [bpy.data.objects[f"Face_{k}Lashes.{s}"] for k in ("Upper", "Lower") for s in E.SIDES]
stats["tris"] = {o.name: E.tri_count(o) for o in eyes}
json.dump(stats, open(os.path.join(EXP, "spec", "eye_v6a_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v6a_eye.blend"))
print("V6A_OK", json.dumps(stats))
