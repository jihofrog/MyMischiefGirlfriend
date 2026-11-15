"""ToonTest_01 step 57 (python with numpy / scipy / PIL): Blender (t48) vs Unity URP (u08) for v6f.

usage: python t57_eye_v6f_unity_compare.py v6d_3 v6f_A v6f_B
Per tag: mean |Blender - Unity| per image (Blender on white), Unity close-up change vs Unity v6d_3 at 0 deg, bright white
px per eye and angle in Blender and Unity (L > 0.80, saturation < 0.10, not the background). Writes
spec/eye_v6f_unity_compare.json and renders/compare_eye_v6f_unity_far.png (far eyes at +-35 / +-45: Blender row, Unity
row per tag; same crop as t53). Env OUTTAG (default v6f) names the outputs.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
tags = sys.argv[1:]
OUTTAG = os.environ.get("OUTTAG", "v6f")          # v6g: writes eye_v6g_unity_compare.json / compare_eye_v6g_unity_far.png
ANG = (0, 35, -35, 45, -45, 60, -60, 90, -90)


def load(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB")).astype(float) / 255


def white_px(a):
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return int(((lum > 0.80) & (sat < 0.10) & (mn < 0.99)).sum())


res = {}
for t in tags:
    r = {"diff": {}, "white_blender": {}, "white_unity": {}}
    names = [f"face_{a}" for a in ANG] + [f"facenh_{a}" for a in ANG] + [f"{s}_toon_{a}" for a in ANG for s in "LR"]
    names += [f"expr_{p}_{a}" for a in (0, 35, -35) for p in ("Neutral", "Blink50", "Blink", "EyeSmile", "SmileEyeSmile", "Surprise", "GazeL", "GazeR")]
    names += [n for n in (f"expr_{p}_{a}" for a in (0, 35, -35) for p in ("GazeLmax", "GazeRmax"))
              if os.path.exists(os.path.join(R, f"unity_{t}_f6_{n}.png"))]
    for n in names:
        b, u = load(os.path.join(R, f"{t}_f6_{n}.png")), load(os.path.join(R, f"unity_{t}_f6_{n}.png"))
        if b.shape != u.shape:
            u = np.asarray(Image.fromarray((u * 255).astype(np.uint8)).resize(b.shape[1::-1], Image.LANCZOS)).astype(float) / 255
        r["diff"][n] = round(float(np.abs(b - u).mean()), 4)
    for a in ANG:
        for s in "LR":
            k = f"{s}_{a}"
            r["white_blender"][k] = white_px(load(os.path.join(R, f"{t}_f6_{s}_toon_{a}.png")))
            r["white_unity"][k] = white_px(load(os.path.join(R, f"unity_{t}_f6_{s}_toon_{a}.png")))
    if t != tags[0]:
        r["unity_front_vs_ref"] = {n: round(float(np.abs(load(os.path.join(R, f"unity_{t}_f6_{n}.png"))
                                                        - load(os.path.join(R, f"unity_{tags[0]}_f6_{n}.png"))).mean()), 4)
                                   for n in ("L_toon_0", "R_toon_0", "face_0")}
    r["diff_mean"] = round(float(np.mean(list(r["diff"].values()))), 4)
    r["diff_max"] = max(r["diff"].items(), key=lambda kv: kv[1])
    res[t] = r
    print(t, "diff mean", r["diff_mean"], "max", r["diff_max"], r.get("unity_front_vs_ref"))
json.dump(res, open(os.path.join(EXP, "spec", f"eye_{OUTTAG}_unity_compare.json"), "w"), indent=1)

F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 24)
views = ("R_35", "L_-35", "R_45", "L_-45")
crops = {}
for v in views:
    s, a = v.split("_")
    idm = load(os.path.join(R, f"{tags[0]}_f6_{s}_id_{a}.png"))
    g = np.abs(idm - np.array([0.35, 0.93, 0.49])).sum(2) < 0.25
    lab, n = label(g)
    g = lab == (1 + int(np.argmax(np.bincount(lab.ravel())[1:])))
    ys, xs = np.nonzero(g)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    hw = max(xs.max() - xs.min(), (ys.max() - ys.min()) * 0.75) / 2 + 30
    crops[v] = (int(cx - hw), int(cy - hw / 0.75), int(cx + hw), int(cy + hw / 0.75))
TW, TH = 240, 320
S = Image.new("RGB", (len(views) * (TW + 6) + 220, len(tags) * 2 * (TH + 6) + 40), "white")
d = ImageDraw.Draw(S)
for j, v in enumerate(views):
    s, a = v.split("_")
    d.text((220 + j * (TW + 6), 6), f"{'오른' if s == 'R' else '왼'}눈 {a}° 먼 눈", fill="black", font=F)
y = 40
for t in tags:
    for src in ("Blender", "Unity"):
        d.text((6, y + TH // 2 - 12), f"{t}\n{src}", fill="black", font=F)
        for j, v in enumerate(views):
            s, a = v.split("_")
            p = os.path.join(R, (f"{t}_f6_{s}_toon_{a}.png" if src == "Blender" else f"unity_{t}_f6_{s}_toon_{a}.png"))
            im = Image.fromarray((load(p) * 255).astype(np.uint8)).crop(crops[v]).resize((TW, TH), Image.LANCZOS)
            S.paste(im, (220 + j * (TW + 6), y))
        y += TH + 6
S.save(os.path.join(R, f"compare_eye_{OUTTAG}_unity_far.png"))
print("UNITY_SHEET_OK")
