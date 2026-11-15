"""ToonTest_01 step 53 (python with numpy / PIL): v6f close-up comparison sheets.

usage: python t53_eye_v6f_sheet.py <tags,comma> <views,comma e.g. R_35,L_-35> <kind: toon|hair|id|rim> <out.png> [pad]
Each view is cropped to the eyeball of the first tag (flat colour id) + pad px, the same crop for every tag.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
LAB = {"v6d_3": "v6d_3 (기준)", "v6f_A": "A 눈꺼풀 경계", "v6f_B": "B 바깥 감싸기"}

if os.environ.get("LABSET") == "v6h":                 # v6h report: A / B / C1 / C2 (Unity copies get a suffix)
    LAB = {"v6f_A": "A v6f_A", "v6g_s": "B v6g_s 단차", "v6h_C1": "C1 눈꼬리 피부 0.85", "v6h_C2": "C2 눈꼬리 피부 0.70"}
    LAB.update({f"unity_{k}": f"{v} Unity" for k, v in list(LAB.items())})


def w(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


tags, views, kind, out = sys.argv[1].split(","), sys.argv[2].split(","), sys.argv[3], sys.argv[4]
pad = int(sys.argv[5]) if len(sys.argv) > 5 else 70
crops = {}
for v in views:
    s, a = v.split("_")
    idm = np.asarray(w(os.path.join(R, f"{tags[0]}_f6_{s}_id_{a}.png"))).astype(float) / 255
    g = (np.abs(idm - np.array([0.35, 0.93, 0.49])).sum(2) < 0.25)
    lab, n = label(g)
    if n:
        g = lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:])))
    ys, xs = np.nonzero(g)
    if len(xs) == 0:
        crops[v] = (0, 0, idm.shape[1], idm.shape[0])
        continue
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    hw = max(xs.max() - xs.min(), (ys.max() - ys.min()) * 0.75) / 2 + pad
    hh = hw / 0.75
    crops[v] = (int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh))
TW, TH = 330, 440
S = Image.new("RGB", (len(views) * (TW + 8) + 200, len(tags) * (TH + 8) + 44), "white")
d = ImageDraw.Draw(S)
for j, v in enumerate(views):
    s, a = v.split("_")
    role = "정면" if a == "0" else ("먼 눈" if (int(a) > 0) == (s == "R") else "가까운 눈")
    d.text((200 + j * (TW + 8), 6), f"{'오른' if s == 'R' else '왼'}눈 {a}° {role}", fill="black", font=F)
for i, t in enumerate(tags):
    d.text((6, 44 + i * (TH + 8) + TH // 2 - 15), LAB.get(t, t), fill="black", font=F)
    for j, v in enumerate(views):
        s, a = v.split("_")
        name = f"{t}_f6_rim_{v}.png" if kind == "rim" else f"{t}_f6_{s}_{kind}_{a}.png"
        im = w(os.path.join(R, name)).crop(crops[v]).resize((TW, TH), Image.LANCZOS)
        S.paste(im, (200 + j * (TW + 8), 44 + i * (TH + 8)))
S.save(out)
print("SHEET_OK", out)
