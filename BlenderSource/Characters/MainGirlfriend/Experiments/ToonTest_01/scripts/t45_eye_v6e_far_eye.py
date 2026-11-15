"""ToonTest_01 step 45 (Blender, background, the .blend is not saved): the far (right) eye at 35 / 45 deg, where the
eyeball shows against the face outline. Same camera / sun as t41.

usage: Blender -b <file.blend> --python t45_eye_v6e_far_eye.py -- <tag>
renders/<tag>_e6_eyeR_<a>.png (no hair, x4) and <tag>_e6_eyeRhair_<a>.png (with hair, x4); the box reaches past the
face outline.
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

tag = sys.argv[sys.argv.index("--") + 1]
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "e6"}
exec(open(p).read().split("FACE = (700")[0], g)
O = bpy.data.objects
HAIR = [o for o in O if (o.name.startswith("hair_bob_01") or o.name.startswith("acc_head_hairclip")) and not o.hide_render]
AXY = 0.03

ib = E.TGT["R"]["iris_bbox"]
x, z = float(E.X((ib[0] + ib[2]) / 2)), float(E.Z((ib[1] + ib[3]) / 2))
y, _ = E.front_hit(E.bvh_of(["Eye_Ball.R"]), x, z)
for a in (35, 45):
    t = math.radians(a)
    cx = 1030 + E.PPM * (x * math.cos(t) + (y - AXY) * math.sin(t))
    cy = float(E.PY(z))
    b = (int(cx - 110), int(cy - 85), int(cx + 130), int(cy + 85))
    for show, name in ((False, "eyeR"), (True, "eyeRhair")):
        for o in HAIR:
            o.hide_render = not show
        g["shoot"](f"e6_{name}_{a}", b, a, 4.0)
print("FAR_EYE_DONE", tag)
