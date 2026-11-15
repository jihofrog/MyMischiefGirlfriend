"""ToonTest_01 step 50 (python with numpy / scipy / PIL): what borders the eyeball, drawn on the toon close up.

usage: python t50_eye_v6f_rimmap.py <tag> <eye_angle> [...]   e.g. v6d_3 R_35 L_-35
renders/<tag>_f6_rim_<eye_angle>.png: toon close up (faded) with the 5 px ring around the eyeball coloured by what is
there: lid sheet blue, lashes red, bare face skin yellow, background magenta.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

tag = sys.argv[1]
for ea in sys.argv[2:]:
    s, a = ea.split("_")
    lab = M.labels(os.path.join(M.R, f"{tag}_f6_{s}_id_{a}.png"))
    toon = M.load(os.path.join(M.R, f"{tag}_f6_{s}_toon_{a}.png"))
    g = M.group(lab)
    ball = g == "ball"
    ring = binary_dilation(ball, iterations=5) & ~ball
    vis = toon * 0.55 + 0.45
    for k, c in (("lid", (0.1, 0.3, 1)), ("lash", (0.9, 0.1, 0.1)), ("skin", (1, 0.85, 0)), ("bg", (1, 0, 1))):
        vis[ring & (g == k)] = c
    Image.fromarray((vis * 255).astype(np.uint8)).save(os.path.join(M.R, f"{tag}_f6_rim_{ea}.png"))
print("RIMMAP_OK")
