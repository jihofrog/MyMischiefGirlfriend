"""Race3D v2 expressions (Blender, background, the .blend is not saved): clearance of the linear key mixes Unity would draw.

usage: Blender -b Models/Race3D/experiments/MainGirlfriend_Race3D_v2_Expressions.blend --python race3d_v2_expr_check.py [-- v1]
(v1: only the v1 keys - Neutral, EyeSmile, Surprise with the same Blink / gaze / camera grid - as the baseline)
For every state (presets, the Neutral -> Happy -> Angry -> Sad -> Surprise transition frames, each with Blink 0 / 0.5 / 1,
gaze 0 / +-0.25, camera 0 / +-35 / +-45 for the view keys) the lid and lash positions are Basis + sum(value x delta)
exactly as a GPU blend shape mix. Counted: lid points closer than 0.1 mm to the eyeball (front projection) and lash
band points closer than 0.3 mm to the lid sheet in front of the eyeball - only where the point is also worse than in
the same Blink / gaze / camera state without the emotion (the v1 keys alone already go under both limits; see v1 mode).
Writes Models/Race3D/spec/race3d_v2_expr_check.json.
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
import expr_common as X  # noqa: E402
import expr_mix as M  # noqa: E402

E = X.E
O = bpy.data.objects
PRESETS = [{}, {"happy": 0.3}, {"happy": 0.6}, {"happy": 0.8}, {"happy": 1.0}, {"angry": 0.5}, {"angry": 1.0}, {"sad": 0.5},
           {"sad": 1.0}, {"sad": 1.0, "cry": 0.5}, {"sad": 1.0, "cry": 1.0}, {"surprise": 0.5}, {"surprise": 1.0}]
seq = [{}, {"happy": 1.0}, {"angry": 1.0}, {"sad": 1.0, "cry": 0.6}, {"surprise": 1.0}]
TRANS = [M.lerp_state(seq[i], seq[i + 1], k / 8) for i in range(len(seq) - 1) for k in range(1, 8)]
V1 = "v1" in sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else False
if V1:
    PRESETS = [{}, {"eyesmile": 0.5}, {"eyesmile": 1.0}, {"v1surprise": 0.5}, {"v1surprise": 1.0}, {"eyesmile": 0.5, "smile": 1.0}]
    TRANS = []
    PRESETS = PRESETS[1:]


def eye_values(st, yaw):
    if not V1:
        return M.compose(st, E.view_key_values, yaw)["eye"]
    v = dict(Blink=st.get("blink", 0.0), EyeSmile=st.get("eyesmile", 0.0), Smile=st.get("smile", 0.0), Surprise=st.get("v1surprise", 0.0))
    v.update(E.view_key_values(yaw, st.get("gaze", 0.0), v["Blink"], v["EyeSmile"]))
    return v


out = dict(mode="v1" if V1 else "v2", states=0, lid_ball_violations=0, lid_ball_worst_mm=None, lash_lid_violations=0, lash_lid_worst_mm=None, worst={})
for s in E.SIDES:
    lids, lash = O[f"Eye_Lids.{s}"], O[f"Eye_Lash.{s}"]
    nb, nr = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"])
    K_l = {k.name: X.key_world(lids, k.name) for k in lids.data.shape_keys.key_blocks}
    K_s = {k.name: X.key_world(lash, k.name) for k in lash.data.shape_keys.key_blocks}
    ball = E.bvh_of([f"Eye_Ball.{s}"])
    faces = [tuple(p.vertices) for p in lids.data.polygons]
    worst_b, worst_l = 1.0, 1.0
    base = {}

    def measure(v):
        Pl = K_l["Basis"] + sum(v.get(k, 0.0) * (K_l[k] - K_l["Basis"]) for k in K_l if k != "Basis")
        Ps = K_s["Basis"] + sum(v.get(k, 0.0) * (K_s[k] - K_s["Basis"]) for k in K_s if k != "Basis")
        yb = X.ball_y(ball, Pl)
        gap = yb - Pl[:, 1]
        bvh = BVHTree.FromPolygons([Vector(tuple(map(float, p))) for p in Pl], faces)
        band = Ps[:nb * nr]
        ly = X.ball_y(bvh, band)
        yb2 = X.ball_y(ball, band)
        over = np.isfinite(ly) & np.isfinite(yb2) & (ly < yb2)
        sep = np.where(over, ly - band[:, 1], np.inf)
        return np.where(np.isfinite(gap), gap, np.inf), sep

    for st0 in [{}] + PRESETS + TRANS:
        for b in (0.0, 0.5, 1.0):
            for gz in (0.0, 0.25, -0.25):
                for yaw in (0, 35, -35, 45, -45):
                    st = dict(st0, blink=b, gaze=gz)
                    gap, sep = measure(eye_values(st, yaw))
                    if not st0:
                        base[(b, gz, yaw)] = (gap, sep)
                        continue
                    out["states"] += 1
                    g0, s0 = base[(b, gz, yaw)]
                    # a point counts when it is under the clearance and worse than the same point without the emotion
                    bad = (gap < 0.0001 - 1e-6) & (gap < g0 - 2e-5)
                    badl = (sep < 0.0003 - 1e-6) & (sep < s0 - 2e-5)
                    out["lid_ball_violations"] += int(bad.sum())
                    out["lash_lid_violations"] += int(badl.sum())
                    if bad.any() and gap[bad].min() < worst_b:
                        worst_b = float(gap[bad].min())
                        out["worst"][f"lid_ball_{s}"] = dict(state=st, yaw=yaw, mm=round(worst_b * 1000, 3), base_mm=round(float(g0[bad].min()) * 1000, 3))
                    if badl.any() and sep[badl].min() < worst_l:
                        worst_l = float(sep[badl].min())
                        out["worst"][f"lash_lid_{s}"] = dict(state=st, yaw=yaw, mm=round(worst_l * 1000, 3))
                    if bad.any() or badl.any():
                        key = json.dumps(st0, sort_keys=True)
                        out.setdefault("states_with_new_violations", {}).setdefault(key, 0)
                        out["states_with_new_violations"][key] += 1
    out[f"lid_ball_min_mm_{s}"] = round(worst_b * 1000, 3)
    out[f"lash_lid_min_mm_{s}"] = round(worst_l * 1000, 3)
json.dump(out, open(os.path.join(os.path.dirname(HERE), "spec", f"race3d_v2_expr_check_{out['mode']}.json"), "w"), indent=1, default=str)
print("CHECK", json.dumps({k: v for k, v in out.items() if k != "worst"}))
print("WORST", json.dumps(out["worst"], default=str))
