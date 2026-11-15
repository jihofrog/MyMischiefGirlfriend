"""ToonTest_01 step 36 (see-through venv python): v6d eyeball texture = v6b eyeball picture + socket AO in alpha.

usage: <venv python> t36_eye_ball_ao_v6d.py
RGB: r30/eye_tex_ball_<s>.png unchanged (turned by the gaze). Alpha: a faint socket shade read through the fixed UV0
(front projection at rest, so it stays with the lids when the gaze turns): 1 - s * (1 - smoothstep(0, W, d)), d = distance
inside the r30 eye opening; s = 0.10 at the sides / bottom, 0.16 under the upper lid; W = 2.2 mm. Outside the opening
(under the lids) 1 - s. Writes r30/eye_tex_ball_v6d_<s>.png.
"""
import json
import os

import numpy as np
from PIL import Image

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TGT = json.load(open(os.path.join(EXP, "spec", "r30_eye_targets.json")))
SPEC = json.load(open(os.path.join(EXP, "spec", "r30_face_spec.json")))
FIT = json.load(open(os.path.join(EXP, "spec", "blender_fit.json")))
PPM = SPEC["head_height_px"] / FIT["head_h"]
W_MM, S_SIDE, S_TOP = 2.2, 0.10, 0.16


def signed_dist(P, poly):
    A, B = poly, np.roll(poly, -1, 0)
    AB = B - A
    AP = P[:, None, :] - A[None]
    t = np.clip((AP * AB).sum(-1) / np.maximum((AB * AB).sum(-1), 1e-12), 0, 1)
    d = np.linalg.norm(AP - t[..., None] * AB, axis=-1).min(1)
    y, x = P[:, 1][:, None], P[:, 0][:, None]
    cross = ((A[None, :, 1] > y) != (B[None, :, 1] > y)) & (
        x < (B[None, :, 0] - A[None, :, 0]) * (y - A[None, :, 1]) / (B[None, :, 1] - A[None, :, 1] + 1e-12) + A[None, :, 0])
    return np.where(cross.sum(1) % 2 == 1, d, -d)          # + inside


for s in "LR":
    img = np.asarray(Image.open(os.path.join(EXP, "r30", f"eye_tex_ball_{s}.png")).convert("RGBA")).astype(np.float32) / 255
    N = img.shape[0]
    bx = TGT["tex_box"][s]
    poly = np.array(TGT[s]["opening"], float)
    G = 256
    gy, gx = np.mgrid[0:G, 0:G]
    P = np.stack([bx[0] + (gx.ravel() + 0.5) / G * (bx[2] - bx[0]), bx[1] + (gy.ravel() + 0.5) / G * (bx[3] - bx[1])], 1)
    d = signed_dist(P, poly).reshape(G, G) / PPM * 1000                     # mm, + inside the opening
    cy = poly[:, 1].mean()
    top = np.clip((cy - P[:, 1].reshape(G, G)) / ((poly[:, 1].max() - poly[:, 1].min()) / 2), 0, 1)   # 1 at the top edge
    st = S_SIDE + (S_TOP - S_SIDE) * top
    t = np.clip(d / W_MM, 0, 1)
    ao = 1 - st * (1 - t * t * (3 - 2 * t))
    ao = np.asarray(Image.fromarray((ao * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)) / 255
    out = img.copy()
    out[..., 3] = ao
    Image.fromarray((out * 255).astype(np.uint8), "RGBA").save(os.path.join(EXP, "r30", f"eye_tex_ball_v6d_{s}.png"))
    print("AO", s, "min", round(float(ao.min()), 3), "mean inside", round(float(ao[np.asarray(Image.fromarray(((d > 0) * 255).astype(np.uint8)).resize((N, N))) > 0].mean()), 3))
