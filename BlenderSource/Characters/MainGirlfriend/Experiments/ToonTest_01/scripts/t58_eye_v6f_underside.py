"""ToonTest_01 step 58 (python with numpy / scipy / PIL): where the lid underside shows (far eye), before / after.

usage: python t58_eye_v6f_underside.py <tags,comma> <views,comma> <out.png>
Per view and tag: toon close up of the outer half of the eyeball, and the same with the lid sheet back faces (looking into
the gap between lid and eyeball) painted magenta, lid sheet front faces blue, bare face skin next to the eyeball yellow.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, label

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 24)
LAB = {"v6d_3": "v6d_3 (기준)", "v6f_A": "A 눈꺼풀 경계", "v6f_B": "B 바깥 감싸기"}
tags, views, out = sys.argv[1].split(","), sys.argv[2].split(","), sys.argv[3]
TW, TH = 300, 420
S = Image.new("RGB", (len(views) * 2 * (TW + 6) + 200, len(tags) * (TH + 6) + 44), "white")
d = ImageDraw.Draw(S)
for j, v in enumerate(views):
    s, a = v.split("_")
    lab0 = M.labels(os.path.join(M.R, f"{tags[0]}_f6_{s}_id_{a}.png"))
    g0 = M.group(lab0) == "ball"
    lb, n = label(g0)
    g0 = lb == (1 + int(np.argmax(np.bincount(lb.ravel())[1:])))
    ys, xs = np.nonzero(g0)
    outer_left = s == "R"                            # far eye: the outer side faces the face outline
    w = (xs.max() - xs.min())
    x0 = xs.min() - 50 if outer_left else xs.max() - int(w * 0.6)
    crop = (int(x0), int(ys.min() - 40), int(x0 + w * 0.6 + 50), int(ys.max() + 30))
    d.text((200 + j * 2 * (TW + 6), 6), f"{'오른' if s == 'R' else '왼'}눈 {a}° 먼 눈 바깥쪽: 일반 / 구분색", fill="black", font=F)
    for i, t in enumerate(tags):
        lab, back = M.labels(os.path.join(M.R, f"{t}_f6_{s}_id_{a}.png"), back=True)
        g = M.group(lab)
        toon = M.load(os.path.join(M.R, f"{t}_f6_{s}_toon_{a}.png"))
        vis = toon * 0.5 + 0.5
        ball = g == "ball"
        ring = binary_dilation(ball, iterations=4) & ~ball
        vis[(g == "lid") & ~back] = (0.2, 0.4, 1.0)
        vis[(g == "lid") & back] = (1.0, 0.0, 1.0)
        vis[ring & (g == "skin")] = (1.0, 0.85, 0.0)
        for k, im in enumerate((toon, vis)):
            pil = Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).crop(crop).resize((TW, TH), Image.LANCZOS)
            S.paste(pil, (200 + (2 * j + k) * (TW + 6), 44 + i * (TH + 6)))
        d.text((6, 44 + i * (TH + 6) + TH // 2), LAB.get(t, t), fill="black", font=F)
S.save(out)
print("UNDERSIDE_OK", out)
