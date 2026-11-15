"""ToonTest_01 step 44 (plain python with numpy / PIL): Blender (t41) vs Unity URP (u07) for the v6e candidates.

usage: python t44_eye_v6e_unity_compare.py v6d_3 v6e_A v6e_B v6e_C
Per tag and image: mean |Blender - Unity| (Blender composited on white), Unity front change vs Unity v6d_3, Unity bright
white px in the left eye close up (L > 0.80, saturation < 0.10, not the background) per angle. Writes spec/eye_v6e_unity_compare.json and
renders/compare_eye_v6e_unity.png (Blender / Unity rows, left eye at 0 / 35 / 45 / 60 / 90 and faces at 35 / 45).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
tags = sys.argv[1:]
ANG = (0, 35, 45, 60, 90)


def load(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB")).astype(float) / 255


def white_px(a):
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return int(((lum > 0.80) & (sat < 0.10) & (mn < 0.99)).sum())            # not the white background


res = {}
for t in tags:
    r = {"diff_blender_unity": {}, "unity_white_px_eyeL": {}, "blender_white_px_eyeL": {}}
    names = [f"face_{a}" for a in ANG] + [f"eyes_{a}" for a in ANG] + [f"eyeL_{a}" for a in ANG]
    names += [f"expr_{p}_{a}" for a in (0, 35) for p in ("Neutral", "Blink50", "Blink", "EyeSmile", "SmileEyeSmile", "Surprise", "GazeL", "GazeR")]
    for n in names:
        b, u = load(os.path.join(R, f"{t}_e6_{n}.png")), load(os.path.join(R, f"unity_{t}_e6_{n}.png"))
        if b.shape != u.shape:
            u = np.asarray(Image.fromarray((u * 255).astype(np.uint8)).resize(b.shape[1::-1], Image.LANCZOS)).astype(float) / 255
        r["diff_blender_unity"][n] = round(float(np.abs(b - u).mean()), 4)
    for a in ANG:
        r["unity_white_px_eyeL"][str(a)] = white_px(load(os.path.join(R, f"unity_{t}_e6_eyeL_{a}.png")))
        r["blender_white_px_eyeL"][str(a)] = white_px(load(os.path.join(R, f"{t}_e6_eyeL_{a}.png")))
    if t != tags[0]:
        r["unity_vs_ref"] = {n: round(float(np.abs(load(os.path.join(R, f"unity_{t}_e6_{n}.png"))
                                                   - load(os.path.join(R, f"unity_{tags[0]}_e6_{n}.png"))).mean()), 4)
                             for n in ("eyeL_0", "eyes_0", "face_0", "eyeL_35", "eyeL_45")}
    d = list(r["diff_blender_unity"].values())
    r["diff_mean_all"] = round(float(np.mean(d)), 4)
    r["diff_max"] = max(r["diff_blender_unity"].items(), key=lambda kv: kv[1])
    res[t] = r
    print(t, "diff mean", r["diff_mean_all"], "max", r["diff_max"], "unity white", r["unity_white_px_eyeL"], r.get("unity_vs_ref"))
json.dump(res, open(os.path.join(EXP, "spec", "eye_v6e_unity_compare.json"), "w"), indent=1)

# sheet
try:
    F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)
except OSError:
    F = ImageFont.load_default()
TW, TH = 300, 196
cols = [("eyeL", a) for a in ANG] + [("face", 35), ("face", 45)]
S = Image.new("RGB", (len(cols) * (TW + 6) + 150, len(tags) * 2 * (TH + 6) + 40), "white")
dr = ImageDraw.Draw(S)
dr.text((10, 8), "Blender (위) / Unity URP (아래) — 왼눈 0·35·45·60·90°, 얼굴 35·45°", fill="black", font=F)
y = 40
for t in tags:
    for src in ("blender", "unity"):
        dr.text((8, y + TH // 2 - 24), f"{t}\n{src}", fill="black", font=F)
        for i, (n, a) in enumerate(cols):
            p = os.path.join(R, (f"{t}_e6_{n}_{a}.png" if src == "blender" else f"unity_{t}_e6_{n}_{a}.png"))
            im = Image.fromarray((load(p) * 255).astype(np.uint8))
            if n == "face":
                W, H = im.size
                im = im.crop((int(W * 0.2), int(H * 0.38), int(W * 0.8), int(H * 0.77)))
            im.thumbnail((TW, TH))
            S.paste(im, (150 + i * (TW + 6), y))
        y += TH + 6
S.save(os.path.join(R, "compare_eye_v6e_unity.png"))
print("UNITY_SHEET_OK")
