"""ToonTest_01 step 20 (Blender, background, read only): survey of the current 3D eye construction.

usage: Blender -b <MG_ToonTest_01_v5f_finish.blend> --python t20_eye_survey.py
Writes spec/eye_survey.json, renders/eye_survey_<view>.png (eye close-ups, hair hidden, outlines on) and
spec/eye_section_L.json (vertical section through the left eye centre: head surface and eye parts, y = depth).
The .blend is not saved.
  per object      vertices / faces, modifiers (+ targets), shape keys, materials, world bounds
  depth           signed distance of each vertex to the subdivided head surface (mm, + = in front of the skin)
  flatness        PCA: thickness (smallest spread) / size (largest spread)
  side_protrusion how far a part comes out in front of the face profile at the same height (side view, mm)
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:                                   # survey geometry without the outline hulls
    md = o.modifiers.get("TT_Outline") if hasattr(o, "modifiers") else None
    if md:
        md.show_viewport = False
dg.update()


def world_mesh(o):
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    vs = [ev.matrix_world @ v.co for v in me.vertices]
    fs = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return vs, fs


hv, hf = world_mesh(bpy.data.objects["Blockout_Head"])
HEAD = BVHTree.FromPolygons(hv, hf)
names = []
for cn in ("MainGirlfriend_Eyes", "MainGirlfriend_FaceDetails"):
    c = bpy.data.collections.get(cn)
    if c:
        names += [(o.name, cn) for o in c.all_objects]


def face_profile_y(z):
    """front-most skin y at height z over the whole face (side-view profile)."""
    best = None
    for x in np.linspace(-0.12, 0.12, 49):
        h = HEAD.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
        if h[0] is not None:
            best = h[0].y if best is None else min(best, h[0].y)
    return best


prof_cache = {}
out = {"objects": {}}
for n, cn in names:
    o = bpy.data.objects[n]
    info = dict(collection=cn, type=o.type, hide_render=o.hide_render,
                modifiers=[(m.type, getattr(getattr(m, "target", None), "name", None)) for m in getattr(o, "modifiers", [])
                           if m.name != "TT_Outline"],
                materials=[s.material.name for s in o.material_slots if s.material])
    if o.type == "MESH":
        me = o.data
        info["verts"], info["faces"] = len(me.vertices), len(me.polygons)
        info["shape_keys"] = [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []
        vs, _ = world_mesh(o)
        P = np.array([tuple(v) for v in vs])
        info["bounds"] = [P.min(0).round(4).tolist(), P.max(0).round(4).tolist()]
        sd = []
        for v in vs:
            loc, nrm, _, dist = HEAD.find_nearest(v, 0.2)
            if loc is not None:
                sd.append(dist * (1 if (v - loc).dot(nrm) >= 0 else -1) * 1000)
        if sd:
            info["depth_mm"] = dict(min=round(min(sd), 2), median=round(float(np.median(sd)), 2), max=round(max(sd), 2))
        ev = np.linalg.svd(P - P.mean(0), full_matrices=False)[1] / math.sqrt(max(1, len(P)))
        info["flatness"] = round(float(ev[-1] / max(ev[0], 1e-9)), 4)
        prot = []
        for v in vs[:: max(1, len(vs) // 60)]:
            k = round(v.z, 3)
            if k not in prof_cache:
                prof_cache[k] = face_profile_y(v.z)
            if prof_cache[k] is not None:
                prot.append((prof_cache[k] - v.y) * 1000)
        if prot:
            info["side_protrusion_mm_max"] = round(max(prot), 2)
    out["objects"][n] = info

# ------------------------------------------------------------------ section through the left eye
ew = bpy.data.objects.get("Eye_White.L")
vs, _ = world_mesh(ew)
cx = sum(v.x for v in vs) / len(vs); cz = sum(v.z for v in vs) / len(vs)
out["eye_L_centre"] = [round(cx, 4), round(cz, 4)]
sec = {"head": []}
for z in np.linspace(cz - 0.06, cz + 0.06, 121):
    h = HEAD.ray_cast(Vector((cx, -1, z)), Vector((0, 1, 0)), 2)
    if h[0] is not None:
        sec["head"].append((float(h[0].y), float(z)))
for n, _ in names:
    o = bpy.data.objects[n]
    if o.type != "MESH" or o.hide_render or not n.endswith(".L"):
        continue
    pts = [(v.y, v.z) for v in world_mesh(o)[0] if abs(v.x - cx) < 0.004 and abs(v.z - cz) < 0.06]
    if pts:
        sec[n] = pts
out["section_parts"] = sorted(k for k in sec if k != "head")
json.dump(out, open(os.path.join(EXP, "spec", "eye_survey.json"), "w"), indent=1)

json.dump(sec, open(os.path.join(EXP, "spec", "eye_section_L.json"), "w"))          # drawn by t21_eye_section.py

# ------------------------------------------------------------------ close-up renders (hair hidden)
sys.argv = [sys.argv[0], "--", "eye_survey"]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "eye"}
exec(open(p).read().split("FACE = (700")[0], g)
for o in bpy.data.objects:
    if o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip"):
        o.hide_render = True
    md = o.modifiers.get("TT_Outline") if hasattr(o, "modifiers") else None
    if md:
        md.show_viewport = True
for name, yaw in (("front", 0), ("34", 35), ("60", 60), ("side", 90)):
    g["shoot"](name, (600, 300, 1460, 700), yaw, 1.0)
print("EYE_SURVEY", json.dumps({k: {kk: v for kk, v in d.items() if kk in ("verts", "modifiers", "shape_keys", "depth_mm", "flatness", "side_protrusion_mm_max")}
                                 for k, d in out["objects"].items() if "Eye" in k or "Lash" in k or "Brow" in k}))
