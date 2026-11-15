"""ToonTest_01 step 76 (python with PIL): far eye cut from the x1 face renders (t48 face_ / facenh_), any angle.

usage: python t76_eye_v6i_far_face.py <tag,tag,...> <angle,angle,...> <face|facenh> <out.png> [half-width px, default 70]
The far eye is R for + angles, L for -; its centre comes from spec/eye_f6_boxes_v6i.json (t55). Labels by LABSET=v6h.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
tags, angs, kind, out = sys.argv[1].split(","), [int(a) for a in sys.argv[2].split(",")], sys.argv[3], sys.argv[4]
HW = int(sys.argv[5]) if len(sys.argv) > 5 else 70
BOX = json.load(open(os.path.join(EXP, "spec", "eye_f6_boxes_v6i.json")))
LAB = {"v6f_A": "A v6f_A", "v6i": "v6i 각도 보정", "v6g_s": "B v6g_s", "unity_v6f_A": "A Unity", "unity_v6i": "v6i Unity", "v6j": "v6j", "unity_v6j": "v6j Unity", "unity_v6jm": "v6j Unity 재질 수정"}
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
TW, TH, LW = 260, int(260 * 0.8), 170
S = Image.new("RGB", (len(angs) * (TW + 6) + LW, len(tags) * (TH + 6) + 34), "white")
d = ImageDraw.Draw(S)
for j, a in enumerate(angs):
    s = "R" if a > 0 else "L"
    b = BOX[f"{s}_{a}"]
    cx, cy = (b[0] + b[2]) / 2 - 600, (b[1] + b[3]) / 2
    d.text((LW + j * (TW + 6), 6), f"{a}° 먼 {'오른' if s == 'R' else '왼'}눈", fill="black", font=F)
    for i, t in enumerate(tags):
        im = Image.open(os.path.join(R, f"{t}_f6_{kind}_{a}.png")).convert("RGB")
        im = im.crop((int(cx - HW), int(cy - HW * 0.8), int(cx + HW), int(cy + HW * 0.8))).resize((TW, TH), Image.LANCZOS)
        S.paste(im, (LW + j * (TW + 6), 34 + i * (TH + 6)))
for i, t in enumerate(tags):
    d.text((6, 34 + i * (TH + 6) + TH // 2 - 12), LAB.get(t, t), fill="black", font=F)
S.save(out)
print("FARFACE_OK", out)
