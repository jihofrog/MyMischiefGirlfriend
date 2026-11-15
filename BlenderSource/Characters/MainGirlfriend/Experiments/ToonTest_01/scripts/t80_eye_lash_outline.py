"""ToonTest_01 step 80 (Blender, background, the .blend is not saved): lash past the face outline on the far eye.

usage: Blender -b <file.blend> --python t80_eye_lash_outline.py -- <tag> [view]
Orthographic rays (t03 camera, no hair, 0.5 px of the x1 render) over the far-eye box at +-25, +-35, +-45; with "view"
the view keys follow the angle (eye_v6_common.view_key_values). A lash hit (band / lower lash, texture alpha > 0.5 at the
hit) counts as "past the outline" when the ray, continued, meets nothing else. Per angle: count, and which band columns
/ rows (and lower-lash vertices) those hits belong to. Writes spec/eye_lash_outline_<tag>.json.
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
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag, view = args[0], "view" in args
O = bpy.data.objects
AXY = 0.03
for o in O:
    if "TT_Outline" in getattr(o, "modifiers", {}):
        o.modifiers["TT_Outline"].show_viewport = False
BOX = json.load(open(os.path.join(E.EXP, "spec", "eye_f6_boxes_v6i.json")))


def lash_alpha(o):
    img = next(nd.image for nd in o.material_slots[0].material.node_tree.nodes if nd.type == "TEX_IMAGE" and nd.image)
    w, h = img.size
    px = np.array(img.pixels[:]).reshape(h, w, 4)
    return px[..., 3], w, h


res = {}
for a in (25, -25, 35, -35, 45, -45):
    s = "R" if a > 0 else "L"
    vw = E.view_key_values(a) if view else {}
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = vw.get(k.name, 0.0)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    V, F, own, names, fidx = [], [], [], [], []
    for o in O:
        if o.type != "MESH" or o.hide_render or o.name.startswith(("hair_bob_01", "acc_head_hairclip", "Face_Blush")):
            continue
        vs, fs = E.world_mesh(o, dg)
        k = len(V)
        V += vs
        F += [tuple(i + k for i in f) for f in fs]
        own += [len(names)] * len(fs)
        fidx += list(range(len(fs)))
        names.append(o.name)
    B = BVHTree.FromPolygons(V, F)
    lash = O[f"Eye_Lash.{s}"]
    li = names.index(lash.name)
    ev = lash.evaluated_get(dg)
    me = ev.to_mesh()
    uvl = me.uv_layers.active.data
    alpha, aw, ah = lash_alpha(lash)
    nb, nr, cs = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"]), int(lash["mmg_crease_start"])
    mw = ev.matrix_world
    t = math.radians(a)
    d = Vector((-math.sin(t), math.cos(t), 0.0))
    x0, y0, x1, y1 = BOX[f"{s}_{a}"]
    cols, rows, lower, past, vis = {}, {}, 0, 0, 0
    for py in np.arange(y0, y1, 0.5):
        z = float(E.Z(py))
        for px in np.arange(x0, x1, 0.5):
            sx = (px - 1030) / E.PPM
            q = Vector((sx * math.cos(t), sx * math.sin(t) + AXY, z)) - d * 3
            while True:
                h = B.ray_cast(q, d, 10)
                if h[0] is None or own[h[2]] != li:
                    break
                # the lash texture: only opaque texels count
                poly = me.polygons[fidx[h[2]]]
                vids = list(poly.vertices)
                P = [mw @ me.vertices[v].co for v in vids]
                ws = np.array([1.0 / max((h[0] - p).length, 1e-7) for p in P])
                ws /= ws.sum()
                uv = sum((w * np.array(uvl[li_].uv) for w, li_ in zip(ws, poly.loop_indices)), np.zeros(2))
                al = alpha[int(np.clip(uv[1], 0, 0.999) * ah), int(np.clip(uv[0], 0, 0.999) * aw)]
                if al <= 0.5:
                    q = h[0] + d * 0.0002
                    continue
                vis += 1
                h2 = B.ray_cast(h[0] + d * 0.0005, d, 10)
                if h2[0] is None:
                    past += 1
                    v = vids[int(np.argmax(ws))]
                    if v < nb * nr:
                        cols[v // nr] = cols.get(v // nr, 0) + 1
                        rows[v % nr] = rows.get(v % nr, 0) + 1
                    elif v < cs:
                        lower += 1
                break
    ev.to_mesh_clear()
    res[f"{s}_{a}"] = dict(lash_visible=vis, lash_past_outline=past, band_cols=dict(sorted(cols.items())),
                           band_rows=dict(sorted(rows.items())), lower_lash=lower, band_cols_total=nb, band_rows_total=nr)
    print("LASH", tag, s, a, vis, past, res[f"{s}_{a}"]["band_cols"], res[f"{s}_{a}"]["band_rows"], lower)
json.dump(res, open(os.path.join(E.EXP, "spec", f"eye_lash_outline_{tag}.json"), "w"), indent=1)
print("LASH_OK", tag)
