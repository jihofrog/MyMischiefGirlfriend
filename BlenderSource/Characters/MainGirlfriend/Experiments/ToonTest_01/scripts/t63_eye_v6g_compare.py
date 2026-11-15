"""ToonTest_01 step 63 (python with numpy / PIL): far eye at face scale, original v6f_A / 2D mock-up (t61) / 3D tags.

usage: python t63_eye_v6g_compare.py <tag3d,tag3d,...> <out.png> [face|facenh] [half-width px, default 120]
Columns +35 / -35 / +45 / -45, crop around the far eye (boxes of v6f_A, so every row shows the same place).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

tags, out = sys.argv[1].split(","), sys.argv[2]
kind = sys.argv[3] if len(sys.argv) > 3 else "face"
HW = int(sys.argv[4]) if len(sys.argv) > 4 else 120
BOX = json.load(open(os.path.join(M.EXP, "spec", "eye_f6_boxes_v6f_A.json")))
VIEWS = (("R", 35), ("L", -35), ("R", 45), ("L", -45))
rows = [("v6f_A 원본", lambda a: f"v6f_A_f6_{kind}_{a}.png"), ("2D 예상 (눈꼬리 감싸기)", lambda a: f"v6f_A_g6_{kind}_fixW_{a}.png")]
rows += [(f"3D {t}", (lambda t: lambda a: f"{t}_f6_{kind}_{a}.png")(t)) for t in tags]

F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
TW, TH, LW = 380, 300, 250
S = Image.new("RGB", (len(VIEWS) * (TW + 6) + LW, len(rows) * (TH + 6) + 36), "white")
d = ImageDraw.Draw(S)
for j, (s, a) in enumerate(VIEWS):
    d.text((LW + j * (TW + 6), 6), f"{a}° 먼 {'오른' if s == 'R' else '왼'}눈", fill="black", font=F)
    bx = BOX[f"{s}_{a}"]
    cx, cy = (bx[0] + bx[2]) / 2 - 600 + (10 if s == "R" else -10) * (a in (35, -35)), (bx[1] + bx[3]) / 2 + 5
    for i, (_, fn) in enumerate(rows):
        im = Image.fromarray((M.load(os.path.join(M.R, fn(a))) * 255).astype(np.uint8))
        im = im.crop((int(cx - HW), int(cy - HW * 0.79), int(cx + HW), int(cy + HW * 0.79))).resize((TW, TH), Image.LANCZOS)
        S.paste(im, (LW + j * (TW + 6), 36 + i * (TH + 6)))
for i, (lab, _) in enumerate(rows):
    d.text((6, 36 + i * (TH + 6) + TH // 2), lab, fill="black", font=F)
S.save(out)
print("COMPARE_OK", out)
