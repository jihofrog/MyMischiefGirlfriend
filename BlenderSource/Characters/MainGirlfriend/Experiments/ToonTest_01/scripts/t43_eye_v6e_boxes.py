"""ToonTest_01 step 43 (Blender, background, read only): the t41 render boxes of one candidate for the Unity check (u07).

usage: Blender -b MG_ToonTest_01_<tag>.blend --python t43_eye_v6e_boxes.py -- <tag>
Writes spec/eye_e6_boxes_<tag>.json: {angle: {eyes: [x0, y0, x1, y1], eyeL: [...], expr: [...]}} in t03 pixels.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

tag = sys.argv[sys.argv.index("--") + 1]
AXY = 0.03


def centre(s):
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    return np.array([x, y, z])


def px_of(p, a):
    t = math.radians(a)
    return 1030 + E.PPM * (p[0] * math.cos(t) + (p[1] - AXY) * math.sin(t)), float(E.PY(p[2]))


def box(cx, cy, w, h):
    return [int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2)]


CL, CR = centre("L"), centre("R")
out = {}
for a in (0, 35, 45, 60, 90):
    xl, yl = px_of(CL, a)
    xr, yr = px_of(CR, a)
    out[str(a)] = dict(eyes=box((xl + xr) / 2, (yl + yr) / 2, 560, 220), eyeL=box(xl, yl, 260, 170),
                       expr=box((xl + xr) / 2, (yl + yr) / 2 + 20, 560, 260))
json.dump(out, open(os.path.join(E.EXP, "spec", f"eye_e6_boxes_{tag}.json"), "w"), indent=1)
print("BOXES_OK", tag)
