"""ToonTest_01 step 49 (python with numpy / scipy / PIL): v6f eye metrics from the t48 renders, near and far eye apart.

usage: python t49_eye_v6f_metrics.py <tag> [<tag> ...]
Per angle and eye (x4 close ups, 240 x 170 px boxes; 1 screen px = 1 / (4 PPM)):
  ball_px          eyeball visible (flat colour id)
  white_px         toon render: bright, unsaturated pixels on the eyeball (sclera)
  rim_*            the 3 px ring just outside the eyeball, split by what is there: lid sheet (skin coloured lids),
                   lash (band, skirt, lower lash), skin (head: the eyeball outline against the bare face), bg
  lidstrip_px      lid sheet pixels within 14 px of the eyeball (the skin coloured strip between eyeball and lashes)
  lidstrip_w       lidstrip_px / eyeball outline length (mean strip width, px at x4)
  lid_underside_px lid sheet back faces in view (looking into the gap between lid and eyeball)
  gap_px           skin coloured pixels (lid sheet or face) lying between the eyeball and a lash (within 16 px of both)
Writes spec/eye_v6f_metrics_<tag>.json.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(EXP, "renders")
COL = dict(skin=(0.6, 0.6, 0.6), up=(0.1, 0.25, 1.0), upsk=(0.0, 0.9, 1.0), lo=(0.55, 0.2, 0.9), losk=(1.0, 0.45, 0.75),
           ball=(0.1, 0.85, 0.2), lash=(0.9, 0.05, 0.05), lashsk=(1.0, 0.5, 0.0), lowlash=(1.0, 0.95, 0.0),
           crease=(1.0, 1.0, 1.0), other=(0.25, 0.25, 0.25))
KEYS = list(COL)


def srgb(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


PAL = np.concatenate([np.array([srgb(COL[k]) for k in KEYS]), np.array([srgb(np.array(COL[k]) * 0.35) for k in KEYS])])


def load(p, alpha=False):
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im).astype(float) / 255
    if alpha:
        return a
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB")).astype(float) / 255


def labels(p, back=False):
    a = load(p, alpha=True)
    rgb, al = a[..., :3], a[..., 3]
    d = ((rgb[..., None, :] - PAL[None, None]) ** 2).sum(-1)
    am = d.argmin(-1)
    lab = am % len(KEYS)
    lab[al < 0.5] = -1
    if back:
        return lab, (am >= len(KEYS)) & (al >= 0.5)
    return lab


def group(lab):
    g = np.full(lab.shape, "bg", dtype=object)
    for k in KEYS:
        i = KEYS.index(k)
        g[lab == i] = ("lid" if k in ("up", "upsk", "lo", "losk") else "lash" if k in ("lash", "lashsk", "lowlash", "crease")
                       else k)
    return g


def metrics(tag, s, a):
    lab, back = labels(os.path.join(R, f"{tag}_f6_{s}_id_{a}.png"), back=True)
    toon = load(os.path.join(R, f"{tag}_f6_{s}_toon_{a}.png"))
    g = group(lab)
    ball = g == "ball"
    out = dict(ball_px=int(ball.sum()))
    out["lid_underside_px"] = int((back & (g == "lid")).sum())         # the lid sheet seen from below (gap to the eyeball)
    if ball.sum() < 50:
        return out
    mx, mn = toon.max(2), toon.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    lum = 0.2126 * toon[..., 0] + 0.7152 * toon[..., 1] + 0.0722 * toon[..., 2]
    out["white_px"] = int((ball & (lum > 0.80) & (sat < 0.10)).sum())
    ring = binary_dilation(ball, iterations=3) & ~ball
    edge = ball & ~binary_erosion(ball)
    n = max(1, int(ring.sum()))
    for k in ("lid", "lash", "skin", "bg", "other"):
        out[f"rim_{k}"] = round(float((ring & (g == k)).sum()) / n, 3)
    near = binary_dilation(ball, iterations=14) & ~ball
    lp = int((near & (g == "lid")).sum())
    out["lidstrip_px"] = lp
    out["lidstrip_w"] = round(lp / max(1, int(edge.sum())), 2)
    # skin coloured gap: lid / skin pixels squeezed between the eyeball and a lash (both within 16 px)
    lash = g == "lash"
    peach = (g == "lid") | (g == "skin")
    gap = peach & near & binary_dilation(ball, iterations=16) & binary_dilation(lash, iterations=16)
    gap &= ~binary_dilation(ball, iterations=1)
    out["gap_px"] = int(gap.sum())
    out["rim_dark"] = out["rim_lash"]
    return out


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        res = {}
        for a in (0, 35, -35, 45, -45, 60, -60, 90, -90):
            for s in "LR":
                if not os.path.exists(os.path.join(R, f"{tag}_f6_{s}_id_{a}.png")):
                    continue
                role = "front" if a == 0 else ("near" if (a > 0) == (s == "L") else "far")
                res[f"{s}_{a}"] = dict(role=role, **metrics(tag, s, a))
        json.dump(res, open(os.path.join(EXP, "spec", f"eye_v6f_metrics_{tag}.json"), "w"), indent=1)
        print("==", tag)
        for k, v in res.items():
            print(" ", k, v)
