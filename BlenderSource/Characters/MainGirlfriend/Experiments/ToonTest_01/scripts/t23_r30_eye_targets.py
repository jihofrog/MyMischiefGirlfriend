"""ToonTest_01 step 23 (see-through venv python, read only on the PSD): r30 eye targets for the v6 eye tests.

usage: <see-through venv python> t23_r30_eye_targets.py
Reads Live2DSource/MainGirlfriend/06_PSD/MainGirlfriend_Front_v30.psd through s22_outfit_prep.py. Per eye (R, L):
  spec/r30_eye_targets.json   opening outline (EyeWhite_Clean, alpha 128, px, counter-clockwise from the outer
                              corner), upper lash band (EyeLash_Upper: lower edge = lid line, upper edge per column),
                              closed-eye lash centre line (EyeLash_Closed), lower lash bbox, iris ellipse, texture boxes
  r30/eye_tex_ball_<s>.png     eyeball texture: r30 eye white + unclipped iris / rim / pupil / highlight, the white
                              extended outward (hidden under the lids at rest, seen when the gaze turns)
  r30/eye_tex_iris_<s>.png     the same box, iris mask only (id renders)
  r30/eye_tex_lash_<s>.png     EyeLash_Upper, EyeLash_Lower and EyeLash_Closed of that eye (RGBA, same box)
  r30/r30_eye_classes.png      front classes for the IoU check (full canvas): white 1, iris 2, lash 3
Texture box: EYE_BOX[s] in canvas px; u = (px - x0) / w, v = 1 - (py - y0) / h.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
PROJ = os.path.abspath(os.path.join(EXP, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "Live2DSource", "MainGirlfriend", "scripts"))
import s22_outfit_prep as s22  # noqa: E402

EYE_BOX = {"R": (780, 400, 1000, 620), "L": (1060, 395, 1280, 615)}     # square 220 px boxes around each eye
TEX = 512


def contour(mask):
    """outer boundary of the largest blob as a polygon (marching along boundary pixels by angle around the centroid)"""
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean(), ys.mean()
    pts = []
    for a in np.linspace(0, 2 * np.pi, 181)[:-1]:
        dx, dy = np.cos(a), -np.sin(a)
        r, last = 0.0, None
        while True:
            x, y = int(round(cx + dx * r)), int(round(cy + dy * r))
            if not (0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]):
                break
            if mask[y, x]:
                last = (cx + dx * r, cy + dy * r)
            elif last is not None and r - np.hypot(last[0] - cx, last[1] - cy) > 6:
                break
            r += 0.5
        pts.append([round(last[0], 1), round(last[1], 1)])
    return pts, [round(cx, 1), round(cy, 1)]


def main():
    layers = s22.load_layers()
    by = {n: im for n, _, im in layers}
    A = lambda n: np.asarray(by[n])[..., 3].astype(np.float32) / 255
    out = {"tex_box": EYE_BOX, "tex_size": TEX}
    classes = np.zeros((3072, 2048), np.uint8)
    for s in "RL":
        x0, y0, x1, y1 = EYE_BOX[s]
        white = np.maximum.reduce([A(f"EyeWhite_Clean_{s}"), A(f"EyeWhite_{s}"), A(f"EyeWhite_{s}_AI")])
        opening = white > 0.5
        poly, centre = contour(opening)
        # upper lash band: per column, top and bottom (lid line) of the dark band
        lash = A(f"EyeLash_Upper_{s}") > 0.5
        cols = {}
        for x in range(x0, x1):
            ys = np.nonzero(lash[:, x])[0]
            if len(ys):
                cols[x] = [int(ys.min()), int(ys.max())]
        closed = A(f"EyeLash_Closed_{s}") > 0.5
        cl = {}
        for x in range(x0, x1):
            ys = np.nonzero(closed[:, x])[0]
            if len(ys):
                cl[x] = [int(ys.min()), int(ys.max())]
        lo = A(f"EyeLash_Lower_{s}") > 0.5
        ys, xs = np.nonzero(lo)
        iris = np.maximum(A(f"Iris_{s}"), A(f"Iris_Rim_{s}")) > 0.5
        iy, ix = np.nonzero(iris)
        oc = {}
        for x in range(x0, x1):
            col = np.nonzero(opening[:, x])[0]
            if len(col):
                oc[x] = [int(col.min()), int(col.max()) + 1]
        out[s] = dict(opening=poly, opening_centre=centre, opening_cols=oc,
                      opening_bbox=[int(np.nonzero(opening)[1].min()), int(np.nonzero(opening)[0].min()),
                                    int(np.nonzero(opening)[1].max()) + 1, int(np.nonzero(opening)[0].max()) + 1],
                      lash_cols=cols, closed_cols=cl,
                      lower_lash_bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                      iris_centre=[round(float(ix.mean()), 1), round(float(iy.mean()), 1)],
                      iris_bbox=[int(ix.min()), int(iy.min()), int(ix.max()) + 1, int(iy.max()) + 1])
        # eyeball texture: white layers, then the iris layers without the white clip, then the highlight
        img = Image.new("RGBA", (2048, 3072))
        for n, v, im in layers:
            if n in (f"EyeWhite_Clean_{s}", f"EyeWhite_{s}", f"EyeWhite_{s}_AI") and s22.DEFAULT_VISIBILITY.get(n, v):
                img.alpha_composite(im)
        img = img.crop(EYE_BOX[s])
        wa = np.asarray(img).astype(np.float32) / 255
        # white as seen in r30 (outside the iris, under no lash), extended outward by normalised blurs so the part
        # hidden under the lids at rest continues the drawn white without seams
        comp = s22.body_base(layers)
        ca = np.asarray(comp).astype(np.float32)[y0:y1, x0:x1] / 255
        iris_box = (np.maximum(A(f"Iris_{s}"), A(f"Iris_Rim_{s}")) > 0.05)[y0:y1, x0:x1]
        lash_box = ((A(f"EyeLash_Upper_{s}") > 0.05) | (A(f"EyeLash_Lower_{s}") > 0.05))[y0:y1, x0:x1]
        vis = (wa[..., 3] > 0.98) & ~iris_box & ~lash_box
        base = np.median(ca[vis][:, :3], axis=0)
        col = np.zeros(wa.shape[:2] + (3,), np.float32); col[:] = base
        acc = np.zeros(wa.shape[:2], np.float32)
        for rad in (24, 12, 6, 3):
            w = Image.fromarray((vis * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))
            w = np.asarray(w).astype(np.float32) / 255
            cs = []
            for k in range(3):
                ch = Image.fromarray((ca[..., k] * vis * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))
                cs.append(np.asarray(ch).astype(np.float32) / 255)
            cs = np.stack(cs, -1) / np.maximum(w[..., None], 1e-4)
            m = np.clip(w * 4, 0, 1)[..., None]
            col = col * (1 - m) + cs * m
        col = col * (1 - vis[..., None]) + ca[..., :3] * vis[..., None]
        bg = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        for n in (f"Iris_Rim_{s}", f"Iris_{s}", f"Pupil_{s}", f"EyeHighlight_{s}"):
            vis = dict((nn, vv) for nn, vv, _ in layers)[n]
            if s22.DEFAULT_VISIBILITY.get(n, vis):
                bg.alpha_composite(by[n].crop(EYE_BOX[s]))
        bg.resize((TEX, TEX), Image.LANCZOS).save(os.path.join(EXP, "r30", f"eye_tex_ball_{s}.png"))
        im = Image.fromarray((iris[y0:y1, x0:x1] * 255).astype(np.uint8)).resize((TEX, TEX), Image.LANCZOS)
        im.save(os.path.join(EXP, "r30", f"eye_tex_iris_{s}.png"))
        lash_img = Image.new("RGBA", (2048, 3072))
        for n in (f"EyeLash_Upper_{s}", f"EyeLash_Lower_{s}"):
            lash_img.alpha_composite(by[n])
        lash_img.crop(EYE_BOX[s]).resize((TEX, TEX), Image.LANCZOS).save(os.path.join(EXP, "r30", f"eye_tex_lash_{s}.png"))
        by[f"EyeLash_Closed_{s}"].crop(EYE_BOX[s]).resize((TEX, TEX), Image.LANCZOS).save(
            os.path.join(EXP, "r30", f"eye_tex_closed_{s}.png"))
        # front classes as drawn (iris clipped by the white, lashes on top)
        irisc = iris & opening
        classes[opening] = 1
        classes[irisc] = 2
        classes[lash | lo] = 3
    Image.fromarray(classes * 80).save(os.path.join(EXP, "r30", "r30_eye_classes.png"))
    json.dump(out, open(os.path.join(EXP, "spec", "r30_eye_targets.json"), "w"))
    print("EYE_TARGETS", {s: dict(opening_bbox=out[s]["opening_bbox"], iris_bbox=out[s]["iris_bbox"],
                                  lash_cols=len(out[s]["lash_cols"]), closed=len(out[s]["closed_cols"])) for s in "RL"})


if __name__ == "__main__":
    main()
