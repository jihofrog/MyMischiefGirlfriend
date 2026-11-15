"""ToonTest_01 step 59 (python with numpy / scipy / PIL): the skin coloured area inside the far eye outline.

usage: python t59_eye_v6g_mask.py <tag> [<tag> ...]
From the t48 close ups (x4, no hair) of the far eye at +35 (right eye) and -35 (left eye), and +-45:
  eye outline   eyeball + lashes (band, skirt, lower lash) closed by 14 px and filled: what reads as "the eye"
  abnormal      skin coloured pixels (face skin or lid sheet) inside that outline on the outer half of the eye
                (between the white and the lashes), plus, where the lashes leave the outer edge of the white open
                (between the end of the upper lash band and the lower lash), the skin between the white and the line
                joining the lashes above and below; normal skin = everything skin coloured outside
Writes renders/<tag>_g6_mask_<side>_<a>.png (white = abnormal), renders/<tag>_g6_marked_<side>_<a>.png (toon with the
abnormal area red, normal skin untouched, outline cyan) and prints the pixel counts.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, binary_dilation, binary_fill_holes, label

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t49_eye_v6f_metrics as M  # noqa: E402

VIEWS = (("R", 35), ("L", -35), ("R", 45), ("L", -45))


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def analyse(tag, s, a):
    lab = M.labels(os.path.join(M.R, f"{tag}_f6_{s}_id_{a}.png"))
    g = M.group(lab)
    ball = g == "ball"
    lb, n = label(ball)
    ball = lb == (1 + int(np.argmax(np.bincount(lb.ravel())[1:])))
    lash = g == "lash"
    lb, n = label(lash)
    if n:                                             # lashes of this eye: components touching the eyeball neighbourhood
        near = binary_dilation(ball, iterations=40)
        keep = [i for i in range(1, n + 1) if (near & (lb == i)).any()]
        lash = np.isin(lb, keep)
    eye = binary_fill_holes(binary_closing(ball | lash, structure=disk(14)))
    skinlike = (g == "skin") | (g == "lid")
    ys, xs = np.nonzero(ball)
    cx = (xs.min() + xs.max()) / 2
    X = np.arange(ball.shape[1])[None, :].repeat(ball.shape[0], 0)
    outer = X < cx if s == "R" else X > cx           # far eye: the temple side
    abn = eye & skinlike & outer
    # rows where the lashes leave the outer edge of the white open (between the band end and the lower lash): the eye
    # outline runs from the last lash pixel above to the first below; skin between that line and the white counts too
    H, W = ball.shape
    rows = np.nonzero(ball.any(1))[0]
    xw = np.full(H, np.nan)
    xo = np.full(H, np.nan)
    for y in rows:
        xb = np.nonzero(ball[y])[0]
        xw[y] = xb.min() if s == "R" else xb.max()
        xl = np.nonzero(lash[y])[0]
        xl = xl[(xl < xw[y]) & (xl > xw[y] - 80)] if s == "R" else xl[(xl > xw[y]) & (xl < xw[y] + 80)]
        if len(xl):
            xo[y] = xl.min() if s == "R" else xl.max()
    have = np.isfinite(xo)
    if have.sum() >= 2:
        ry = rows[(rows >= np.nonzero(have)[0].min()) & (rows <= np.nonzero(have)[0].max())]
        xi = np.interp(ry, np.nonzero(have)[0], xo[have])
        for y, x in zip(ry, xi):
            lo, hi = (int(round(x)), int(xw[y])) if s == "R" else (int(xw[y]) + 1, int(round(x)) + 1)
            if hi > lo:
                abn[y, lo:hi] |= skinlike[y, lo:hi]
    r_out = dict(xw=xw, xo=xo)
    lb, n = label(abn)
    if n:                                             # drop specks
        sizes = np.bincount(lb.ravel())
        abn = np.isin(lb, [i for i in range(1, n + 1) if sizes[i] >= 25])
    eye = eye | abn
    return dict(ball=ball, lash=lash, eye=eye, abn=abn)


if __name__ == "__main__":
    out = {}
    for tag in sys.argv[1:]:
        for s, a in VIEWS:
            r = analyse(tag, s, a)
            toon = M.load(os.path.join(M.R, f"{tag}_f6_{s}_toon_{a}.png"))
            vis = toon.copy()
            vis[r["abn"]] = vis[r["abn"]] * 0.35 + np.array([1.0, 0.0, 0.0]) * 0.65
            ring = binary_dilation(r["eye"], iterations=2) & ~r["eye"]
            vis[ring] = (0.0, 0.8, 0.9)
            Image.fromarray((r["abn"] * 255).astype(np.uint8)).save(os.path.join(M.R, f"{tag}_g6_mask_{s}_{a}.png"))
            Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save(os.path.join(M.R, f"{tag}_g6_marked_{s}_{a}.png"))
            out[f"{tag}_{s}_{a}"] = dict(abnormal_px=int(r["abn"].sum()), white_ball_px=int(r["ball"].sum()))
            print(tag, s, a, out[f"{tag}_{s}_{a}"])
    json.dump(out, open(os.path.join(M.EXP, "spec", "eye_v6g_mask_counts.json"), "w"), indent=1)
