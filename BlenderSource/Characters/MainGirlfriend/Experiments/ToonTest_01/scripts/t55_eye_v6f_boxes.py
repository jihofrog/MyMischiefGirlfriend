"""ToonTest_01 step 55 (Blender, background, read only): the t48 close-up boxes for the Unity check (u08).

usage: Blender -b MG_ToonTest_01_<tag>.blend --python t55_eye_v6f_boxes.py -- <tag>
Writes spec/eye_f6_boxes_<tag>.json: {"<side>_<angle>": [x0, y0, x1, y1]} in t03 pixels.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

tag = sys.argv[sys.argv.index("--") + 1]
out = {}
for s in "LR":
    ib = E.TGT[s]["iris_bbox"]
    x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
    y, _ = E.front_hit(E.bvh_of([f"Eye_Ball.{s}"]), x, z)
    for a in (0, 15, -15, 25, -25, 35, -35, 45, -45, 60, -60, 90, -90):
        t = math.radians(a)
        cx, cy = 1030 + E.PPM * (x * math.cos(t) + (y - 0.03) * math.sin(t)), float(E.PY(z))
        out[f"{s}_{a}"] = [int(cx - 120), int(cy - 85), int(cx + 120), int(cy + 85)]
json.dump(out, open(os.path.join(E.EXP, "spec", f"eye_f6_boxes_{tag}.json"), "w"), indent=1)
print("BOXES_OK", tag)
