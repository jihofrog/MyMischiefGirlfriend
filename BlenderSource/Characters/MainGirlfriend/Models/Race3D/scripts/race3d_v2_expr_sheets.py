"""Race3D v2 expressions (python with PIL): review sheets from the renders of race3d_v2_expr_render.py.

usage: python race3d_v2_expr_sheets.py
Writes Models/Race3D/experiments/sheets/: compare_eyesmile.png, <emotion>.png (face x1 / eyes + brows / mouth per
angle and intensity), all_faces.png, transition_0.gif / _35.gif and transition_strip.png.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(os.path.dirname(HERE), "experiments", "renders")
OUT = os.path.join(os.path.dirname(HERE), "experiments", "sheets")
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
ANG = ("0", "35", "-35", "45", "-45")


def load(p, sc=1.0):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    return im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS) if sc != 1.0 else im


def grid(rows, cols, path_fn, sc, out, title=None, row_label=lambda r: r, col_label=lambda c: f"{c}°"):
    ims = {(r, c): load(path_fn(r, c), sc) for r in rows for c in cols}
    W = max(i.width for i in ims.values())
    H = max(i.height for i in ims.values())
    LW, TH = 200, 34 + (34 if title else 0)
    S = Image.new("RGB", (LW + len(cols) * (W + 4), TH + len(rows) * (H + 4)), "white")
    d = ImageDraw.Draw(S)
    if title:
        d.text((8, 6), title, fill="black", font=F)
    for j, c in enumerate(cols):
        d.text((LW + j * (W + 4) + 4, TH - 28), col_label(c), fill="black", font=F)
    for i, r in enumerate(rows):
        d.text((6, TH + i * (H + 4) + H // 2 - 12), row_label(r), fill="black", font=F)
        for j, c in enumerate(cols):
            S.paste(ims[(r, c)], (LW + j * (W + 4), TH + i * (H + 4)))
    S.save(os.path.join(OUT, out))
    return S.size


LBL = {"OldEyeSmile050": "현재 EyeSmile 0.5", "OldEyeSmile100": "현재 EyeSmile 1.0", "NewHappy030": "새 Happy 0.3",
       "NewHappy060": "새 Happy 0.6", "NewHappy100": "새 Happy 1.0", "Neutral": "Neutral",
       "Happy030": "Happy 0.3", "Happy060": "Happy 0.6", "Happy100": "Happy 1.0", "Angry050": "Angry 0.5", "Angry100": "Angry 1.0",
       "Sad050": "Sad 0.5", "Sad100": "Sad 1.0", "Cry050": "Sad 1 + Cry 0.5", "Cry100": "Sad 1 + Cry 1.0",
       "Surprise050": "Surprise 0.5", "Surprise100": "Surprise 1.0"}
grid(["OldEyeSmile050", "OldEyeSmile100", "NewHappy030", "NewHappy060", "NewHappy100"], ANG,
     lambda r, c: os.path.join(R, "compare", f"{r}_{c}.png"), 0.42, "compare_eyesmile.png",
     "현재 EyeSmile 대 새 Happy 눈 (같은 카메라, 눈·눈썹·볼만)", lambda r: LBL[r])
EMO = {"happy": ["Neutral", "Happy030", "Happy060", "Happy100"], "angry": ["Neutral", "Angry050", "Angry100"],
       "sad": ["Neutral", "Sad050", "Sad100", "Cry050", "Cry100"], "surprise": ["Neutral", "Surprise050", "Surprise100"]}
for e, rows in EMO.items():
    grid(rows, ANG, lambda r, c: os.path.join(R, "express", f"{r}_face_{c}.png"), 0.5, f"{e}_face.png", f"{e} — 얼굴 전체", lambda r: LBL[r])
    grid(rows, ANG, lambda r, c: os.path.join(R, "express", f"{r}_eyes_{c}.png"), 0.4, f"{e}_eyes.png", f"{e} — 눈·눈썹 확대 (1.5배)", lambda r: LBL[r])
    grid(rows, ANG, lambda r, c: os.path.join(R, "express", f"{r}_mouth_{c}.png"), 0.45, f"{e}_mouth.png", f"{e} — 입 확대 (4배)", lambda r: LBL[r])
grid(["Neutral", "Happy060", "Happy100", "Angry100", "Sad100", "Cry100", "Surprise100"], ANG,
     lambda r, c: os.path.join(R, "express", f"{r}_face_{c}.png"), 0.42, "all_faces.png", "네 감정 + Neutral (강도 1.0, Happy 0.6 포함)", lambda r: LBL[r])
# transition
frames = json.load(open(os.path.join(R, "transition", "frames.json")))
for a in ("0", "35"):
    seq = [load(os.path.join(R, "transition", f"t{a}_{i:02d}.png"), 0.6) for i in range(len(frames))]
    seq[0].save(os.path.join(OUT, f"transition_{a}.gif"), save_all=True, append_images=seq[1:] + [seq[-1]] * 6, duration=110, loop=0)
pick = list(range(0, len(frames), 2))
row = [load(os.path.join(R, "transition", f"t0_{i:02d}.png"), 0.32) for i in pick]
row35 = [load(os.path.join(R, "transition", f"t35_{i:02d}.png"), 0.32) for i in pick]
w, h = row[0].size
S = Image.new("RGB", (len(pick) * (w + 2), 2 * (h + 2) + 30), "white")
d = ImageDraw.Draw(S)
d.text((6, 4), "Neutral → Happy → Angry → Sad(+Cry 0.6) → Surprise, 2프레임 간격 (위 0°, 아래 35°)", fill="black", font=FS)
for k, (a, b) in enumerate(zip(row, row35)):
    S.paste(a, (k * (w + 2), 30))
    S.paste(b, (k * (w + 2), 30 + h + 2))
S.save(os.path.join(OUT, "transition_strip.png"))
print("SHEETS", sorted(os.listdir(OUT)))
