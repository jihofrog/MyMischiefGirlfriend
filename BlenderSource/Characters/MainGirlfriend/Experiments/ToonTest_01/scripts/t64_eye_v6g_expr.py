"""ToonTest_01 step 64 (python with numpy / PIL): expressions close up at +-35 (t48 expr renders), far and near eye.

usage: python t64_eye_v6g_expr.py <tag,tag,...> <angle> <out.png> [half-width px, default 75]
Rows: tag x (far eye, near eye); columns: the poses. Crops use the v6f_A eye boxes of the face render.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

tags, a, out = sys.argv[1].split(","), int(sys.argv[2]), sys.argv[3]
HW = int(sys.argv[4]) if len(sys.argv) > 4 else 75
BOX = json.load(open(os.path.join(M.EXP, "spec", "eye_f6_boxes_v6f_A.json")))
POSES = tuple(os.environ.get("POSES", "Neutral,Blink50,Blink,EyeSmile,SmileEyeSmile,Surprise,GazeL,GazeR").split(","))
far, near = ("R", "L") if a > 0 else ("L", "R")

F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
TW, TH, LW = 240, int(240 * 0.79), 230
rows = [(t, s) for t in tags for s in (far, near)]
S = Image.new("RGB", (len(POSES) * (TW + 4) + LW, len(rows) * (TH + 4) + 32), "white")
d = ImageDraw.Draw(S)
for j, p in enumerate(POSES):
    d.text((LW + j * (TW + 4), 4), p, fill="black", font=F)
    for i, (t, s) in enumerate(rows):
        ctr = {k: ((BOX[f"{k}_{a}"][0] + BOX[f"{k}_{a}"][2]) / 2, (BOX[f"{k}_{a}"][1] + BOX[f"{k}_{a}"][3]) / 2) for k in "LR"}
        mx, my = (ctr["L"][0] + ctr["R"][0]) / 2, (ctr["L"][1] + ctr["R"][1]) / 2
        cx, cy = (ctr[s][0] - (int(mx - 280))) * 1.4, (ctr[s][1] - (int(my - 110))) * 1.4      # t48 expr frame, x1.4
        im = Image.fromarray((M.load(os.path.join(M.R, f"{t}_f6_expr_{p}_{a}.png")) * 255).astype(np.uint8))
        im = im.crop((int(cx - HW), int(cy - HW * 0.79), int(cx + HW), int(cy + HW * 0.79))).resize((TW, TH), Image.LANCZOS)
        S.paste(im, (LW + j * (TW + 4), 32 + i * (TH + 4)))
for i, (t, s) in enumerate(rows):
    d.text((6, 32 + i * (TH + 4) + TH // 2 - 10), f"{t} {'먼' if s == far else '가까운'} 눈", fill="black", font=F)
S.save(out)
print("EXPR_OK", out)
