"""ToonTest_01 step 81 (Blender, background): v6j from v6i - lash band of the view keys without the Blink turn.

usage: V6J_MODE=<keep|shift> V6J_OUT=<file.blend> [V6J_U0=0.85 V6J_W=0.35 V6J_SH=0.35]
       Blender -b MG_ToonTest_01_v6i.blend --python t81_eye_v6j_lash.py
In v6i the view keys move the lash band along the Blink path, which also turns the strands down; seen from the far side
the turned strands of the eye tail stand out from the eye line like spikes. Changed in ViewFar<s>, ViewFar<s>_GO and
ViewFar<s>_GI only (Basis, Blink, ViewSide and the other keys stay):
  keep  (default) the band columns over the iris come down with the lid as in v6i; past the iris (u / iris half-width
        from V6J_U0 to V6J_U0 + V6J_W) their share of the v6i key fades to 0, so the eye-tail flick stays where it is in
        the front view and only the lid skin closes under it
  shift every band column keeps its Basis strand shape and follows its root row (row 1); closing columns get shorter
        by V6J_SH * f (tried: the tail strands then point sideways from mid height) Row 0 (skirt) and the lower lash / crease keep the v6i key. Then the lash is kept
0.3 mm in front of the lid sheet in every driver blend (t52 rule). Writes the .blend and spec/eye_<name>_stats.json.
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

EXP = E.EXP
assert os.path.basename(bpy.data.filepath) == "MG_ToonTest_01_v6i.blend"
SH = float(os.environ.get("V6J_SH", 0.35))
MODE = os.environ.get("V6J_MODE", "keep")
U0 = float(os.environ.get("V6J_U0", 0.85))
W = float(os.environ.get("V6J_W", 0.35))
OUT = os.environ["V6J_OUT"]
O = bpy.data.objects
stats = dict(mode=MODE, shorten=SH, keep_from_iris_radii=[U0, U0 + W])

for s in E.SIDES:
    lash = O[f"Eye_Lash.{s}"]
    nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
    kbs = lash.data.shape_keys.key_blocks
    B = np.array([tuple(d.co) for d in kbs["Basis"].data])
    BL = np.array([tuple(d.co) for d in kbs["Blink"].data])
    ib = E.TGT[s]["iris_bbox"]
    sg = 1 if s == "L" else -1
    xc = float(E.X((ib[0] + ib[2]) / 2))
    ax = abs(float(E.X(ib[2]) - E.X(ib[0]))) / 2
    Wb = np.array([tuple(lash.matrix_world @ d.co) for d in kbs["Basis"].data])
    for name in (f"ViewFar{s}", f"ViewFar{s}_GO", f"ViewFar{s}_GI"):
        K = np.array([tuple(d.co) for d in kbs[name].data])
        new = K.copy()
        fs = []
        if MODE == "keep":
            for c in range(nb):
                u = sg * (Wb[c * nr + 1, 0] - xc) / ax
                g = 1 - float(E.smooth((u - U0) / W))
                sl = slice(c * nr, c * nr + nr)
                new[sl] = B[sl] + g * (K[sl] - B[sl])
                fs.append(g)
            for d, c in zip(kbs[name].data, new):
                d.co = tuple(c)
            stats[f"{name}"] = dict(cols_kept=int(sum(g < 0.05 for g in fs)), cols_partial=int(sum(0.05 <= g < 0.95 for g in fs)))
            continue
        for c in range(nb):
            r1 = c * nr + 1
            dv = K[r1] - B[r1]
            bl = BL[r1] - B[r1]
            f = float(np.clip(np.dot(dv, bl) / max(np.dot(bl, bl), 1e-12), 0, 1))    # Blink fraction of the root
            fs.append(f)
            for r in range(1, nr):
                i = c * nr + r
                new[i] = B[r1] + dv + (B[i] - B[r1]) * (1 - SH * f)
        for d, c in zip(kbs[name].data, new):
            d.co = tuple(c)
        stats[f"{name}"] = dict(cols_closing=int(sum(f > 0.05 for f in fs)), f_max=round(max(fs), 3))
    lash.data.update()

# lash in front of the lid sheet (0.3 mm) and of the eyeball (0.1 mm) in the driver blends, view keys only
def front_y(bvh, P):
    out = np.full(len(P), np.nan)
    for i, p in enumerate(P):
        y, _ = E.front_hit(bvh, p[0], p[2])
        if y is not None:
            out[i] = y
    return out


for s in E.SIDES:
    lash, lids = O[f"Eye_Lash.{s}"], O[f"Eye_Lids.{s}"]
    BALL = E.bvh_of([f"Eye_Ball.{s}"])
    nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
    n = nb * nr
    mw, mi = lash.matrix_world, lash.matrix_world.inverted()
    total = np.zeros(n)
    for name in (f"ViewFar{s}", f"ViewFar{s}_GO", f"ViewFar{s}_GI"):
        for t in (0.25, 0.5, 0.75, 1.0):
            for extra in ({}, {"Surprise": 1.0}, {"Blink": 0.5}, {"EyeSmile": 0.5}):
                sc = (1 - extra.get("Blink", 0)) * (1 - extra.get("EyeSmile", 0))
                w = dict(extra, **{name: t * sc})
                for o in (lash, lids):
                    for k in o.data.shape_keys.key_blocks[1:]:
                        k.value = w.get(k.name, 0.0)
                bpy.context.view_layer.update()
                LB = E.bvh_of([lids.name])
                vs, _ = E.world_mesh(lash)
                P = np.array([tuple(v) for v in vs])[:n]
                yl = front_y(LB, P)
                yb = front_y(BALL, P)
                need = np.fmax(np.where(np.isfinite(yl), P[:, 1] - (yl - 0.0003), 0), np.where(np.isfinite(yb), P[:, 1] - (yb - 0.0001), 0))
                need = np.where(np.isfinite(need), need, 0)
                idx = np.nonzero(need > 1e-6)[0]
                if len(idx):
                    kb = lash.data.shape_keys.key_blocks[name]
                    for j in idx:
                        l = min(need[j] / (t * sc), 0.002)
                        p = mw @ kb.data[j].co
                        kb.data[j].co = mi @ Vector((p.x, p.y - l, p.z))
                        total[j] += l
                    lash.data.update()
    for o in (lash, lids):
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
    stats[f"lash_lift_{s}"] = [int((total > 0).sum()), round(float(total.max()) * 1000, 2)]

name = os.path.splitext(OUT)[0].replace("MG_ToonTest_01_", "")
json.dump(stats, open(os.path.join(EXP, "spec", f"eye_{name}_stats.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(EXP, OUT))
print("V6J_OK", json.dumps(stats))
