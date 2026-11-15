"""ToonTest_01 step 79 (python with PIL): whole face (eyes) at 0, +-15, +-25, +-35, +-45, +-60, +-90 per tag.

usage: python t79_eye_v6i_faces.py <tag,tag,...> <face|facenh> <out.png>
Crop (600 + 130, 330) - (600 + 730, 650) of the x1 face renders (t48 / u11).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
tags, kind, out = sys.argv[1].split(","), sys.argv[2], sys.argv[3]
ANG = (90, 60, 45, 35, 25, 15, 0, -15, -25, -35, -45, -60, -90)
LAB = {"v6f_A": "A v6f_A", "v6i": "v6i", "v6j": "v6j", "unity_v6f_A": "A Unity", "unity_v6i": "v6i Unity", "unity_v6j": "v6j Unity"}
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
TW, TH, LW = 150, 80, 110
S = Image.new("RGB", (len(ANG) * (TW + 3) + LW, len(tags) * (TH + 3) + 26), "white")
d = ImageDraw.Draw(S)
for j, a in enumerate(ANG):
    d.text((LW + j * (TW + 3), 3), f"{a}°", fill="black", font=F)
    for i, t in enumerate(tags):
        im = Image.open(os.path.join(R, f"{t}_f6_{kind}_{a}.png")).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        S.paste(bg.convert("RGB").crop((130, 330, 730, 650)).resize((TW, TH), Image.LANCZOS), (LW + j * (TW + 3), 26 + i * (TH + 3)))
for i, t in enumerate(tags):
    d.text((4, 26 + i * (TH + 3) + TH // 2 - 10), LAB.get(t, t), fill="black", font=F)
S.save(out)
print("FACES_OK", out)
