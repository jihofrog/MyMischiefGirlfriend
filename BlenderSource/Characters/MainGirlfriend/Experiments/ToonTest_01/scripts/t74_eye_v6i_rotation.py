"""ToonTest_01 step 74 (Blender, background, the .blend is not saved): head turn test 0 -> +-60 -> 0.

usage: Blender -b <file.blend> --python t74_eye_v6i_rotation.py -- <tag> [view]
Same camera / sun as t03 / t48 (hair on). Angles 0, 2, ..., 60, ..., 2, 0 and 0, -2, ..., -60, ..., 0; with "view" the
ViewFar keys follow every frame (eye_v6_common.view_key_values, gaze 0). Frames: renders/<tag>_rot/<i>.png (box around
both eyes, x1), i = frame number (0..60 for 0 -> +60 -> 0, 61..121 for 0 -> -60 -> 0).
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eye_v6_common as E  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
tag, view = args[0], "view" in args
sys.argv = [sys.argv[0], "--", tag]
p = os.path.join(HERE, "t03_render.py")
g = {"__file__": p, "__name__": "f6"}
exec(open(p).read().split("FACE = (700")[0], g)
O = bpy.data.objects
seq = list(range(0, 61, 2)) + list(range(58, -1, -2))
seq = seq + [-a for a in seq]
for o in O:
    if o.type == "MESH" and o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks[1:]:
            k.value = 0.0
for i, a in enumerate(seq):
    if view:
        vw = E.view_key_values(a)
        for o in O:
            if o.type == "MESH" and o.data.shape_keys:
                for k in o.data.shape_keys.key_blocks[1:]:
                    if k.name in vw:
                        k.value = vw[k.name]
        bpy.context.view_layer.update()
    g["shoot"](f"rot/{i:03d}", (560, 340, 1500, 640), a, 1.0)
print("ROT_DONE", tag, len(seq))
