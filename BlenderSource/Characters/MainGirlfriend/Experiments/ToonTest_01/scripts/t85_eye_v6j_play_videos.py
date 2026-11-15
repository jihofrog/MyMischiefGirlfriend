"""ToonTest_01 step 85 (python with numpy / PIL + ffmpeg): Unity play-mode frames (EyeViewTestRig, u12) A | v6j.

usage: python t85_eye_v6j_play_videos.py
For every sequence in renders/unity_play/v6f_A: side by side frames with the set angle / inputs, an MP4 (30 fps) and a
GIF (half size) renders/unity_play_<sequence>.{mp4,gif}; per frame the mean |v6j - A| (how much the correction shows)
and the frame-to-frame change of each, in the far-eye area (where v6j and A ever differ, grown by 12 px); the largest
excess of the v6j change over the A change is the "jump" number. Also a far-eye strip of the turn at 0..60 deg
(renders/compare_eye_v6j_play_turn.png). Writes spec/eye_v6j_play.json.
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
P = os.path.join(EXP, "renders", "unity_play")
OUT = os.path.join(EXP, "renders")
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
SEQ = ("turn", "blink35", "gaze35", "smile35", "above", "below", "dolly35", "dolly25")


def load(t, n):
    return np.asarray(Image.open(os.path.join(P, t, n)).convert("RGB")).astype(float) / 255


res = {}
for s in SEQ:
    rows = list(csv.DictReader(open(os.path.join(P, "v6j", f"{s}.csv"))))
    n = len(rows)
    A = [load("v6f_A", f"{s}_{i:03d}.png") for i in range(n)]
    J = [load("v6j", f"{s}_{i:03d}.png") for i in range(n)]
    mask = np.zeros(A[0].shape[:2], bool)
    for a, j in zip(A, J):
        mask |= np.abs(a - j).sum(2) > 0.15
    mask = binary_dilation(mask, iterations=12) if mask.any() else np.ones_like(mask)
    diff = [float(np.abs(a - j)[mask].mean()) for a, j in zip(A, J)]
    sa = [float(np.abs(A[i + 1] - A[i])[mask].mean()) for i in range(n - 1)]
    sj = [float(np.abs(J[i + 1] - J[i])[mask].mean()) for i in range(n - 1)]
    exc = [b - a for a, b in zip(sa, sj)]
    k = int(np.argmax(exc))
    res[s] = dict(frames=n, max_diff_vs_A=round(max(diff), 4), max_step_A=round(max(sa), 4), max_step_v6j=round(max(sj), 4),
                  max_step_excess=round(max(exc), 4), at_frame=k, at_yaw=float(rows[k]["yaw_set"]),
                  far_weight_max_step=round(max(abs(float(rows[i + 1]["farR"]) - float(rows[i]["farR"])) +
                                                abs(float(rows[i + 1]["farL"]) - float(rows[i]["farL"])) for i in range(n - 1)), 3))
    print(s, res[s])
    tmp = os.path.join("/tmp", f"v6j_play_{s}")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    gif = []
    for i in range(n):
        h, w = A[i].shape[:2]
        fr = Image.new("RGB", (w * 2 + 8, h + 54), "white")
        fr.paste(Image.fromarray((A[i] * 255).astype(np.uint8)), (0, 54))
        fr.paste(Image.fromarray((J[i] * 255).astype(np.uint8)), (w + 8, 54))
        d = ImageDraw.Draw(fr)
        r = rows[i]
        info = f"yaw {float(r['yaw_set']):+.0f}°  pitch {float(r['pitch_set']):+.0f}°  dist {float(r['dist']):.2f}  " \
               f"blink {float(r['blink']):.2f}  eyesmile {float(r['eyesmile']):.2f}  smile {float(r['smile']):.2f}  gaze {float(r['gaze']):+.2f}"
        d.text((6, 5), "A v6f_A", fill="black", font=F)
        d.text((w + 14, 5), f"v6j  far L {float(r['farL']):.2f} R {float(r['farR']):.2f}", fill="black", font=F)
        d.text((6, 29), info, fill=(90, 90, 90), font=F)
        fr.save(os.path.join(tmp, f"{i:04d}.png"))
        gif.append(fr.resize((fr.width // 2, fr.height // 2), Image.LANCZOS))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(tmp, "%04d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    os.path.join(OUT, f"unity_play_{s}.mp4")], check=True)
    gif[0].save(os.path.join(OUT, f"unity_play_{s}.gif"), save_all=True, append_images=gif[1:], duration=33, loop=0)

# far-eye strip of the turn (0..60 deg, frames 0..60): crop around the area that changes
rows = list(csv.DictReader(open(os.path.join(P, "v6j", "turn.csv"))))
picks = (0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60)
TW, TH = 150, 150
S = Image.new("RGB", (len(picks) * (TW + 4) + 90, 2 * (TH + 4) + 28), "white")
d = ImageDraw.Draw(S)
for jx, f in enumerate(picks):
    a, j = load("v6f_A", f"turn_{f:03d}.png"), load("v6j", f"turn_{f:03d}.png")
    m = np.abs(a - j).sum(2) > 0.15
    ref = load("v6f_A", "turn_035.png"), load("v6j", "turn_035.png")
    if not m.any():
        m = np.abs(ref[0] - ref[1]).sum(2) > 0.15
    ys, xs = np.nonzero(m)
    cx, cy = int(np.median(xs)), int(np.median(ys))
    box = (cx - 70, cy - 70, cx + 70, cy + 70)
    d.text((90 + jx * (TW + 4), 4), f"{f}°", fill="black", font=F)
    for r_, im in enumerate((a, j)):
        S.paste(Image.fromarray((im * 255).astype(np.uint8)).crop(box).resize((TW, TH), Image.LANCZOS), (90 + jx * (TW + 4), 28 + r_ * (TH + 4)))
d.text((4, 28 + TH // 2), "A", fill="black", font=F)
d.text((4, 28 + TH + 4 + TH // 2), "v6j", fill="black", font=F)
S.save(os.path.join(OUT, "compare_eye_v6j_play_turn.png"))
json.dump(res, open(os.path.join(EXP, "spec", "eye_v6j_play.json"), "w"), indent=1)
print("PLAY_OK")
