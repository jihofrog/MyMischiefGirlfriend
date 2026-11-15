"""Race3D v3b expressions: comparison sheets and GIFs (plain python + Pillow, no Blender).

usage: python race3d_v3b_expr_sheets.py
Reads experiments/renders_v3 (before), experiments/renders_v3b (Blender) and experiments/unity_v3b (Unity play mode,
Race3DExprCheck) and writes experiments/sheets_v3b/*.png / *.gif.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(os.path.dirname(HERE), "experiments")
V3, V3B, UNI = (os.path.join(EXP, d) for d in ("renders_v3", "renders_v3b", "unity_v3b"))
OUT = os.path.join(EXP, "sheets_v3b")
os.makedirs(OUT, exist_ok=True)
FONT = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
SMALL = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 16)


def load(p):
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def grid(name, rows, cols, scale, title=None, label_w=170):
    """rows: [(label, [path or None, ...])], cols: column labels"""
    first = next(load(p) for _, ps in rows for p in ps if p and os.path.exists(p))
    w, h = int(first.width * scale), int(first.height * scale)
    top = 30 + (30 if title else 0)
    S = Image.new("RGB", (label_w + w * len(cols), top + h * len(rows)), "white")
    d = ImageDraw.Draw(S)
    if title:
        d.text((8, 4), title, fill="black", font=FONT)
    for j, c in enumerate(cols):
        d.text((label_w + j * w + 6, top - 26), c, fill="black", font=FONT)
    for i, (lab, ps) in enumerate(rows):
        y = top + i * h
        for k, line in enumerate(lab.split("\n")):
            d.text((6, y + h // 2 - 12 + 20 * k - 10 * (lab.count("\n"))), line, fill="black", font=SMALL)
        for j, p in enumerate(ps):
            im = load(p) if p else None
            if im is None:
                d.text((label_w + j * w + 10, y + 10), "-", fill="grey", font=FONT)
                continue
            S.paste(im.resize((w, h), Image.LANCZOS), (label_w + j * w, y))
        d.line([(0, y), (S.width, y)], fill=(225, 225, 225))
    path = os.path.join(OUT, name)
    S.save(path)
    print(path, S.size)
    return path


def gif(name, paths, scale, ms=90, pingpong=True, label=None):
    ims = []
    for i, p in enumerate(paths):
        im = load(p)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        if label:
            ImageDraw.Draw(im).text((8, 6), label(i), fill="black", font=FONT)
        ims.append(im)
    if pingpong:
        ims = ims + ims[-2:0:-1]
    path = os.path.join(OUT, name)
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=ms, loop=0)
    print(path, len(ims))


A5 = (0, 35, -35, 45, -45)

# 1. v3 -> v3b (fixed candidate)
rows = []
for n, n3 in (("Happy080", "Happy080"), ("Happy100", "Happy100"), ("Angry100", "Angry100"), ("Angry2_100", None),
              ("Cry100", "Cry100"), ("Surprise100", "Surprise100")):
    rows.append((f"{n}\nv3", [os.path.join(V3, "express", f"{n3}_eyes_{a}.png") if n3 else None for a in (0, 35, -45)]))
    rows.append((f"{n}\nv3b", [os.path.join(V3B, "express", f"{n}_eyes_{a}.png") for a in (0, 35, -45)]))
grid("compare_v3_v3b_eyes.png", rows, ["0", "35", "-45"], 0.42, "v3 (before) / v3b (fixed candidate) - eyes; Angry2 = new stronger candidate (v3 has none)")
rows = []
for n in ("Happy080", "Angry100", "Cry100", "Surprise100"):
    rows.append((f"{n}\nv3", [os.path.join(V3, "express", f"{n}_face_{a}.png") for a in (0, 35)]))
    rows.append((f"{n}\nv3b", [os.path.join(V3B, "express", f"{n}_face_{a}.png") for a in (0, 35)]))
rows.append(("Angry2_100\nv3b", [os.path.join(V3B, "express", f"Angry2_100_face_{a}.png") for a in (0, 35)]))
grid("compare_v3_v3b_face.png", rows, ["0", "35"], 0.55, "v3 / v3b - face")

# 2. Happy 0.6 .. 1.0
rows = [(f"Happy {h / 100:.1f}", [os.path.join(V3B, "happy", f"Happy{h:03d}_eyes_{a}.png") for a in A5]) for h in (60, 70, 80, 90, 100)]
grid("happy_steps.png", rows, [str(a) for a in A5], 0.36, "Happy 0.6 - 1.0 (v3b: A 0-0.6, A->C 0.6-0.85, C->B 0.85-1.0)")
rows = [(f"Happy {h / 100:.1f}\n{t}", [os.path.join(V3B if t == "Blender" else UNI, "happy", f"Happy{h:03d}_eyes_{a}.png") for a in (0, 35, -45)])
        for h in (70, 80, 90) for t in ("Blender", "Unity")]
grid("happy_steps_unity.png", rows, ["0", "35", "-45"], 0.36, "Happy 0.7 / 0.8 / 0.9 - Blender and Unity")
for a in (0, 35):
    gif(f"happy_steps_{a}.gif", [os.path.join(V3B, "happy", "seq", f"s{a}_{k:02d}.png") for k in range(17)], 1.0, 90,
        label=lambda i: f"Happy {0.6 + 0.025 * i:.3f}")

# 3. Angry brows: hide (bangs hide them, r30) / over (v3: card over every hair pixel) / pull (v3b: card 30 mm toward the camera, depth tested)
rows = []
for n in ("Angry100", "Angry2_100"):
    for m in ("hide", "over", "pull"):
        rows.append((f"{n}\n{m}", [os.path.join(V3B, "angrybrow", f"{n}_{m}_eyes_{a}.png") for a in A5]))
    rows.append((f"{n}\npull Unity", [os.path.join(UNI, "angrybrow", f"{n}_pull_eyes_{a}.png") for a in A5]))
grid("angry_brow.png", rows, [str(a) for a in A5], 0.36, "Angry brows: hide / over (v3) / pull 30 mm (v3b, recommended) / Unity stencil + pull")
rows = [(n, [os.path.join(V3B, "angrybrow", f"{n}_pull_face_{a}.png") for a in A5]) for n in ("Angry100", "Angry2_100")]
rows += [(f"{n}\nUnity", [os.path.join(UNI, "angrybrow", f"{n}_pull_face_{a}.png") for a in A5]) for n in ("Angry100", "Angry2_100")]
grid("angry_face.png", rows, [str(a) for a in A5], 0.42, "Angry (kept) / Angry2 (stronger candidate) - face, brows pull")


def brow_crop(src, dst_name, cases, angles):
    """the brow band of the eyes shots, larger"""
    cells = []
    for lab, path_fn in cases:
        for a in angles:
            im = load(path_fn(a))
            if im is None:
                continue
            cells.append((f"{lab} {a}", im.crop((60, 0, 810, 200)).resize((525, 140), Image.LANCZOS)))
    cols = len(angles)
    W, H = 525, 140 + 24
    S = Image.new("RGB", (W * cols, H * ((len(cells) + cols - 1) // cols)), "white")
    d = ImageDraw.Draw(S)
    for i, (lab, im) in enumerate(cells):
        x, y = (i % cols) * W, (i // cols) * H
        S.paste(im, (x, y + 24))
        d.text((x + 6, y + 2), lab, fill="black", font=SMALL)
    S.save(os.path.join(OUT, dst_name))
    print(dst_name, S.size)


brow_crop(V3B, "angry_brow_zoom.png",
          [(f"{n} {m}", (lambda a, n=n, m=m: os.path.join(V3B, "angrybrow", f"{n}_{m}_eyes_{a}.png"))) for n in ("Angry100",) for m in ("hide", "over", "pull")]
          + [("Angry100 pull Unity", lambda a: os.path.join(UNI, "angrybrow", f"Angry100_pull_eyes_{a}.png"))],
          (0, 45, -45))

# 4. Cry flow
rows = []
for a in (0, 35, -35):
    rows.append((f"{a} Blender", [os.path.join(V3B, "cry", f"Flow{f:03d}_face_{a}.png") for f in (0, 25, 50, 75, 100)]))
    rows.append((f"{a} Unity", [os.path.join(UNI, "cry", f"Flow{f:03d}_face_{a}.png") for f in (0, 25, 50, 75, 100)]))
grid("cry_flow.png", rows, ["Flow 0", "0.25", "0.5", "0.75", "1.0"], 0.42, "Cry (Sad 1, Cry 1): tear stream Flow 0 -> 1")
rows = [(t, [os.path.join(V3B if t == "Blender" else UNI, "cry", f"Flow100_eyes_{a}.png") for a in (0, 35, -35)]) for t in ("Blender", "Unity")]
grid("cry_eyes.png", rows, ["0", "35", "-35"], 0.42, "Cry Flow 1.0 - eyes")
CW, CH = 300, 170
S = Image.new("RGB", (110 + CW * 5, 24 + CH * 6), "white")
d = ImageDraw.Draw(S)
for j, f in enumerate((0, 0.25, 0.5, 0.75, 1.0)):
    d.text((110 + j * CW + 4, 2), f"Flow {f}", fill="black", font=SMALL)
for i, (a, t) in enumerate((a, t) for a in (0, 35, -35) for t in ("Blender", "Unity")):
    d.text((4, 24 + i * CH + CH // 2 - 10), f"{a} {t}", fill="black", font=SMALL)
    for j, f in enumerate((0, 25, 50, 75, 100)):
        im = load(os.path.join(V3B if t == "Blender" else UNI, "cry", f"Flow{f:03d}_face_{a}.png"))
        S.paste(im.crop((80, 170, 520, 420)).resize((CW, CH), Image.LANCZOS), (110 + j * CW, 24 + i * CH))
S.save(os.path.join(OUT, "cry_flow_zoom.png"))
print("cry_flow_zoom.png", S.size)

# 5. Surprise x gaze
rows = []
for sv in (50, 100):
    for a in (0, 35, -35):
        for t in ("Blender", "Unity"):
            rows.append((f"S {sv / 100:.1f} {a}\n{t}", [os.path.join(V3B if t == "Blender" else UNI, "surprise", f"S{sv:03d}_g{g}_eyes_{a}.png")
                                                        for g in ("-0.25", "+0.00", "+0.25")]))
grid("surprise_gaze.png", rows, ["gaze -0.25", "gaze 0", "gaze +0.25"], 0.36, "Surprise 0.5 / 1.0 x gaze (sparkle and iris scale follow the gaze)")

# 6. view correction x emotions (hair off)
states = ("Neutral", "Happy060", "Angry100", "Sad100", "Cry100", "Surprise100", "Surprise100_gR", "Angry100_b05")
for a in (35, 45, 60):
    rows = []
    for n in states:
        rows.append((n, [os.path.join(V3B, "view", f"{n}_noview_{a}.png"), os.path.join(V3B, "view", f"{n}_view_{a}.png"),
                         os.path.join(UNI, "view", f"{n}_view_{a}.png"), os.path.join(V3B, "view", f"{n}_noview_{-a}.png"),
                         os.path.join(V3B, "view", f"{n}_view_{-a}.png"), os.path.join(UNI, "view", f"{n}_view_{-a}.png")]))
    grid(f"view_{a}.png", rows, [f"{a} off", f"{a} on", f"{a} Unity", f"{-a} off", f"{-a} on", f"{-a} Unity"], 0.26,
         f"v6j view correction x emotions at +-{a} (hair off): off / on (Blender) / Unity")

# 7. Unity vs Blender transition and play sweep
for a in (0, 35):
    fr = (0, 4, 8, 12, 16, 20, 24, 28, 32)
    rows = [(t, [os.path.join(V3B if t == "Blender" else UNI, "transition", f"t{a}_{f:02d}.png") for f in fr]) for t in ("Blender", "Unity")]
    grid(f"transition_{a}_unity_blender.png", rows, [f"f{f}" for f in fr], 0.3, f"Neutral > Happy > Angry > Sad+Cry > Surprise at {a} (8 steps each)")
sweep = sorted(f for f in os.listdir(os.path.join(UNI, "sweep")) if f.endswith(".png"))
gif("unity_play_sweep.gif", [os.path.join(UNI, "sweep", f) for f in sweep], 0.8, 250, pingpong=False)
rows = [("", [os.path.join(UNI, "sweep", f) for f in sweep[i:i + 8]]) for i in range(0, len(sweep), 8)]
grid("unity_play_sweep.png", rows, [f"+{k * 0.5:.1f}s" for k in range(8)], 0.3,
     "Unity play mode sweep (16 s): emotions crossfade, Blink pulses, gaze sweep, camera yaw +-60", label_w=10)

# 8. far eye at the side views (hair off): crops and the eye-white pixel count (light grey, not the white background or
# the pure-white highlights) in a 120 px strip from the outer dark column of the far side
import json  # noqa: E402

import numpy as np  # noqa: E402

VSTATES = ("Neutral", "Happy060", "Angry100", "Sad100", "Cry100", "Surprise100", "Surprise100_gR", "Angry100_b05")
white = {}
for A in (35, 45, 60):
    box = {}
    for a in (A, -A):
        ar = np.asarray(load(os.path.join(V3B, "view", f"Neutral_noview_{a}.png"))).astype(int)
        m = ar.sum(2) < 200
        cols, rws = np.nonzero(m.any(0))[0], np.nonzero(m.any(1))[0]
        x0 = cols.min() - 40 if a > 0 else cols.max() - 200
        box[a] = (x0, max(rws.min() - 30, 0), x0 + 240, min(rws.min() + 250, ar.shape[0]))
        sl = slice(cols.min() - 10, cols.min() + 110) if a > 0 else slice(cols.max() - 110, cols.max() + 10)
        for n in VSTATES:
            r = []
            for src, v in ((V3B, "noview"), (V3B, "view"), (UNI, "view")):
                im = np.asarray(load(os.path.join(src, "view", f"{n}_{v}_{a}.png"))).astype(int)[:, sl]
                mx, mn = im.max(2), im.min(2)
                r.append(int(((mn > 185) & (mx < 250) & (mx - mn < 30)).sum()))
            white.setdefault(str(a), {})[n] = dict(off=r[0], on=r[1], unity=r[2])
    w, h = box[A][2] - box[A][0], box[A][3] - box[A][1]
    CW, CH = int(w * 0.75), int(h * 0.75)
    S = Image.new("RGB", (120 + CW * 6, 24 + CH * len(VSTATES)), "white")
    d = ImageDraw.Draw(S)
    for j, hd in enumerate((f"{A} off", f"{A} on", f"{A} Unity", f"-{A} off", f"-{A} on", f"-{A} Unity")):
        d.text((120 + j * CW + 4, 2), hd, fill="black", font=SMALL)
    for i, n in enumerate(VSTATES):
        d.text((4, 24 + i * CH + CH // 2 - 8), n, fill="black", font=SMALL)
        for j, (a, src, v) in enumerate(((A, V3B, "noview"), (A, V3B, "view"), (A, UNI, "view"), (-A, V3B, "noview"), (-A, V3B, "view"), (-A, UNI, "view"))):
            S.paste(load(os.path.join(src, "view", f"{n}_{v}_{a}.png")).crop(box[a]).resize((CW, CH), Image.LANCZOS), (120 + j * CW, 24 + i * CH))
    S.save(os.path.join(OUT, f"view_fareye_{A}.png"))
    print(f"view_fareye_{A}.png", S.size)
json.dump(white, open(os.path.join(OUT, "view_fareye_white.json"), "w"), indent=1)
for a, v in white.items():
    print("far eye white", a, " ".join(f"{n} {x['off']}/{x['on']}/{x['unity']}" for n, x in v.items()))
