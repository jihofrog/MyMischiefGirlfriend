"""ToonTest_01 step 32 (Blender, background): v6c = v6b eye structure + clean lashes + A style double-eyelid crease.

usage: Blender -b MG_ToonTest_01_v6b_eye.blend --python t32_eye_v6c.py
Writes MG_ToonTest_01_v6c_eye.blend and spec/eye_v6c_stats.json (v6b stays as it is). Unchanged from v6b: socket,
eyeball, iris picture and gaze, lid sheets, lash band geometry, Blink / EyeSmile / Surprise movements, FBX keys.
  depths   the lash band no longer sinks behind the hidden lid sheet / socket wall, the hidden lid rows stay behind the
           skin, the band sits on its painted front position (fix_depths)
  lashes   Eye_Lash.<s> uses r30/eye_tex_lash_v6c_<s>.png (t31: one clean silhouette, no highlight strokes, no half
           transparent fringe, 1024 px) with a smooth alpha edge (Blender: blended; Unity: alpha to coverage)
  crease   thin strip on the skin (0.25 mm above it) along the painted crease, joined into Eye_Lash.<s> (same material,
           no new draw call). Keys: Blink folds it to nothing (half at Blink 50 %), EyeSmile 0.85 width, Surprise moves
           it up with the lid (90 %) and 1.1 width
  Smile    eye lid part removed from Smile (mouth / cheek / brows only), so Smile + EyeSmile adds up without the lower lid
           passing the upper one
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP) and "v6b" in os.path.basename(bpy.data.filepath)
CR = json.load(open(os.path.join(EXP, "spec", "eye_v6c_crease.json")))
HEAD = E.bvh_of(["Blockout_Head"])
O = bpy.data.objects
stats = {}


def head_point(x, z, lift):
    out = []
    for xx, zz in zip(np.atleast_1d(x), np.atleast_1d(z)):
        y, n = E.front_hit(HEAD, xx, zz)
        out.append((xx, y - lift / max(0.35, abs(n.y)), zz))
    return np.array(out)


def fix_depths(s):
    """the v6b smudge: next to the socket margin the lash band followed the coarse socket wall and sank behind the
    hidden upper lid sheet; at the outer corner the hidden lid rows came out in front of the skin. Per key block:
      lid sheet rows outside the socket margin: never in front of the skin (pushed 0.3 mm behind it)
      lash band rows (not the skirt) and lower lash: never behind max(skin or lid sheet + 0.4 mm, eyeball + 2.2 mm), per
      vertex and per face (centre / edge middles)"""
    sph = E.Spheroid(**json.loads(O[f"Eye_Ball.{s}"]["mmg_spheroid"]))
    poly = E.opening_poly(s)
    lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
    nb = (len(lash.data.vertices) - 36) // 7
    band_idx = np.array([i * 7 + j for i in range(nb) for j in range(1, 7)] + list(range(nb * 7, nb * 7 + 36)))  # + lower lash
    res = {}
    # band front alignment: v6b put the band on the eyeball along the surface normal, which moves it sideways where the
    # eyeball turns away (outer side, up to ~1 mm) -> the painted lash no longer covers the r30 lash area. Put every
    # band vertex back on its painted (UV) front position; the same shift goes to every key
    uvl = lash.data.uv_layers.active.data
    uvv = {}
    for fc in lash.data.polygons:
        for li in fc.loop_indices:
            uvv[lash.data.loops[li].vertex_index] = tuple(uvl[li].uv)
    tb = E.TGT["tex_box"][s]
    kbs = lash.data.shape_keys.key_blocks
    shift = {}
    for i in band_idx[band_idx < nb * 7]:
        u_, v_ = uvv[int(i)]
        x0 = float(E.X(tb[0] + u_ * (tb[2] - tb[0])))
        z0 = float(E.Z(tb[1] + (1 - v_) * (tb[3] - tb[1])))
        p = lash.matrix_world @ kbs["Basis"].data[int(i)].co
        shift[int(i)] = Vector((x0 - p.x, 0.0, z0 - p.z))
    mi = lash.matrix_world.inverted().to_3x3()
    for kb in kbs:
        for i, d in shift.items():
            kb.data[i].co += mi @ d
    for i, d in shift.items():
        lash.data.vertices[i].co += mi @ d
    res["band_front_shift_mm_max"] = round(max(d.length for d in shift.values()) * 1000, 2)
    lid_bvh = {}

    def front(q, kname, band):
        """front-most skin surface at (x, z): the head, and for the lash band also the lid sheet of the same key"""
        y, n = E.front_hit(HEAD, q[0], q[2])
        if band and kname in lid_bvh:
            y2, n2 = E.front_hit(lid_bvh[kname], q[0], q[2])
            if y2 is not None and (y is None or y2 < y):
                y, n = y2, n2
        return y, n

    for o, idx, mode in ((lids, np.arange(len(lids.data.vertices)), "lid"), (lash, band_idx, "band")):
        moved = 0
        if mode == "band":
            fl = [tuple(f.vertices) for f in lids.data.polygons]
            for kb in lids.data.shape_keys.key_blocks:
                lid_bvh[kb.name] = BVHTree.FromPolygons([lids.matrix_world @ d.co for d in kb.data], fl)
        for kb in o.data.shape_keys.key_blocks:
            P = np.array([tuple(o.matrix_world @ kb.data[i].co) for i in idx])
            dive = 0.0021 + 0.0009 * E.smooth((P[:, 2] - poly[:, 1].mean()) / 0.012 + 0.5)   # socket margin of t25
            r = E.signed_dist(P[:, [0, 2]], poly) - dive
            for k, (p, rr) in enumerate(zip(P, r)):
                y, n = front(p, kb.name, mode == "band")
                if y is None:
                    continue
                ny = max(0.35, abs(n.y))
                if mode == "lid":
                    if rr > 0 and p[1] < y + 0.0003 / ny:
                        new = y + 0.0003 / ny
                        yb = sph.front_y(p[0], p[2])
                        if not np.isnan(yb):
                            new = min(new, float(yb) - 0.0003)          # stays in front of the eyeball
                        if new > p[1] + 1e-6:
                            P[k, 1] = new
                            moved += 1
                else:
                    tgt = y - 0.0004 / ny
                    yb = sph.front_y(p[0], p[2])
                    if not np.isnan(yb):
                        tgt = min(tgt, float(sph.surf(p[0], p[2], 0.0022)[1]))
                    if p[1] > tgt + 1e-6:
                        P[k, 1] = tgt
                        moved += 1
            if mode == "band":
                # between band vertices the coarse socket wall can still rise through the band: sample each band face
                # (4 x 4 points) and lift the face where the skin is in front of it
                pos = {int(i): k for k, i in enumerate(idx)}
                faces = [[pos[v] for v in f.vertices] for f in o.data.polygons if all(v in pos for v in f.vertices)]
                for _ in range(5):
                    lift = np.zeros(len(P))
                    for f in faces:
                        Q = P[f]
                        if len(f) == 4:                                          # 4 x 4 points over the quad
                            samples = [(1 - a) * (1 - b) * Q[0] + a * (1 - b) * Q[1] + a * b * Q[2] + (1 - a) * b * Q[3]
                                       for a in (0.15, 0.4, 0.6, 0.85) for b in (0.15, 0.4, 0.6, 0.85)]
                        else:
                            samples = [Q.mean(0)] + [(Q[a] + Q[(a + 1) % len(f)]) / 2 for a in range(len(f))]
                        need = 0.0
                        for q in samples:
                            y, n = front(q, kb.name, True)
                            if y is not None:
                                need = max(need, q[1] - (y - 0.0004 / max(0.35, abs(n.y))))
                        if need > 1e-6:
                            for a in f:
                                lift[a] = max(lift[a], need)
                    if not lift.any():
                        break
                    P[:, 1] -= lift
                    moved += int((lift > 0).sum())
            mi = o.matrix_world.inverted()
            for i, p in zip(idx, P):
                kb.data[i].co = mi @ Vector(tuple(p))
            if kb.name == "Basis":
                for i, p in zip(idx, P):
                    o.data.vertices[i].co = mi @ Vector(tuple(p))
        res[mode + "_vertex_moves_all_keys"] = moved
    return res


for s in E.SIDES:
    stats[f"depth_fix_{s}"] = fix_depths(s)
    lash = O[f"Eye_Lash.{s}"]
    ncol_band = (len(lash.data.vertices) - 36) // 7
    # material: clean texture, smooth alpha
    m = lash.material_slots[0].material.copy()
    m.name = f"MG6c_Lash_{s}"
    nt = m.node_tree
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    tex.image = bpy.data.images.load(os.path.join(EXP, "r30", f"eye_tex_lash_v6c_{s}.png"), check_existing=True)
    tex.interpolation = "Linear"
    mix = next(n for n in nt.nodes if n.type == "MIX_SHADER")
    nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
    for n in [n for n in nt.nodes if n.type == "MATH" and n.operation == "GREATER_THAN"]:
        nt.nodes.remove(n)
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    m["mmg_tex"] = f"eye_tex_lash_v6c_{s}.png"
    lash.material_slots[0].material = m

    # crease strip
    pts = np.array(CR[s]["centre"])
    px, py, hw = pts[:, 0], pts[:, 1], pts[:, 2]
    off = hw + 1.6                                               # painted half width + soft edge margin, r30 px
    rows = np.array([1.0, 0.0, -1.0])                             # below / centre / above the line (rows go up)
    bx = E.TGT["tex_box"][s]
    uv = lambda X, Y: np.stack([(X - bx[0]) / (bx[2] - bx[0]), 1 - (Y - bx[1]) / (bx[3] - bx[1])], 1)
    xs = np.repeat(px, 3)
    xm, hwid = (px.min() + px.max()) / 2, (px.max() - px.min()) / 2
    arc = np.clip(1 - ((px - xm) / hwid) ** 2, 0, 1) ** 0.5

    def strip(width, lift_px):
        ys = (py[:, None] - lift_px[:, None] + rows[None] * (off * width)[:, None]).ravel()
        return head_point(E.X(xs), E.Z(ys), 0.00025), ys

    basis, ys0 = strip(np.ones(len(px)), np.zeros(len(px)))
    keys = {"Blink": strip(np.zeros(len(px)) + 1e-3, np.zeros(len(px)))[0],
            "EyeSmile": strip(np.full(len(px), 0.85), np.zeros(len(px)))[0],
            "Smile": basis.copy(),
            "Surprise": strip(np.full(len(px), 1.1), 0.9 * 0.0022 * E.PPM * arc)[0]}
    F = E.grid_faces(len(px), 3)
    cre = E.mesh_object(f"Eye_Crease_tmp.{s}", basis, F, lash.users_collection[0], uvs=uv(xs, ys0), mat=m)
    for k, co in keys.items():
        E.add_key(cre, k, co)
    # Smile without the lid part (lash band and lid sheets keep their Basis in Smile)
    for o in (lash, O[f"Eye_Lids.{s}"]):
        kb = o.data.shape_keys.key_blocks
        for d, b in zip(kb["Smile"].data, kb["Basis"].data):
            d.co = b.co.copy()
    start = len(lash.data.vertices)
    bpy.ops.object.select_all(action="DESELECT")
    cre.select_set(True)
    lash.select_set(True)
    bpy.context.view_layer.objects.active = lash
    bpy.ops.object.join()
    lash["mmg_band_cols"] = ncol_band
    lash["mmg_band_rows"] = 7
    lash["mmg_crease_start"] = start
    assert len(lash.material_slots) == 1, [s_.material.name for s_ in lash.material_slots]
    assert [k.name for k in lash.data.shape_keys.key_blocks] == ["Basis", "Blink", "EyeSmile", "Smile", "Surprise"]

    # checks per pose: crease above the lash band (front px), lid sheet edge under the band
    def pose_coords(o, w):
        kb = o.data.shape_keys.key_blocks
        B = np.array([tuple(d.co) for d in kb["Basis"].data])
        out = B.copy()
        for name, v in w.items():
            out += v * (np.array([tuple(d.co) for d in kb[name].data]) - B)
        return np.array([tuple(o.matrix_world @ Vector(tuple(c))) for c in out])

    gaps = {}
    for pn, w in (("Neutral", {}), ("Blink50", {"Blink": 0.5}), ("Blink", {"Blink": 1.0}), ("EyeSmile", {"EyeSmile": 1.0}),
                  ("Smile+EyeSmile", {"Smile": 1.0, "EyeSmile": 1.0}), ("Surprise", {"Surprise": 1.0})):
        L = pose_coords(lash, w)
        band = L[:ncol_band * 7].reshape(ncol_band, 7, 3)
        btop = band[:, 6]                                          # top row (lash tips included)
        bbot = band[:, 1]
        cr = L[start:].reshape(len(px), 3, 3)
        cb = cr[:, 0]                                              # lower edge of the crease strip
        g = []
        for c in cb:
            k = np.argmin(np.abs(btop[:, 0] - c[0]))
            g.append(float(E.PY(btop[k, 2]) - E.PY(c[2])))          # + = crease above the lash tips (px)
        lid = pose_coords(O[f"Eye_Lids.{s}"], w)
        nl = len(lid) // 14
        edge = lid[:nl * 7].reshape(nl, 7, 3)[int(nl * 0.15): int(nl * 0.85), 1]     # upper lid sheet edge row
        cov = []
        for e in edge:
            k = np.argmin(np.abs(bbot[:, 0] - e[0]))
            cov.append(float(E.PY(bbot[k, 2]) - E.PY(e[2])))         # + = the band reaches below the lid edge
        gaps[pn] = dict(crease_over_lash_px_min=round(min(g), 2),
                        crease_width_px=round(float(np.median(E.PY(cr[:, 0, 2]) - E.PY(cr[:, 2, 2]))), 2),
                        band_below_lid_edge_px_min=round(min(cov), 2))
    stats[f"poses_{s}"] = gaps
    stats[f"tris_{s}"] = dict(lash=E.tri_count(lash), crease_added=2 * (len(px) - 1) * 2)
    O[f"Eye_Lash.{s}"].data.update()

for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
json.dump(stats, open(os.path.join(EXP, "spec", "eye_v6c_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, "MG_ToonTest_01_v6c_eye.blend"))
print("V6C_OK", json.dumps(stats))
