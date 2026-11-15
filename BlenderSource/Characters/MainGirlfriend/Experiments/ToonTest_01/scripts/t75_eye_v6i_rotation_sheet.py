"""ToonTest_01 step 75 (python with numpy / PIL): t74 head turn frames, A vs candidate.

usage: python t75_eye_v6i_rotation_sheet.py <ref tag> <tag> [prefix, default ""]   (prefix "unity_" for the u11 frames)
Per frame: mean |candidate - ref| (how far the correction is applied) and its change to the next frame (a jump shows as
a spike); the same frame-to-frame change of each tag alone. Writes spec/eye_v6i_rotation_<prefix><tag>.json,
renders/compare_eye_v6i_rotation_<prefix><tag>.gif (ref | tag, angle label) and renders/compare_eye_v6i_rotation_<prefix><tag>.png
(frames at 0, 10, 20, 24, 28, 32, 36, 40, 50, 60 deg both ways, crop around the far eye).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
ref, tag = sys.argv[1], sys.argv[2]
pre = sys.argv[3] if len(sys.argv) > 3 else ""
seq = list(range(0, 61, 2)) + list(range(58, -1, -2))
seq = seq + [-a for a in seq]
F = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 22)


def load(t, i):
    p = os.path.join(R, f"{pre}{t}_rot", f"{i:03d}.png")
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB")).astype(float) / 255


A = [load(ref, i) for i in range(len(seq))]
Bm = [load(tag, i) for i in range(len(seq))]
d_ab = [float(np.abs(a - b).mean()) for a, b in zip(A, Bm)]
step_a = [float(np.abs(A[i + 1] - A[i]).mean()) for i in range(len(seq) - 1)]
step_b = [float(np.abs(Bm[i + 1] - Bm[i]).mean()) for i in range(len(seq) - 1)]
jump = [abs(d_ab[i + 1] - d_ab[i]) for i in range(len(seq) - 1)]
# the same angle on the way out and back must give the same picture (no history in the driver)
back = max(float(np.abs(Bm[i] - Bm[60 - i]).max()) for i in range(31))
res = dict(angles=seq, diff_vs_ref=[round(v, 5) for v in d_ab], step_ref=[round(v, 5) for v in step_a],
           step_tag=[round(v, 5) for v in step_b], max_step_excess=round(max(b - a for a, b in zip(step_a, step_b)), 5),
           max_diff_jump=round(max(jump), 5), out_back_max_px_diff=round(back, 4))
json.dump(res, open(os.path.join(EXP, "spec", f"eye_v6i_rotation_{pre}{tag}.json"), "w"), indent=1)
print("ROT", pre + tag, "max diff vs ref", round(max(d_ab), 4), "max jump", res["max_diff_jump"], "max step excess", res["max_step_excess"],
      "out/back", res["out_back_max_px_diff"])
frames = []
for i, a in enumerate(seq):
    a_im = Image.fromarray((A[i] * 255).astype(np.uint8))
    b_im = Image.fromarray((Bm[i] * 255).astype(np.uint8))
    W, H = a_im.size
    fr = Image.new("RGB", (W * 2 + 10, H + 34), "white")
    fr.paste(a_im, (0, 34))
    fr.paste(b_im, (W + 10, 34))
    d = ImageDraw.Draw(fr)
    d.text((6, 4), f"{ref} {a:+d}°", fill="black", font=F)
    d.text((W + 16, 4), f"{tag} {a:+d}°", fill="black", font=F)
    frames.append(fr.resize((fr.width // 2, fr.height // 2), Image.LANCZOS))
frames[0].save(os.path.join(R, f"compare_eye_v6i_rotation_{pre}{tag}.gif"), save_all=True, append_images=frames[1:], duration=60, loop=0)
BOX = json.load(open(os.path.join(EXP, "spec", "eye_f6_boxes_v6i.json")))
PPM = 1825.2246526823355


def eye_px(side, a):
    """eye centre in the t74 frame (box 560, 340) at angle a, from the t55 boxes at 0 and 60 deg"""
    c0 = (BOX[f"{side}_0"][0] + BOX[f"{side}_0"][2]) / 2
    c60 = (BOX[f"{side}_60"][0] + BOX[f"{side}_60"][2]) / 2
    x = (c0 - 1030) / PPM
    yy = ((c60 - 1030) / PPM - x * 0.5) / np.sin(np.radians(60))
    t = np.radians(a)
    return 1030 + PPM * (x * np.cos(t) + yy * np.sin(t)) - 560, (BOX[f"{side}_0"][1] + BOX[f"{side}_0"][3]) / 2 - 340


pick = (0, 10, 20, 24, 28, 32, 36, 40, 50, 60)
TW, TH = 200, 150
S = Image.new("RGB", (len(pick) * (TW + 4) + 160, 4 * (TH + 4) + 30), "white")
d = ImageDraw.Draw(S)
for j, a in enumerate(pick):
    d.text((160 + j * (TW + 4), 4), f"{a}°", fill="black", font=F)
    for r, (sign, im_list, lab) in enumerate(((1, A, ref), (1, Bm, tag), (-1, A, ref), (-1, Bm, tag))):
        i = seq.index(sign * a) if a else 0
        im = Image.fromarray((im_list[i] * 255).astype(np.uint8))
        W, H = im.size
        # far eye: R (screen left) for +, L (screen right) for -
        cx, cy = eye_px("R" if sign > 0 else "L", sign * a)
        box = (int(cx - 80), int(cy - 60), int(cx + 80), int(cy + 60))
        S.paste(im.crop(box).resize((TW, TH), Image.LANCZOS), (160 + j * (TW + 4), 30 + r * (TH + 4)))
        if j == 0:
            d.text((4, 30 + r * (TH + 4) + TH // 2 - 12), f"{lab} {'+' if sign > 0 else '-'}", fill="black", font=F)
S.save(os.path.join(R, f"compare_eye_v6i_rotation_{pre}{tag}.png"))
print("ROT_SHEET_OK")
