"""ToonTest_01 step 62 (Blender, background): v6g from v6f_A - the white beyond the iris on the outer side steps back.

usage: V6G_H=<mm> V6G_OUT=<file.blend> Blender -b MG_ToonTest_01_v6f_A.blend --python t62_eye_v6g.py
In the 35 deg view of the far eye the white strip between the iris and the eyeball outline faces almost along the line of
sight (the eyeball there turns 48-55 deg outward), so the eye reads as a ball on the face. Here the eyeball surface on the
outer side of the iris drops back by V6G_H just outside the iris edge (over 12 % of the iris radius) and stays that much
lower out to the outer corner: seen from the far side the iris edge then hides that strip, like a cornea; from the front
nothing moves (y only), from the near side the strip still faces the camera. The step fades out toward the top and bottom
of the iris and 4 mm outside the r30 opening. Lid sheets, lash rows lying on the eyeball and the socket skin behind the
eyeball follow (heights above the eyeball kept); the rim, the face and the upper lash band on the rim stay. Then the lid
key blends are lifted clear of the eyeball again (t51 blend_lift).
Options: V6G_R0 (iris radius where the step starts), V6G_SUB=1 (eyeball subdivided once).
The eyeball keeps its old (smooth) shading normals, so the step shows only in the outline, not as a shaded crease.
Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6f_A.blend"
H = float(os.environ.get("V6G_H", 2.0)) / 1000
R0 = float(os.environ.get("V6G_R0", 0.99))          # step starts at this iris radius (1 = r30 iris edge)
SUB = os.environ.get("V6G_SUB", "0") == "1"           # eyeball: one more subdivision so the step edge is not jagged
OUT = os.environ["V6G_OUT"]
O = bpy.data.objects
stats = dict(step_mm=H * 1000, step_from_iris_radius=R0, eyeball_subdivided=SUB)


def blocks(o):
    return list(o.data.shape_keys.key_blocks) if o.data.shape_keys else []


def set_y(o, fn):
    mw, mi = o.matrix_world, o.matrix_world.inverted()
    for src in [kb.data for kb in blocks(o)] + [o.data.vertices]:
        P = np.array([tuple(mw @ v.co) for v in src])
        Y = fn(P)
        for v, p, y in zip(src, P, Y):
            if abs(y - p[1]) > 1e-9:
                v.co = mi @ Vector((p[0], y, p[2]))
    o.data.update()


def ball_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


GEO = {}
for s in E.SIDES:
    ib = E.TGT[s]["iris_bbox"]
    xc, zc = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    ax, az = abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2, abs(float(E.Z(ib[1]) - E.Z(ib[3]))) / 2
    GEO[s] = dict(sg=1 if s == "L" else -1, xc=xc, zc=zc, ax=ax, az=az, poly=E.opening_poly(s))


def field(P):
    d = np.zeros(len(P))
    for s, g in GEO.items():
        u = g["sg"] * (P[:, 0] - g["xc"])
        v = (P[:, 2] - g["zc"]) / g["az"]
        rho = np.sqrt((u / g["ax"]) ** 2 + v ** 2)
        step = sm((rho - R0) / 0.08)                            # just outside the iris edge
        lat = sm((u / g["ax"] - 0.25) / 0.45)                   # outer side only
        vert = 1 - sm((np.abs(v) - 0.9) / 0.3)                  # fades toward the top / bottom of the iris
        near = np.abs(P[:, 0] - g["xc"]) < 0.08
        out = E.signed_dist(P[:, [0, 2]], g["poly"])
        wo = 1 - sm(out / 0.004)
        d += np.where(near, H * step * lat * vert * wo, 0.0)
    return d


BALLS = {s: E.bvh_of([f"Eye_Ball.{s}"]) for s in E.SIDES}


def ball_any(P):
    y = np.full(len(P), np.nan)
    for s in E.SIDES:
        yy = ball_y(BALLS[s], P)
        m = np.isfinite(yy) & ~np.isfinite(y)
        y[m] = yy[m]
    return y


def vertex_normals(o):
    me = o.data
    acc = np.zeros((len(me.vertices), 3))
    for li, lp in enumerate(me.loops):
        acc[lp.vertex_index] += tuple(me.corner_normals[li].vector)
    return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)


def subdivide(o):
    """one cut on every edge (grid fill), positions linear, UVs interpolated; returns the smooth normals for all vertices
    (old: as before, new: averaged from the neighbours they were cut from)"""
    N_old = vertex_normals(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n_old = len(bm.verts)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bm.verts.ensure_lookup_table()
    N = np.zeros((len(bm.verts), 3))
    N[:n_old] = N_old
    done = np.zeros(len(bm.verts), bool)
    done[:n_old] = True
    for _ in range(3):
        for v in bm.verts:
            if done[v.index]:
                continue
            nb = [e.other_vert(v).index for e in v.link_edges if done[e.other_vert(v).index] and e.other_vert(v).index < n_old] \
                or [e.other_vert(v).index for e in v.link_edges if done[e.other_vert(v).index]]
            if nb:
                n = N[nb].sum(0)
                N[v.index] = n / np.linalg.norm(n)
                done[v.index] = True
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return N


for s in E.SIDES:
    ball = O[f"Eye_Ball.{s}"]
    if SUB:
        n_before = len(ball.data.polygons)
        N0 = subdivide(ball)
        stats[f"eyeball_faces_{s}"] = [n_before, len(ball.data.polygons)]
    else:
        N0 = vertex_normals(ball)
    set_y(ball, lambda P: P[:, 1] + field(P))
    ball.data.normals_split_custom_set_from_vertices([tuple(n) for n in N0])   # shading as before: no crease at the step
    set_y(O[f"Eye_Lids.{s}"], lambda P: P[:, 1] + field(P))

    def lash_fn(P):
        h = ball_any(P) - P[:, 1]
        w = np.where(np.isfinite(h), np.clip((0.0034 - h) / 0.0006, 0, 1), 0.0)
        return P[:, 1] + field(P) * w
    set_y(O[f"Eye_Lash.{s}"], lash_fn)


def head_fn(P):
    h = ball_any(P) - P[:, 1]
    w = np.where(np.isfinite(h), np.clip((0.0005 - h) / 0.0015, 0, 1) * np.clip((h + 0.008) / 0.002, 0, 1), 0.0)
    return P[:, 1] + field(P) * w      # socket skin only: the back of the head behind the eye stays


set_y(O["Blockout_Head"], head_fn)

# lid key blends clear of the new eyeball (same rule as t51)
src = open(os.path.join(HERE, "t51_eye_v6f.py")).read()
i, j = src.index("def blend_lift"), src.index("# ------------------------------------------------------------------ A: lid boundary")
exec(src[i:j])
for s in E.SIDES:
    blend_lift(s, E.bvh_of([f"Eye_Ball.{s}"]))  # noqa: F821


def lash_lift(s, BALL):
    """same for the lash band and the lower lash (the crease strip stays)"""
    lash = O[f"Eye_Lash.{s}"]
    cs = int(lash["mmg_crease_start"])
    mw, mi = lash.matrix_world, lash.matrix_world.inverted()
    kbs = lash.data.shape_keys.key_blocks
    K = {kb.name: np.array([tuple(mw @ d.co) for d in kb.data])[:cs] for kb in kbs}
    P0 = K["Basis"]
    mixes = [{k: t} for k in K if k != "Basis" for t in (0.25, 0.5, 0.75, 1.0)] + [{}]
    mixes += [{"Smile": t, "EyeSmile": t} for t in (0.5, 1.0)] + [{"Smile": 1.0, "EyeSmile": 0.5}, {"Smile": 0.5, "EyeSmile": 1.0}]
    lift = np.zeros(len(P0))
    for mx in mixes:
        Pm = P0 + sum((t * (K[k] - P0) for k, t in mx.items() if k in K), np.zeros_like(P0))
        ys = ball_y(BALL, Pm)
        need = Pm[:, 1] - (ys - 0.0001)
        lift = np.maximum(lift, np.where(np.isfinite(need), need, 0.0))
    lift[lift < 1e-6] = 0.0
    for kb in kbs:
        for d, l in zip(kb.data[:cs], lift):
            if l > 0:
                p = mw @ d.co
                d.co = mi @ Vector((p.x, p.y - l, p.z))
    for v, d in zip(lash.data.vertices, kbs["Basis"].data):
        v.co = d.co.copy()
    lash.data.update()
    stats.setdefault("lash_lift_for_blends", []).append(dict(side=s, verts=int((lift > 0).sum()), max_mm=round(float(lift.max()) * 1000, 2)))


for s in E.SIDES:
    lash_lift(s, E.bvh_of([f"Eye_Ball.{s}"]))

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6G_OK", json.dumps(stats))
