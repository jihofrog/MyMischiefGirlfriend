"""ToonTest_01 step 86 (python with numpy / PIL + ffmpeg): final Unity play-mode head turns (u19, renders/unity_final).

usage: python t86_eye_v6j_final_videos.py
For face_turn (whole face) and eye_turn (eyes close up), 0 -> 60 -> 0 -> -60 -> 0 at 0.5 deg per frame:
  renders/unity_final_v6j_<seq>.mp4 / .gif    v6j alone, with the angle and the far-eye weights
  renders/unity_final_AB_<seq>.mp4            A v6f_A | v6j side by side
  renders/compare_eye_v6j_final_<seq>.png     frames at 0, 10, 15, 20, ..., 45, 50, 60 deg both ways (v6j)
and per frame the change of the v6j picture minus the change of the A picture in the area where they differ (a sudden
change of the eyes shows as a spike), written to spec/eye_v6j_final_turn.json.
"""
import csv
import json
import os
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(EXP, "renders", "unity_final")
OUT = os.path.join(EXP, "renders")
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)


def load(t, n):
    return np.asarray(Image.open(os.path.join(P, t, n)).convert("RGB")).astype(float) / 255


def video(frames_dir, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(frames_dir, "%04d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], check=True)


res = {}
for s in ("face_turn", "eye_turn"):
    rows = list(csv.DictReader(open(os.path.join(P, "v6j", f"{s}.csv"))))
    n = len(rows)
    A = [load("v6f_A", f"{s}_{i:03d}.png") for i in range(n)]
    J = [load("v6j", f"{s}_{i:03d}.png") for i in range(n)]
    mask = np.zeros(A[0].shape[:2], bool)
    for a, j in zip(A, J):
        mask |= np.abs(a - j).sum(2) > 0.15
    mask = binary_dilation(mask, iterations=12) if mask.any() else np.ones_like(mask)
    sa = [float(np.abs(A[i + 1] - A[i])[mask].mean()) for i in range(n - 1)]
    sj = [float(np.abs(J[i + 1] - J[i])[mask].mean()) for i in range(n - 1)]
    exc = [b - a for a, b in zip(sa, sj)]
    k = int(np.argmax(exc))
    yaw = [float(r["yaw_set"]) for r in rows]
    in_band = [i for i in range(n - 1) if 15 <= abs(yaw[i]) <= 45]
    res[s] = dict(frames=n, deg_per_frame=0.5, max_step_A=round(max(sa), 4), max_step_v6j=round(max(sj), 4),
                  max_excess=round(max(exc), 4), at_yaw=yaw[k],
                  max_excess_15_45=round(max(exc[i] for i in in_band), 4),
                  far_weight_max_step=round(max(abs(float(rows[i + 1]["farR"]) - float(rows[i]["farR"])) +
                                                abs(float(rows[i + 1]["farL"]) - float(rows[i]["farL"])) for i in range(n - 1)), 4))
    print(s, res[s])
    for kind in ("v6j", "AB"):
        tmp = f"/tmp/unity_final_{kind}_{s}"
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        gif = []
        for i in range(n):
            r = rows[i]
            h, w = J[i].shape[:2]
            label = f"yaw {float(r['yaw_set']):+.1f}°   far weight L {float(r['farL']):.2f}  R {float(r['farR']):.2f}"
            if kind == "v6j":
                fr = Image.new("RGB", (w, h + 36), "white")
                fr.paste(Image.fromarray((J[i] * 255).astype(np.uint8)), (0, 36))
                ImageDraw.Draw(fr).text((8, 6), "v6j  " + label, fill="black", font=F)
                if i % 2 == 0:
                    gif.append(fr.resize((fr.width // 2, fr.height // 2), Image.LANCZOS))
            else:
                fr = Image.new("RGB", (w * 2 + 8, h + 36), "white")
                fr.paste(Image.fromarray((A[i] * 255).astype(np.uint8)), (0, 36))
                fr.paste(Image.fromarray((J[i] * 255).astype(np.uint8)), (w + 8, 36))
                d = ImageDraw.Draw(fr)
                d.text((8, 6), f"A v6f_A   yaw {float(r['yaw_set']):+.1f}°", fill="black", font=F)
                d.text((w + 16, 6), "v6j  " + label, fill="black", font=F)
            fr.save(os.path.join(tmp, f"{i:04d}.png"))
        video(tmp, os.path.join(OUT, f"unity_final_{kind}_{s}.mp4"))
        if gif:
            gif[0].save(os.path.join(OUT, f"unity_final_v6j_{s}.gif"), save_all=True, append_images=gif[1:], duration=66, loop=0)
    picks = (0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60)
    TW = 220 if s == "face_turn" else 260
    h, w = J[0].shape[:2]
    TH = int(TW * h / w)
    S = Image.new("RGB", (len(picks) * (TW + 4) + 60, 2 * (TH + 4) + 30), "white")
    d = ImageDraw.Draw(S)
    for jx, a in enumerate(picks):
        d.text((60 + jx * (TW + 4), 4), f"{a}°", fill="black", font=F)
        for r_, sign in enumerate((1, -1)):
            i = yaw.index(sign * a) if a else 0
            S.paste(Image.fromarray((J[i] * 255).astype(np.uint8)).resize((TW, TH), Image.LANCZOS), (60 + jx * (TW + 4), 30 + r_ * (TH + 4)))
            if jx == 0:
                d.text((6, 30 + r_ * (TH + 4) + TH // 2 - 12), "+" if sign > 0 else "-", fill="black", font=F)
    S.save(os.path.join(OUT, f"compare_eye_v6j_final_{s}.png"))
json.dump(res, open(os.path.join(EXP, "spec", "eye_v6j_final_turn.json"), "w"), indent=1)
print("FINAL_OK")
