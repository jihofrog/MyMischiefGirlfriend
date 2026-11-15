"""ToonTest_01 step 52 (Blender, background, read only): depth order checks for v6f, per eye and pose.

usage: Blender -b <file.blend> --python t52_eye_v6f_checks.py -- <tag>
Poses: Neutral, Blink50, Blink, EyeSmile, SmileEyeSmile, Surprise. Counts (inside the r30 opening + 4 mm):
  lid_behind_ball    lid sheet vertices behind the eyeball surface
  lash_behind_ball   lash band / lower lash vertices behind the eyeball surface
  lash_behind_lid    lash band vertices with the lid sheet more than 0.05 mm in front of them (lid through the lashes)
  skin_through_ball  socket skin vertices more than 0.1 mm in front of the eyeball 1 mm or more inside the opening
Writes spec/eye_v6f_checks_<tag>.json.
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

tag = sys.argv[sys.argv.index("--") + 1]
O = bpy.data.objects
POSES = (("Neutral", {}), ("Blink50", {"Blink": 0.5}), ("Blink", {"Blink": 1.0}), ("EyeSmile", {"EyeSmile": 1.0}),
         ("SmileEyeSmile", {"Smile": 1.0, "EyeSmile": 1.0}), ("Surprise", {"Surprise": 1.0}))
if os.environ.get("VIEWPOSES") == "1":           # v6i: ViewFar keys of both eyes (as if both were far), through the driver
    def _vf(yaw, gaze=0.0, blink=0.0, eyesmile=0.0, raw=False, **extra):
        w = {}
        for a in (yaw, -yaw):
            w.update({k: v for k, v in (E.view_key_values(a, 0, 0, 0) if raw else E.view_key_values(a, gaze, blink, eyesmile)).items() if v})
        w.update(extra)
        if blink:
            w["Blink"] = blink
        if eyesmile:
            w["EyeSmile"] = eyesmile
        return w
    POSES = (("VF", _vf(40)), ("VF_GazeOut", _vf(40, gaze=0.25)), ("VF_GazeIn", _vf(40, gaze=-0.25)),
             ("VF_Blink50", _vf(40, blink=0.5)), ("VF_Blink", _vf(40, blink=1.0)), ("VF_EyeSmile", _vf(40, eyesmile=1.0)),
             ("VF_SmileEyeSmile", _vf(40, eyesmile=1.0, Smile=1.0)), ("VF_Surprise", _vf(40, Surprise=1.0)),
             ("VF_Smile", _vf(40, Smile=1.0)), ("VF30_Blink50", _vf(30, blink=0.5)),
             ("VF60", _vf(60)), ("VF60_Blink50", _vf(60, blink=0.5)), ("VF90_Surprise", _vf(90, Surprise=1.0)),
             ("VF90_EyeSmile", _vf(90, eyesmile=1.0)),
             ("RAW_VF_Blink", _vf(40, blink=1.0, raw=True)), ("RAW_VF_EyeSmile", _vf(40, eyesmile=1.0, raw=True)))


def pose(w):
    for o in O:
        if o.type == "MESH" and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = w.get(k.name, 0.0)
    bpy.context.view_layer.update()


def pts(o):
    vs, _ = E.world_mesh(o)
    return np.array([tuple(v) for v in vs])


out = {"tag": tag}
for s in E.SIDES:
    poly = E.opening_poly(s)
    lash = O[f"Eye_Lash.{s}"]
    nb, nr, cs = int(lash["mmg_band_cols"]), int(lash["mmg_band_rows"]), int(lash["mmg_crease_start"])
    res = {}
    for pn, w in POSES:
        pose(w)
        B = E.bvh_of([f"Eye_Ball.{s}"] + ([f"Eye_TailWrap.{s}"] if f"Eye_TailWrap.{s}" in O else []))   # v6h: eye-tail piece counts as eyeball cover
        LB = E.bvh_of([f"Eye_Lids.{s}"])
        c = dict(lid_behind_ball=0, lash_behind_ball=0, lash_behind_lid=0, skin_through_ball=0)
        for p in pts(O[f"Eye_Lids.{s}"]):
            if E.signed_dist(np.array([[p[0], p[2]]]), poly)[0] < 0.004:
                y, _ = E.front_hit(B, p[0], p[2])
                if y is not None and p[1] > y + 0.00002:
                    c["lid_behind_ball"] += 1
        P = pts(lash)[:cs]
        for i, p in enumerate(P):
            if E.signed_dist(np.array([[p[0], p[2]]]), poly)[0] >= 0.004:
                continue
            y, _ = E.front_hit(B, p[0], p[2])
            if y is not None and p[1] > y + 0.00002:
                c["lash_behind_ball"] += 1
            if i < nb * nr:
                yl, _ = E.front_hit(LB, p[0], p[2])
                if yl is not None and yl < p[1] - 0.00005:
                    c["lash_behind_lid"] += 1
        H = pts(O["Blockout_Head"])
        sd = E.signed_dist(H[:, [0, 2]], poly)
        for p in H[sd < -0.001]:
            y, _ = E.front_hit(B, p[0], p[2])
            if y is not None and p[1] < y - 0.0001:
                c["skin_through_ball"] += 1
        res[pn] = c
    pose({})
    out[s] = res
json.dump(out, open(os.path.join(E.EXP, "spec", f"eye_v6f_checks_{tag}" + ("_view" if os.environ.get("VIEWPOSES") == "1" else "") + ".json"), "w"), indent=1)
print("V6F_CHECKS", json.dumps(out))
