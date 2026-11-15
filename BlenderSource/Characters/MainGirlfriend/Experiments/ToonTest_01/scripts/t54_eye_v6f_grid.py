"""ToonTest_01 step 54 (python with PIL): v6f grid sheets of the t48 renders.

usage: python t54_eye_v6f_grid.py <tags,comma> <kind> <out.png>
kind faces / facesnh: whole face with / without hair at 0, +-35, +-45, +-60, +-90 (crop around the eyes);
expr<a>: the poses at angle a (expr35, expr-35, expr0).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 24)
LAB = {"v6d_3": "v6d_3 (기준)", "v6f_A": "A 눈꺼풀 경계", "v6f_B": "B 바깥 감싸기", "v6g_s": "v6g 눈꼬리 감싸기"}

if os.environ.get("LABSET") == "v6h":                 # v6h report: A / B / C1 / C2 (Unity copies get a suffix)
    LAB = {"v6f_A": "A v6f_A", "v6g_s": "B v6g_s 단차", "v6h_C1": "C1 눈꼬리 피부 0.85", "v6h_C2": "C2 눈꼬리 피부 0.70"}
    LAB.update({f"unity_{k}": f"{v} Unity" for k, v in list(LAB.items())})
POSES = ("Neutral", "Blink50", "Blink", "EyeSmile", "SmileEyeSmile", "Surprise", "GazeL", "GazeR")
PL = dict(Neutral="Neutral", Blink50="Blink 50%", Blink="Blink 100%", EyeSmile="EyeSmile", SmileEyeSmile="Smile+EyeSmile",
          Surprise="Surprise", GazeL="시선 왼쪽", GazeR="시선 오른쪽")


def w(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


tags, kind, out = sys.argv[1].split(","), sys.argv[2], sys.argv[3]
if kind.startswith("face"):
    pre = "face" if kind == "faces" else "facenh"
    cols = [(f"{pre}_{a}", f"{a}°") for a in (0, 35, -35, 45, -45, 60, -60, 90, -90)]
    crop, TW, TH = (60, 120, 800, 700), 260, 204
else:
    a = kind[4:]
    cols = [(f"expr_{p}_{a}", PL[p]) for p in POSES]
    crop, TW, TH = None, 300, 156
S = Image.new("RGB", (len(cols) * (TW + 6) + 170, len(tags) * (TH + 6) + 40), "white")
d = ImageDraw.Draw(S)
for j, (n, lab) in enumerate(cols):
    d.text((170 + j * (TW + 6), 6), lab, fill="black", font=F)
for i, t in enumerate(tags):
    d.text((6, 40 + i * (TH + 6) + TH // 2 - 12), LAB.get(t, t), fill="black", font=F)
    for j, (n, lab) in enumerate(cols):
        im = w(os.path.join(R, f"{t}_f6_{n}.png"))
        if crop:
            im = im.crop(crop)
        S.paste(im.resize((TW, TH), Image.LANCZOS), (170 + j * (TW + 6), 40 + i * (TH + 6)))
S.save(out)
print("GRID_OK", out)
