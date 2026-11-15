"""ToonTest_01 step 31 (see-through venv python, read only on the PSD): v6c lash / crease texture.

usage: <venv python> t31_lash_texture_v6c.py
Same front-projected box as the v6b lash texture (r30_eye_targets.json tex_box), 1024 px instead of 512:
  shape    r30 EyeLash_Upper + EyeLash_Lower alpha, upscaled, smoothed and cut at 0.5 -> one clean silhouette (holes inside
           the band filled, crumbs under 1.6 r30 px^2 removed), then a 1 px soft edge for alpha-to-coverage / blending
  colour   r30 lash colours without the light highlight strokes, spread over the whole silhouette (no fringe of half
           transparent red-brown pixels below the band)
  crease   thin soft brown double-eyelid line painted above the band: offset from the band body (spikes ignored) by
           10-12.5 r30 px (at least 3 r30 px above the tallest lash tip under it), from 16 % to 70 % of the band (inner -> outer), width up to 1.8 r30 px, tapering to 0 at both
           ends; each eye from its own r30 band, so the drawn asymmetry stays
Writes r30/eye_tex_lash_v6c_<s>.png and spec/eye_v6c_crease.json (crease centre line in canvas px, for the mesh strip).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)
PROJ = os.path.abspath(os.path.join(EXP, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJ, "Live2DSource", "MainGirlfriend", "scripts"))
import s22_outfit_prep as s22  # noqa: E402

TGT = json.load(open(os.path.join(EXP, "spec", "r30_eye_targets.json")))
N = 1024
CREASE = dict(t0=0.16, t1=0.70, gap=10.0, gap_mid=2.5, width=1.8, colour=(150, 88, 74), alpha=0.85)


def components(mask):
    """label 8-connected components with PIL flood fills: returns list of (label image value, area)"""
    im = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8)).copy()      # fromarray images are read only
    out, k = [], 1
    while True:
        a = np.asarray(im)
        idx = np.argwhere(a == 255)
        if not len(idx) or k > 250:
            break
        y, x = idx[0]
        ImageDraw.floodfill(im, (int(x), int(y)), k, thresh=0)
        out.append((k, int((np.asarray(im) == k).sum())))
        k += 1
    return np.asarray(im), out


def main():
    layers = s22.load_layers()
    by = {n: np.asarray(im).astype(np.float32) / 255 for n, _, im in layers}
    out = {}
    for s in "LR":
        x0, y0, x1, y1 = TGT["tex_box"][s]
        W = x1 - x0
        U = N / W
        up = by[f"EyeLash_Upper_{s}"][y0:y1, x0:x1]
        lo = by[f"EyeLash_Lower_{s}"][y0:y1, x0:x1]
        a = np.maximum(up[..., 3], lo[..., 3])
        A = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.0))) / 255
        M = A > 0.5
        # fill holes inside the band (background not reachable from the border)
        bg = Image.fromarray(np.where(M, 0, 255).astype(np.uint8)).copy()
        ImageDraw.floodfill(bg, (0, 0), 128, thresh=0)
        holes = np.asarray(bg) == 255
        M = M | holes
        # drop crumbs
        lab, comps = components(M)
        keep = np.zeros_like(M)
        for k, area in comps:
            if area >= 0.4 * U * U * 4:
                keep |= lab == k
        M = keep
        alpha = np.asarray(Image.fromarray((M * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))) / 255
        # colour: r30 lash colours without the light strokes, spread over the silhouette
        rgb = np.where(up[..., 3:4] > 0.05, up[..., :3], lo[..., :3])
        w0 = np.maximum(up[..., 3], lo[..., 3])
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
        good = (w0 > 0.85) & (lum < 0.30)
        col = np.zeros((W, W, 3), np.float32)
        base = np.median(rgb[good], axis=0)
        col[:] = base
        for rad in (12, 6, 3, 1.5):
            ww = np.asarray(Image.fromarray((good * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))) / 255
            cs = np.stack([np.asarray(Image.fromarray((rgb[..., k] * good * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))) / 255
                           for k in range(3)], -1) / np.maximum(ww[..., None], 1e-4)
            m = np.clip(ww * 4, 0, 1)[..., None]
            col = col * (1 - m) + cs * m
        COL = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)) / 255
        # band body top per column (spikes ignored): running median of the top edge of the upper band
        Mu = np.asarray(Image.fromarray((up[..., 3] * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)) / 255 > 0.5
        cols = [x for x in range(N) if Mu[:, x].any()]
        top = np.array([np.nonzero(Mu[:, x])[0].min() for x in cols], float)
        bot = np.array([np.nonzero(Mu[:, x])[0].max() for x in cols], float)
        win = int(10 * U)
        body = np.array([np.percentile(top[max(0, i - win): i + win + 1], 70) for i in range(len(cols))])
        body = np.convolve(np.pad(body, win // 2, mode="edge"), np.ones(win // 2 * 2 + 1) / (win // 2 * 2 + 1), mode="valid")[:len(cols)]
        cols = np.array(cols, float)
        inner_is_low = s == "L"                         # L eye: the nose side is the small canvas x
        t = (cols - cols[0]) / (cols[-1] - cols[0])
        t = t if inner_is_low else 1 - t
        c = CREASE
        sel = (t >= c["t0"]) & (t <= c["t1"])
        u = (t[sel] - c["t0"]) / (c["t1"] - c["t0"])
        fit = np.polyval(np.polyfit(cols[sel], body[sel], 3), cols[sel])          # smooth arc, no kinks from the band
        clear = float(((fit - top[sel]) / U).max()) + 3.0               # above the tallest lash tip under the crease
        gap = max(c["gap"], clear)
        cy = fit - (gap + c["gap_mid"] * np.sin(np.pi * u)) * U
        hw = 0.5 * c["width"] * U * np.sin(np.pi * u) ** 0.6
        cx = cols[sel]
        # paint the crease (anti-aliased by supersampling the distance to the centre line)
        yy, xx = np.mgrid[0:N, 0:N]
        cre = np.zeros((N, N), np.float32)
        for X, Y, H in zip(cx, cy, hw):
            if H < 0.15 * U:
                continue
            x_ = int(X)
            ys = slice(max(0, int(Y - H - 3)), int(Y + H + 4))
            d = np.abs(yy[ys, x_] - Y)
            cre[ys, x_] = np.maximum(cre[ys, x_], np.clip(H + 0.75 - d, 0, 1.5) / 1.5)
        cre = np.asarray(Image.fromarray((cre * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))) / 255
        cre = np.clip(cre * 1.25, 0, 1) * c["alpha"] * (1 - alpha)
        ccol = np.array(c["colour"], np.float32) / 255
        rgb_out = (COL * alpha[..., None] + ccol * cre[..., None]) / np.maximum(alpha + cre, 1e-4)[..., None]
        a_out = np.clip(alpha + cre, 0, 1)
        img = np.concatenate([np.clip(rgb_out, 0, 1), a_out[..., None]], -1)
        Image.fromarray((img * 255).astype(np.uint8), "RGBA").save(os.path.join(EXP, "r30", f"eye_tex_lash_v6c_{s}.png"))
        step = max(1, int(2 * U))
        pts = [[round(x0 + X / U, 2), round(y0 + Y / U, 2), round(H / U, 3)] for X, Y, H in zip(cx[::step], cy[::step], hw[::step])]
        out[s] = dict(centre=pts, gap_px=round(gap, 2), holes_filled_px=int(holes.sum()), crumbs_removed=len([1 for _, a_ in comps if a_ < 0.4 * U * U * 4]))
        print("LASH", s, "holes filled (1024 px)", int(holes.sum()), "crumbs", out[s]["crumbs_removed"], "crease pts", len(pts))
    out["params"] = CREASE
    json.dump(out, open(os.path.join(EXP, "spec", "eye_v6c_crease.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
