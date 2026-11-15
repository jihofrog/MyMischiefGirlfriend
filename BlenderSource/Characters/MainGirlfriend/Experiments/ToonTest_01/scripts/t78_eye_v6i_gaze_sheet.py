"""ToonTest_01 step 78 (python with PIL): far eye x4 close ups at +-35 deg over the gaze range (t48 gaze=<name>:<rad>).

usage: python t78_eye_v6i_gaze_sheet.py <tag,tag,...> <out.png>
Columns: gaze 0.25 / 0.15 / 0.06 toward the character's left, 0, 0.06 / 0.15 / 0.25 toward the right; rows: tag x
(35 deg far right eye, -35 deg far left eye). Same crop for every image (middle of the t48 box).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
tags, out = sys.argv[1].split(","), sys.argv[2]
COLS = (("GazeLmax", "왼 0.25"), ("GazeL", "왼 0.15"), ("GazeLh", "왼 0.06"), ("", "0"), ("GazeRh", "오른 0.06"),
        ("GazeR", "오른 0.15"), ("GazeRmax", "오른 0.25"))
LAB = {"v6f_A": "A v6f_A", "v6i": "v6i 각도 보정", "v6j": "v6j 속눈썹 수정"}
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
TW, TH, LW = 170, 230, 210
rows = [(t, s, a) for t in tags for s, a in (("R", 35), ("L", -35))]
S = Image.new("RGB", (len(COLS) * (TW + 4) + LW, len(rows) * (TH + 4) + 30), "white")
d = ImageDraw.Draw(S)
for j, (g, lab) in enumerate(COLS):
    d.text((LW + j * (TW + 4), 4), f"시선 {lab}", fill="black", font=F)
    for i, (t, s, a) in enumerate(rows):
        im = Image.open(os.path.join(R, f"{t}_f6_{s}_toon{'_' + g if g else ''}_{a}.png")).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        w, h = im.size
        cw, ch = int(w * 0.42), int(w * 0.42 * TH / TW)
        x0, y0 = (w - cw) // 2, max(0, (h - ch) // 2)
        S.paste(bg.convert("RGB").crop((x0, y0, x0 + cw, y0 + ch)).resize((TW, TH), Image.LANCZOS), (LW + j * (TW + 4), 30 + i * (TH + 4)))
for i, (t, s, a) in enumerate(rows):
    d.text((6, 30 + i * (TH + 4) + TH // 2 - 12), f"{LAB.get(t, t)}\n{a}° 먼 {'오른' if s == 'R' else '왼'}눈", fill="black", font=F)
S.save(out)
print("GAZE_SHEET_OK", out)
