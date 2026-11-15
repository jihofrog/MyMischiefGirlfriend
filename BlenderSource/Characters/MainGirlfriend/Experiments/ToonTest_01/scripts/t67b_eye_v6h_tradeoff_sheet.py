"""ToonTest_01 step 67b (python with numpy / PIL): picture of t67 (/tmp/v6h_tradeoff_<s>_<a>.npy).

usage: python t67b_eye_v6h_tradeoff_sheet.py
Visible eyeball of one eye per view: grey = iris side / other eyeball, colour = outer white by rho (front iris-ellipse
radius, blue 1.0 -> red 1.6), the line marks rho = 1.1. Writes renders/compare_eye_v6h_tradeoff.png.
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = json.load(open(os.path.join(EXP, "spec", "eye_v6h_tradeoff.json")))
VIEWS = (("R", 35, "35° 먼 오른눈"), ("L", 0, "0° 정면 왼눈"), ("L", 35, "35° 가까운 왼눈"), ("L", 90, "90° 가까운 왼눈"))
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
TW, TH = 300, 212
S = Image.new("RGB", (len(VIEWS) * (TW + 8) + 8, TH + 150), "white")
d = ImageDraw.Draw(S)
for j, (s, a, lab) in enumerate(VIEWS):
    img = np.load(f"/tmp/v6h_tradeoff_{s}_{a}.npy")
    H, W = img.shape
    rgb = np.full((H, W, 3), 255, np.uint8)
    rgb[img == 0] = (165, 165, 165)
    m = img > 0
    k = np.clip((img - 1.0) / 0.6, 0, 1)
    col = np.stack([60 + 195 * k, 90 + 0 * k, 255 - 195 * k], -1)
    rgb[m] = col[m].astype(np.uint8)
    edge = m & (np.abs(img - 1.1) < 0.006)
    rgb[edge] = (0, 0, 0)
    x0 = 8 + j * (TW + 8)
    S.paste(Image.fromarray(rgb).resize((TW, TH), Image.NEAREST), (x0, 30))
    d.text((x0, 4), lab, fill="black", font=F)
    h = J[f"{s}_{a}"]["hidden_share"]
    d.text((x0, TH + 38), f"바깥 흰자 중 가려지는 비율\nrho>1.05: {h['1.05']:.0%}\nrho>1.1: {h['1.1']:.0%}\nrho>1.2: {h['1.2']:.0%}",
           fill="black", font=F)
S.save(os.path.join(EXP, "renders", "compare_eye_v6h_tradeoff.png"))
print("TRADEOFF_SHEET_OK")
