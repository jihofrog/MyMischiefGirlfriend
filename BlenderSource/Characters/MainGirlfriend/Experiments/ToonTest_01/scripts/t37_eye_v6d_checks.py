"""ToonTest_01 step 37 (Blender, background, read only): "eyeball forward" numbers for v6c / v6d candidates.

usage: Blender -b <file.blend> --python t37_eye_v6d_checks.py -- <tag>
Writes spec/eye_v6d_checks_<tag>.json, per eye (mm):
  dome           eyeball surface inside the r30 opening (1 mm in) vs the plane through the visible lid edges (lash band
                 bottom + lower lid edge at rest), + = in front of that plane: max / p90 / median
  below_ring     eyeball 2 mm inside the opening vs the skin 5 mm outside (+ = eyeball deeper), median
  apex_curv      horizontal / vertical curvature of the eyeball at the iris centre (1/m, from a local quadratic fit)
  penetration    per pose (Neutral, Blink 50 / 100, EyeSmile, Smile + EyeSmile, Surprise): lid sheet and lash skirt vertices
                 behind the eyeball surface; eyeball points > 4 mm outside the opening in front of the skin
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1]
O = bpy.data.objects
HEAD = E.bvh_of(["Blockout_Head"])
POSES = (("Neutral", {}), ("Blink50", {"Blink": 0.5}), ("Blink", {"Blink": 1.0}), ("EyeSmile", {"EyeSmile": 1.0}),
         ("SmileEyeSmile", {"Smile": 1.0, "EyeSmile": 1.0}), ("Surprise", {"Surprise": 1.0}))
out = {"tag": tag}


def pose(w):
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = w.get(k.name, 0.0)
    bpy.context.view_layer.update()


def pts(o):
    vs, _ = E.world_mesh(o)
    return np.array([tuple(v) for v in vs])


for s in E.SIDES:
    res = {}
    pose({})
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    poly = E.opening_poly(s)
    lash, lids = O[f"Eye_Lash.{s}"], O[f"Eye_Lids.{s}"]
    nb = int(lash.get("mmg_band_cols", (len(lash.data.vertices) - 36) // 7))
    Lb = pts(lash)
    Ll = pts(lids)
    nc = len(Ll) // 14
    oc = E.cols(s, "opening_cols")
    xs = np.array(sorted(oc), float)
    x0, x1 = E.X(xs.min()), E.X(xs.max())
    band_bottom = Lb[:nb * 7].reshape(nb, 7, 3)[:, 1]
    band_bottom = band_bottom[(band_bottom[:, 0] > min(x0, x1)) & (band_bottom[:, 0] < max(x0, x1))]
    low_edge = Ll[nc * 7:].reshape(nc, 7, 3)[:, 1]
    rim = np.concatenate([band_bottom, low_edge])
    A = np.c_[rim[:, 0], rim[:, 2], np.ones(len(rim))]
    coef, *_ = np.linalg.lstsq(A, rim[:, 1], rcond=None)
    gx, gz = np.meshgrid(np.arange(poly[:, 0].min(), poly[:, 0].max(), 0.0008), np.arange(poly[:, 1].min(), poly[:, 1].max(), 0.0008))
    G = np.stack([gx.ravel(), gz.ravel()], 1)
    G = G[E.signed_dist(G, poly) < -0.001]
    dome = []
    for x, z in G:
        y, _ = E.front_hit(BALL, x, z)
        if y is not None:
            dome.append((coef[0] * x + coef[1] * z + coef[2]) - y)
    dome = np.array(dome) * 1000
    res["dome_mm"] = dict(max=round(float(dome.max()), 2), p90=round(float(np.percentile(dome, 90)), 2), med=round(float(np.median(dome)), 2))
    c = poly.mean(0)
    ring = []
    for p in poly[::4]:
        n = (p - c) / np.linalg.norm(p - c)
        yi, _ = E.front_hit(BALL, *(p - n * 0.002))
        yo, _ = E.front_hit(HEAD, *(p + n * 0.005))
        if yi is not None and yo is not None:
            ring.append((yi - yo) * 1000)
    res["below_ring_mm_med"] = round(float(np.median(ring)), 2)
    ib = E.TGT[s]["iris_bbox"]
    ic = (float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2)))
    Q = []
    for dx in np.linspace(-0.012, 0.012, 9):
        for dz in np.linspace(-0.012, 0.012, 9):
            y, _ = E.front_hit(BALL, ic[0] + dx, ic[1] + dz)
            if y is not None:
                Q.append((dx, dz, y))
    Q = np.array(Q)
    M = np.c_[Q[:, 0] ** 2, Q[:, 1] ** 2, Q[:, 0] * Q[:, 1], Q[:, 0], Q[:, 1], np.ones(len(Q))]
    k, *_ = np.linalg.lstsq(M, Q[:, 2], rcond=None)
    res["apex_curvature_per_m"] = dict(horizontal=round(float(2 * k[0]), 3), vertical=round(float(2 * k[1]), 3))
    # penetration per pose
    pen = {}
    for pn, w in POSES:
        pose(w)
        B = E.bvh_of([f"Eye_Ball.{s}"])
        Pl = pts(lids)
        Pk = pts(lash)[:nb * 7].reshape(nb, 7, 3)[:, 0]          # skirt row
        n_in = 0
        for p in np.concatenate([Pl, Pk]):
            y, _ = E.front_hit(B, p[0], p[2])
            if y is not None and p[1] > y + 0.00002 and E.signed_dist(np.array([[p[0], p[2]]]), poly)[0] < 0.004:
                n_in += 1
        pen[pn] = n_in
    pose({})
    res["lid_or_skirt_behind_eyeball"] = pen
    bv = pts(O[f"Eye_Ball.{s}"])
    sd = E.signed_dist(bv[:, [0, 2]], poly)
    poke = 0
    for p, r in zip(bv, sd):
        if r > 0.004:
            y, _ = E.front_hit(HEAD, p[0], p[2])
            if y is not None and y > p[1] + 1e-5:
                poke += 1
    res["eyeball_in_front_of_skin_outside_socket"] = poke
    out[s] = res
json.dump(out, open(os.path.join(EXP, "spec", f"eye_v6d_checks_{tag}.json"), "w"), indent=1)
print("V6D_CHECKS", json.dumps(out))
