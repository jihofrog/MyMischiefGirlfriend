"""ToonTest_01 step 21 (system python + Pillow): draw spec/eye_section_L.json (from t20_eye_survey.py) as
renders/eye_survey_section.png: vertical section through the left eye centre, depth y to the left = toward the viewer."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sec = json.load(open(os.path.join(EXP, "spec", "eye_section_L.json")))
cz = json.load(open(os.path.join(EXP, "spec", "eye_survey.json")))["eye_L_centre"][1]
S = 12000.0                                                           # px per metre (1 cm = 120 px)
eye_y = min(p[0] for k, v in sec.items() if k != "head" for p in v)
y0, z0 = eye_y - 0.006, cz + 0.032
W, Hh = int(0.05 * S) + 300, int(0.064 * S) + 60
img = Image.new("RGB", (W, Hh), (255, 255, 255)); d = ImageDraw.Draw(img)
f = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
T = lambda y, z: (20 + (y - y0) * S, 20 + (z0 - z) * S)
head = sorted((p for p in sec["head"] if abs(p[1] - cz) < 0.032), key=lambda p: -p[1])
d.line([T(*p) for p in head], fill=(230, 150, 120), width=4)
cols = {"Eye_White.L": (90, 90, 220), "Eye_Iris.L": (170, 70, 40), "Eye_UpperLid.L": (40, 160, 60), "Face_Blush.L": (240, 120, 160)}
yl = 20
for k, pts in sorted(sec.items()):
    if k == "head":
        continue
    c = cols.get(k, (100, 100, 100))
    for y, z in pts:
        if abs(z - cz) < 0.032:
            x_, y_ = T(y, z); d.ellipse([x_ - 3, y_ - 3, x_ + 3, y_ + 3], fill=c)
    d.text((W - 270, yl), k, fill=c, font=f); yl += 24
d.text((W - 270, yl), "Blockout_Head (skin)", fill=(230, 150, 120), font=f)
d.line([(20, Hh - 25), (20 + 0.01 * S, Hh - 25)], fill=(0, 0, 0), width=3)
d.text((30 + 0.01 * S, Hh - 36), "1 cm   (left = toward the viewer)", fill=(60, 60, 60), font=f)
img.save(os.path.join(EXP, "renders", "eye_survey_section.png"))
print("SECTION", img.size)
