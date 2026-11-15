"""ToonTest_01 step 61 (python with numpy / PIL): put the t60 2D mock-ups of the far eye back into the whole face.

usage: python t61_eye_v6g_face2d.py <tag> <fix,fix,...>
For +-35 / +-45: the change of the far eye close up (x4) is scaled to the face render (x1, with and without hair; with
hair only where the hair does not cover the eye) and added. Writes renders/<tag>_g6_face_<fix>_<a>.png and
renders/<tag>_g6_facenh_<fix>_<a>.png, and renders/compare_eye_v6g_face2d_<tag>.png (rows: original / fixes, columns:
+35 / -35 / +45 / -45 with hair, crop around the far eye).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

tag, fixes = sys.argv[1], sys.argv[2].split(",")
BOX = json.load(open(os.path.join(M.EXP, "spec", f"eye_f6_boxes_{tag}.json")))
VIEWS = (("R", 35), ("L", -35), ("R", 45), ("L", -45))


def small(a, size):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize(size, Image.LANCZOS)).astype(float) / 255


for s, a in VIEWS:
    x0, y0, x1, y1 = BOX[f"{s}_{a}"]
    size = (x1 - x0, y1 - y0)
    toon = M.load(os.path.join(M.R, f"{tag}_f6_{s}_toon_{a}.png"))
    hairc = M.load(os.path.join(M.R, f"{tag}_f6_{s}_hair_{a}.png"))
    free = small((np.abs(hairc - toon).sum(2) < 0.06).astype(float)[..., None].repeat(3, 2), size)[..., :1] > 0.9
    for fx in fixes:
        fixed = M.load(os.path.join(M.R, f"{tag}_g6_{fx}_{s}_{a}.png"))
        delta = small(fixed, size) - small(toon, size)
        for kind, use_free in (("facenh", False), ("face", True)):
            face = M.load(os.path.join(M.R, f"{tag}_f6_{kind}_{a}.png"))
            fx0, fy0 = x0 - 600, y0
            reg = face[fy0:fy0 + size[1], fx0:fx0 + size[0]]
            dd = delta[:reg.shape[0], :reg.shape[1]]
            if use_free:
                dd = dd * free[:reg.shape[0], :reg.shape[1]]
            face[fy0:fy0 + size[1], fx0:fx0 + size[0]] = np.clip(reg + dd, 0, 1)
            Image.fromarray((face * 255).astype(np.uint8)).save(os.path.join(M.R, f"{tag}_g6_{kind}_{fx}_{a}.png"))

F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
TW, TH = 380, 300
rows = ["orig"] + fixes
S = Image.new("RGB", (len(VIEWS) * (TW + 6) + 130, len(rows) * (TH + 6) + 36), "white")
d = ImageDraw.Draw(S)
for j, (s, a) in enumerate(VIEWS):
    d.text((130 + j * (TW + 6), 6), f"{a}° 먼 {'오른' if s == 'R' else '왼'}눈, 머리카락 포함 (x1 렌더 확대)", fill="black", font=F)
    for i, r in enumerate(rows):
        p = os.path.join(M.R, f"{tag}_f6_face_{a}.png" if r == "orig" else f"{tag}_g6_face_{r}_{a}.png")
        im = Image.fromarray((M.load(p) * 255).astype(np.uint8))
        bx = BOX[f"{s}_{a}"]
        cx, cy = (bx[0] + bx[2]) / 2 - 600 + (25 if s == "R" else -25), (bx[1] + bx[3]) / 2 + 5
        im = im.crop((int(cx - 120), int(cy - 95), int(cx + 120), int(cy + 95))).resize((TW, TH), Image.LANCZOS)
        S.paste(im, (130 + j * (TW + 6), 36 + i * (TH + 6)))
for i, r in enumerate(rows):
    d.text((6, 36 + i * (TH + 6) + TH // 2), {"orig": "원본", "fixO": "윤곽선 연장", "fixW": "눈꼬리 감싸기"}.get(r, r), fill="black", font=F)
S.save(os.path.join(M.R, f"compare_eye_v6g_face2d_{tag}.png"))
print("FACE2D_OK")
