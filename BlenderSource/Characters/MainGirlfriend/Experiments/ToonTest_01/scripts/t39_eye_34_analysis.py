"""ToonTest_01 step 39 (Blender, background, read only): why the eye looks pushed forward at 3/4 - numbers per eye.

usage: Blender -b <file.blend> --python t39_eye_34_analysis.py -- <tag>
Writes spec/eye_v6e_analysis_<tag>.json. Yaw = turn about the vertical axis away from the face front (+ = outward,
toward the ear); views orbit as in t03 (camera toward the character's left for +yaw, so the left eye is the near eye).
  facing      outward yaw of: the eyeball surface at the iris centre, the plane through the visible lid edges, the skin
              ring 6-12 mm outside the opening, the skin at the outer corner
  spread      projected width of the opening / iris at 0-90 deg relative to the front (a front-facing flat eye: cos yaw)
  bulge       at 35 / 45 / 60 deg, scan line through the iris centre: how far the eyeball (where it is the visible
              surface) comes in front of the straight chord between the skin 3 mm beyond its two visible ends (mm, + = in
              front); and the eyeball vs the skin behind it (socket)
  profile     skin depth across the face at the iris height (x 0 .. 0.13 m) and its outward yaw
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.abspath(bpy.data.filepath).startswith(EXP)
tag = sys.argv[sys.argv.index("--") + 1]
O = bpy.data.objects
AXY = 0.03                                      # t03 orbit axis (x 0, y 0.03)
YAWS = (0, 35, 45, 60, 90)
out = {"tag": tag}


def yaw_of(n, sgn):
    return round(math.degrees(math.atan2(n[0] * sgn, -n[1])), 1)


def bvh(names):
    return E.bvh_of([n for n in names if n in O])


for s, sgn in (("L", 1), ("R", -1)):
    res = {}
    BALL = bvh([f"Eye_Ball.{s}"])
    SKIN = bvh(["Blockout_Head"])
    LID = bvh([f"Eye_Lids.{s}", f"Eye_Lash.{s}", "Blockout_Head"])
    ALL = bvh(["Blockout_Head", f"Eye_Lids.{s}", f"Eye_Lash.{s}", f"Eye_Ball.{s}"])
    poly = E.opening_poly(s)
    ib = E.TGT[s]["iris_bbox"]
    ic = np.array([float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))])
    h = BALL.ray_cast(Vector((ic[0], -1, ic[1])), Vector((0, 1, 0)), 3)
    res["iris_centre"] = [round(ic[0], 4), round(h[0].y, 4), round(ic[1], 4)]
    res["yaw_eyeball_at_iris"] = yaw_of(h[1], sgn)
    # lid edge plane: lash band bottom row + lower lid edge row (rest pose)
    lash, lids = O[f"Eye_Lash.{s}"], O[f"Eye_Lids.{s}"]
    nb = int(lash.get("mmg_band_cols", (len(lash.data.vertices) - 36) // 7))
    Lb = np.array([tuple(v) for v in E.world_mesh(lash)[0]])
    Ll = np.array([tuple(v) for v in E.world_mesh(lids)[0]])
    nc = len(Ll) // 14
    xs = sorted(E.cols(s, "opening_cols"))
    xa, xb = sorted([float(E.X(xs[0])), float(E.X(xs[-1]))])
    bb = Lb[:nb * 7].reshape(nb, 7, 3)[:, 1]
    bb = bb[(bb[:, 0] > xa) & (bb[:, 0] < xb)]
    rim = np.concatenate([bb, Ll[nc * 7:].reshape(nc, 7, 3)[:, 1]])
    A = np.c_[rim[:, 0], rim[:, 2], np.ones(len(rim))]
    coef, *_ = np.linalg.lstsq(A, rim[:, 1], rcond=None)
    nrm = np.array([-coef[0], 1.0, -coef[1]])
    nrm = -nrm / np.linalg.norm(nrm)                               # outward (toward -y)
    res["yaw_lid_plane"] = yaw_of(nrm, sgn)
    c = poly.mean(0)
    ring = []
    for p in poly[::6]:
        d = (p - c) / np.linalg.norm(p - c)
        for r in (0.006, 0.009, 0.012):
            q = p + d * r
            hh = SKIN.ray_cast(Vector((q[0], -1, q[1])), Vector((0, 1, 0)), 3)
            if hh[0] is not None:
                ring.append(tuple(hh[1]))
    rn = np.mean(ring, 0)
    res["yaw_skin_ring"] = yaw_of(rn, sgn)
    outer = poly[np.argmax(poly[:, 0] * sgn)]
    hh = SKIN.ray_cast(Vector((outer[0] + sgn * 0.008, -1, outer[1])), Vector((0, 1, 0)), 3)
    res["yaw_skin_outer_corner"] = yaw_of(hh[1], sgn)
    # projected spread
    iris_pts = []
    rx, rz = (ib[2] - ib[0]) / 2 / E.PPM, (ib[3] - ib[1]) / 2 / E.PPM
    for a in np.linspace(0, 2 * np.pi, 48, endpoint=False):
        x, z = ic[0] + rx * math.cos(a), ic[1] + rz * math.sin(a)
        hh = BALL.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 3)
        if hh[0] is not None:
            iris_pts.append(tuple(hh[0]))
    iris_pts = np.array(iris_pts)
    spread = {}
    for t in YAWS:
        tr = math.radians(t * sgn)
        right = np.array([math.cos(tr), math.sin(tr), 0])
        f = lambda P: (P[:, 0] * right[0] + (P[:, 1] - AXY) * right[1])
        spread[t] = dict(opening=float(np.ptp(f(rim))), iris=float(np.ptp(f(iris_pts))))
    res["spread_vs_front"] = {t: dict(opening=round(v["opening"] / spread[0]["opening"], 3), iris=round(v["iris"] / spread[0]["iris"], 3),
                                      flat_front_eye=round(math.cos(math.radians(t)), 3)) for t, v in spread.items()}
    # bulge along the scan line through the iris centre
    bul = {}
    for t in (35, 45, 60):
        tr = math.radians(t * sgn)
        view = Vector((-math.sin(tr), math.cos(tr), 0))
        right = Vector((math.cos(tr), math.sin(tr), 0))
        s0 = ic[0] * right.x + (h[0].y - AXY) * right.y
        samples = []
        for ds in np.arange(-0.07, 0.07, 0.0005):
            o = Vector((0, AXY, ic[1])) + right * (s0 + ds) - view * 1.0
            fa = ALL.ray_cast(o, view, 3)
            fe = BALL.ray_cast(o, view, 3)
            fs = SKIN.ray_cast(o, view, 3)
            samples.append((ds, fa[3] if fa[0] else None, fe[3] if fe[0] else None, fs[3] if fs[0] else None))
        vis = set(k for k, (ds, fa, fe, fs) in enumerate(samples) if fa is not None and fe is not None and abs(fa - fe) < 1e-5)
        kc = int(np.argmin([abs(sm[0]) for sm in samples]))                # the run through the iris centre
        if kc not in vis:
            near = sorted(vis, key=lambda k: abs(k - kc))
            if not near or abs(near[0] - kc) > 6:
                bul[t] = None
                continue
            kc = near[0]
        k0 = k1 = kc
        while k0 - 1 in vis or k0 - 2 in vis:
            k0 -= 1
        while k1 + 1 in vis or k1 + 2 in vis:
            k1 += 1
        pad = 6                                                           # 3 mm beyond the visible eyeball
        ka, kb = max(0, k0 - pad), min(len(samples) - 1, k1 + pad)
        da, db = samples[ka][1], samples[kb][1]
        best, deep = -1e9, []
        for k in range(k0, k1 + 1):
            ds, fa, fe, fs = samples[k]
            if fe is None or fa is None or abs(fa - fe) > 1e-5:
                continue
            chord = da + (db - da) * (k - ka) / (kb - ka)
            best = max(best, chord - fe)
            if fs is not None:
                deep.append(fs - fe)
        bul[t] = dict(bulge_over_chord_mm=round(best * 1000, 2), visible_eyeball_mm=round((k1 - k0) * 0.5, 1),
                      eyeball_vs_skin_behind_mm=round(float(np.median(deep)) * 1000, 2) if deep else None)
    res["bulge"] = bul
    prof = []
    for x in np.arange(0.0, 0.131, 0.01):
        hh = SKIN.ray_cast(Vector((sgn * x, -1, ic[1])), Vector((0, 1, 0)), 3)
        if hh[0] is not None:
            prof.append((round(float(x), 3), round(hh[0].y * 1000, 1), yaw_of(hh[1], sgn)))
    res["profile_x_y_yaw"] = prof
    res["opening_x"] = [round(xa, 4), round(xb, 4)]
    out[s] = res
json.dump(out, open(os.path.join(EXP, "spec", f"eye_v6e_analysis_{tag}.json"), "w"), indent=1)
L = out["L"]
print("ANALYSIS", tag, json.dumps({k: L[k] for k in ("yaw_eyeball_at_iris", "yaw_lid_plane", "yaw_skin_ring", "yaw_skin_outer_corner", "spread_vs_front", "bulge")}))
print("PROFILE", L["profile_x_y_yaw"], "opening x", L["opening_x"])
