"""ToonTest_01 step 71 (python with numpy / PIL): bright white px of the 4x eye close ups (t48), per tag and view.

usage: python t71_eye_white_px.py <tag,tag,...> <view,view,...> [kind, default toon] [out.json]
view = <s>_<a>, e.g. R_35. White: luminance > 0.80, saturation < 0.10, not the background.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")


def load(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB")).astype(float) / 255


def white(a):
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return int(((lum > 0.80) & (sat < 0.10) & (mn < 0.99)).sum())


tags, views = sys.argv[1].split(","), sys.argv[2].split(",")
kind = sys.argv[3] if len(sys.argv) > 3 else "toon"
res = {}
for v in views:
    s, a = v.split("_")
    res[v] = {t: white(load(os.path.join(R, f"{t}_f6_{s}_{kind}_{a}.png"))) for t in tags}
    print(v, res[v])
if len(sys.argv) > 4:
    json.dump(res, open(sys.argv[4], "w"), indent=1)
