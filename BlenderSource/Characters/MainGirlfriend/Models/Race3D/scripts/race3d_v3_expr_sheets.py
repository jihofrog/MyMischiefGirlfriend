"""Race3D v3 expressions (python with PIL): review sheets of the second pass, with the v2 renders as "before".

usage: python race3d_v3_expr_sheets.py
Writes Models/Race3D/experiments/sheets_v3/: eyes.png (eyes + brows), faces.png (whole face), transition_strip.png and
transition_0.gif / _35.gif, before_after_eyes.png / before_after_faces.png (v2 -> v3), tear_flow.png.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EXPD = os.path.join(os.path.dirname(HERE), "experiments")
R3, R2 = os.path.join(EXPD, "renders_v3"), os.path.join(EXPD, "renders")
OUT = os.path.join(EXPD, "sheets_v3")
os.makedirs(OUT, exist_ok=True)
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
FS = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
ANG = ("0", "35", "-35", "45", "-45")
ROWS = ["Neutral", "Happy030", "Happy060", "Happy100", "Angry100", "Sad100", "Cry100", "Surprise100"]
LBL = {"Neutral": "Neutral", "Happy030": "Happy 0.3", "Happy060": "Happy 0.6", "Happy080": "Happy 0.8", "Happy100": "Happy 1.0",
       "Angry100": "Angry 1.0", "Sad100": "Sad 1.0", "Cry100": "Sad 1 + Cry 1.0", "Surprise100": "Surprise 1.0"}


def load(p, sc=1.0):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    return im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS) if sc != 1.0 else im


def grid(cells, rows, cols, out, title, row_label, col_label):
    W = max(i.width for i in cells.values())
    H = max(i.height for i in cells.values())
    LW, TH = 230, 70
    S = Image.new("RGB", (LW + len(cols) * (W + 4), TH + len(rows) * (H + 4)), "white")
    d = ImageDraw.Draw(S)
    d.text((8, 6), title, fill="black", font=F)
    for j, c in enumerate(cols):
        d.text((LW + j * (W + 4) + 4, TH - 28), col_label(c), fill="black", font=F)
    for i, r in enumerate(rows):
        d.text((6, TH + i * (H + 4) + H // 2 - 12), row_label(r), fill="black", font=F)
        for j, c in enumerate(cols):
            S.paste(cells[(r, c)], (LW + j * (W + 4), TH + i * (H + 4)))
    S.save(os.path.join(OUT, out))


deg = lambda c: f"{c}°" if c.startswith("-") or c == "0" else f"+{c}°"
grid({(r, c): load(os.path.join(R3, "express", f"{r}_eyes_{c}.png"), 0.4) for r in ROWS for c in ANG}, ROWS, ANG, "eyes.png",
     "v3 — 눈·눈썹 확대 (1.5배 렌더)", lambda r: LBL[r], deg)
grid({(r, c): load(os.path.join(R3, "express", f"{r}_face_{c}.png"), 0.5) for r in ROWS for c in ANG}, ROWS, ANG, "faces.png",
     "v3 — 얼굴 전체", lambda r: LBL[r], deg)
# before / after (v2 -> v3) at 0 and 35
BA = ["Happy030", "Happy060", "Happy100", "Angry100", "Sad100", "Cry100", "Surprise100"]
cols = [("v2", "0"), ("v3", "0"), ("v2", "35"), ("v3", "35")]
for kind, sc in (("eyes", 0.42), ("face", 0.5)):
    cells = {}
    for r in BA:
        for v, a in cols:
            cells[(r, (v, a))] = load(os.path.join(R2 if v == "v2" else R3, "express", f"{r}_{kind}_{a}.png"), sc)
    grid(cells, BA, cols, f"before_after_{kind}.png", f"수정 전(v2) → 수정 후(v3) — {'눈·눈썹' if kind == 'eyes' else '얼굴 전체'}",
         lambda r: LBL[r], lambda c: f"{'수정 전 v2' if c[0] == 'v2' else '수정 후 v3'} {deg(c[1])}")
# transition
frames = json.load(open(os.path.join(R3, "transition", "frames.json")))
for a in ("0", "35"):
    seq = [load(os.path.join(R3, "transition", f"t{a}_{i:02d}.png"), 0.6) for i in range(len(frames))]
    seq[0].save(os.path.join(OUT, f"transition_{a}.gif"), save_all=True, append_images=seq[1:] + [seq[-1]] * 6, duration=110, loop=0)
pick = list(range(0, len(frames), 2))
r0 = [load(os.path.join(R3, "transition", f"t0_{i:02d}.png"), 0.34) for i in pick]
r35 = [load(os.path.join(R3, "transition", f"t35_{i:02d}.png"), 0.34) for i in pick]
w, h = r0[0].size
S = Image.new("RGB", (len(pick) * (w + 2), 2 * (h + 2) + 32), "white")
d = ImageDraw.Draw(S)
d.text((6, 4), "v3 Neutral → Happy → Angry → Sad(+Cry 0.6) → Surprise, 2프레임 간격 (위 0°, 아래 35°)", fill="black", font=FS)
for k, (a, b) in enumerate(zip(r0, r35)):
    S.paste(a, (k * (w + 2), 32))
    S.paste(b, (k * (w + 2), 32 + h + 2))
S.save(os.path.join(OUT, "transition_strip.png"))
# tear flow mask
fl = ["000", "025", "050", "075", "100"]
cells = {(a, f): load(os.path.join(R3, "flow", f"CryFlow{f}_face_{a}.png"), 0.5) for a in ("0", "35") for f in fl}
grid(cells, ["0", "35"], fl, "tear_flow.png", "Cry 1.0 — 눈물 흐름 마스크 Flow 값 (0 → 1), 정지 시트 기본값 0.5",
     deg, lambda f: f"Flow {int(f) / 100:.2f}")
print("SHEETS_V3", sorted(os.listdir(OUT)))
