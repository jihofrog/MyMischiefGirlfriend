"""ToonTest_01 step 66 (python with PIL): v6g report sheet, far eye close ups (x4) at +35 / -35 / +45 / -45.

usage: python t66_eye_v6g_sheet.py <out.png> <label=pattern> ...
pattern: file name in renders/ with {s} (eye) and {a} (angle), e.g. "v6f_A_g6_marked_{s}_{a}.png". Every image is cut to
the middle of its eye box (same box for every row).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
out, rows = sys.argv[1], [r.split("=", 1) for r in sys.argv[2:]]
VIEWS = (("R", 35), ("L", -35), ("R", 45), ("L", -45))
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
TW, TH, LW = 300, 320, 240
S = Image.new("RGB", (len(VIEWS) * (TW + 6) + LW, len(rows) * (TH + 6) + 36), "white")
d = ImageDraw.Draw(S)
for j, (s, a) in enumerate(VIEWS):
    d.text((LW + j * (TW + 6), 6), f"{a}° 먼 {'오른' if s == 'R' else '왼'}눈", fill="black", font=F)
    for i, (_, pat) in enumerate(rows):
        im = Image.open(os.path.join(R, pat.format(s=s, a=a))).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        w, h = im.size
        cw, ch = int(w * 0.56), int(w * 0.56 * TH / TW)
        x0, y0 = (w - cw) // 2, max(0, (h - ch) // 2)
        S.paste(bg.convert("RGB").crop((x0, y0, x0 + cw, y0 + ch)).resize((TW, TH), Image.LANCZOS), (LW + j * (TW + 6), 36 + i * (TH + 6)))
for i, (lab, _) in enumerate(rows):
    d.multiline_text((6, 36 + i * (TH + 6) + TH // 2 - 24), lab.replace("|", "\n"), fill="black", font=F)
S.save(out)
print("SHEET66_OK", out)
